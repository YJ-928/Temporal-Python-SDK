"""
Replay engine for topological execution state reconstruction.

Builds a visual DAG from ReactFlow schemas and propagates execution states
using topological sorting, handling parallel fan-out/joins and conditional branching.
"""
from typing import Dict, List
from ..config import get_logger

logger = get_logger(__name__)


def propagate_dag_states(
    rf_json: dict,
    event_states: dict,
    workflow_completed: bool
) -> dict:
    """
    Trace and propagate execution statuses topologically using the ReactFlow graph.
    Resolves parallel execution paths, join nodes, and conditional branches.

    Args:
        rf_json: ReactFlow JSON dictionary containing "nodes" and "edges"
        event_states: Event status dictionary mapped by ReactFlow node ID
        workflow_completed: True if the workflow has completed execution

    Returns:
        Dict mapping node IDs to their trace status and payload information
    """
    nodes = rf_json.get("nodes", [])
    edges = rf_json.get("edges", [])

    # Initialize all nodes to 'not_started'
    final_states = {}
    node_by_id = {}
    for node in nodes:
        node_id = node["id"]
        node_by_id[node_id] = node
        final_states[node_id] = {
            "status": "not_started",
            "input": None,
            "output": None,
            "error": None,
            "duration_seconds": None
        }

    # Overlay explicit event states from history (activities/child workflows)
    # Map event_states keys (task names like N2_capture, N5_send_rain_alert_inner) back to ReactFlow node IDs (like N2, N5_send_rain_alert)
    for task_name, state in event_states.items():
        matched_node_id = None
        if task_name in final_states:
            matched_node_id = task_name
        else:
            # Sort by length descending to match the longest, most specific node ID prefix first
            for nid in sorted(final_states.keys(), key=len, reverse=True):
                if task_name.startswith(nid + "_"):
                    matched_node_id = nid
                    break

        if matched_node_id:
            final_states[matched_node_id] = {
                "status": state.get("status", "running"),
                "input": state.get("input"),
                "output": state.get("output"),
                "error": state.get("error"),
                "duration_seconds": state.get("duration_seconds")
            }

    # Build adjacency lists for DAG traversal
    # outgoing: node_id -> list of (target_id, edge_condition)
    # incoming: node_id -> list of source_id
    outgoing: Dict[str, List[tuple]] = {n["id"]: [] for n in nodes}
    incoming: Dict[str, List[str]] = {n["id"]: [] for n in nodes}

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        condition = edge.get("branch")
        if not condition and edge.get("control"):
            condition = edge.get("control", {}).get("branch")
        if not condition:
            condition = edge.get("data", {}).get("condition")
            
        if source in outgoing and target in incoming:
            outgoing[source].append((target, condition))
            incoming[target].append(source)

    # Perform Topological Sort using Kahn's Algorithm
    in_degree = {n["id"]: 0 for n in nodes}
    for edge in edges:
        target = edge.get("target")
        if target in in_degree:
            in_degree[target] += 1

    # Find starting nodes (in-degree == 0)
    queue = [n["id"] for n in nodes if in_degree[n["id"]] == 0]
    topo_order = []
    while queue:
        curr = queue.pop(0)
        topo_order.append(curr)
        for target, _ in outgoing[curr]:
            in_degree[target] -= 1
            if in_degree[target] == 0:
                queue.append(target)

    # Backup: append any remaining nodes to avoid skipping them in case of cycles or disconnected nodes
    if len(topo_order) < len(nodes):
        seen = set(topo_order)
        for n in nodes:
            if n["id"] not in seen:
                topo_order.append(n["id"])

    # Locate start node (case-insensitive)
    start_node = next((n for n in nodes if str(n.get("type", "")).lower() == "start"), None)
    if not start_node:
        logger.warning("No start node found in ReactFlow graph for trace replay")
        return final_states

    start_id = start_node["id"]
    final_states[start_id]["status"] = "completed"

    def _mark_branch_skipped(nid: str):
        """Recursively mark a visual branch path as skipped."""
        if final_states[nid]["status"] in ["completed", "running", "failed"]:
            return  # Do not skip already executed nodes
            
        final_states[nid] = {
            "status": "skipped",
            "input": None,
            "output": None,
            "error": None
        }
        for target, _ in outgoing[nid]:
            # A join node is only skipped if ALL its incoming paths are skipped
            all_parents_skipped = all(
                final_states[p]["status"] == "skipped" for p in incoming[target]
            )
            if all_parents_skipped:
                _mark_branch_skipped(target)

    # Propagate states along the topological order
    for node_id in topo_order:
        node = node_by_id.get(node_id)
        if not node:
            continue
        node_type = str(node.get("type", "")).lower()

        # If it's the start node, it's already set to completed
        if node_id == start_id:
            continue

        # 1. Propagate state to inline control nodes (input, output, if, end, start)
        # These nodes don't produce activity completion events, so their status is inferred from parents.
        if node_type in ["input", "output", "if", "end", "start"]:
            current_status = final_states[node_id]["status"]
            
            # We only propagate status if it is not already resolved by an execution event
            if current_status not in ["completed", "running", "failed"]:
                parents = incoming[node_id]
                if parents:
                    # If ALL parents are skipped, this node is skipped
                    if all(final_states[p]["status"] == "skipped" for p in parents):
                        final_states[node_id]["status"] = "skipped"
                    # If ALL non-skipped parents are completed, this node becomes completed
                    else:
                        non_skipped = [p for p in parents if final_states[p]["status"] != "skipped"]
                        if non_skipped and all(final_states[p]["status"] == "completed" for p in non_skipped):
                            final_states[node_id]["status"] = "completed"

        # 2. Overlay condition-based exclusions (IF nodes)
        if node_type == "if":
            # If the IF node is completed, evaluate which branch was taken
            if final_states[node_id]["status"] == "completed":
                true_active = False
                false_active = False
                
                for target, cond in outgoing[node_id]:
                    target_status = final_states[target]["status"]
                    is_active = target_status in ["running", "completed", "failed"]
                    if cond == "true" and is_active:
                        true_active = True
                    elif cond == "false" and is_active:
                        false_active = True

                # Exclude the branch that was not taken
                if true_active and not false_active:
                    for target, cond in outgoing[node_id]:
                        if cond == "false":
                            _mark_branch_skipped(target)
                elif false_active and not true_active:
                    for target, cond in outgoing[node_id]:
                        if cond == "true":
                            _mark_branch_skipped(target)

    # Final cleanup on workflow completion
    if workflow_completed:
        # Mark END node completed (case-insensitive)
        end_node = next((n for n in nodes if str(n.get("type", "")).lower() == "end"), None)
        if end_node:
            final_states[end_node["id"]]["status"] = "completed"
        
        # Propagate completion to any remaining unexecuted nodes on the active path
        for node_id in topo_order:
            if final_states[node_id]["status"] == "not_started":
                parents = incoming[node_id]
                if parents and all(final_states[p]["status"] in ["completed", "skipped"] for p in parents):
                    final_states[node_id]["status"] = "completed"

    return final_states
