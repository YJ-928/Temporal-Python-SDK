"""
Core graph compilation logic.

Phase A: Graph Analysis and Traversal
- Parse workflow JSON
- Build node map and adjacency list
- Find entry point (START node)
- Traverse graph in DFS preorder
- Pre-compute execution metadata for builders
"""
from typing import Any
from .exceptions import (
    GraphValidationError,
    CycleDetectedError,
    MissingBranchError,
)


def generate_node_map(nodes: list[dict]) -> dict[str, dict]:
    """
    Convert node list to node_id → node dict mapping.

    Args:
        nodes: List of node dicts from workflow JSON

    Returns:
        dict mapping node_id to full node dict
    """
    return {node["id"]: node for node in nodes}


def generate_adjacency_list(edges: list[dict]) -> dict[str, list[tuple[str, dict | None]]]:
    """
    Build adjacency list from edges.

    Returns source_id → [(target_id, control), ...] mapping.

    Args:
        edges: List of edge dicts from workflow JSON

    Returns:
        dict mapping source node_id to list of (target_id, control_dict) tuples
    """
    adjacency: dict[str, list[tuple[str, dict | None]]] = {}

    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        control = edge.get("control")
        branch = edge.get("branch")

        # Normalize top-level branch into control for compatibility
        if branch:
            if not control:
                control = {"branch": branch}
            elif "branch" not in control:
                control["branch"] = branch

        if source not in adjacency:
            adjacency[source] = []

        adjacency[source].append((target, control))

    return adjacency


def find_entrypoint(node_map: dict[str, dict]) -> str:
    """
    Find the START node ID.

    Args:
        node_map: node_id → node dict mapping

    Returns:
        ID of the START node

    Raises:
        ValueError: if no START node found
    """
    for node_id, node in node_map.items():
        if node["type"] == "START":
            return node_id

    raise ValueError("No START node found in workflow")


def resolve_task_name(node: dict) -> str:
    """
    Compute the DSL task name that a node's builder will emit.

    START and END nodes produce no DSL output (return None from builders).

    Args:
        node: Full node dict from node_map

    Returns:
        Task name string for DSL do-list

    Raises:
        ValueError: if node type has no naming rule
    """
    node_type = node["type"]
    node_id = node["id"]

    if node_type == "INPUT":
        return f"{node_id}_capture"
    elif node_type == "OUTPUT":
        return f"{node_id}_expose"
    elif node_type == "ACTION":
        operation = node["data"]["operation"]
        return f"{node_id}_{operation}"
    elif node_type == "AGENT":
        return f"{node_id}_agent"
    elif node_type == "IF":
        return f"{node_id}_if"
    elif node_type in ("START", "END"):
        raise ValueError(
            f"START and END nodes produce no DSL task. "
            f"resolve_task_name() must not be called for {node_type} nodes."
        )
    else:
        raise ValueError(
            f"No task naming rule for node type {node_type!r} (node id: {node_id!r})"
        )


def traverse_graph(
    entrypoint_id: str,
    node_map: dict[str, dict],
    adjacency: dict[str, list[tuple[str, dict | None]]],
) -> list[dict]:
    """
    Perform DFS traversal from START node.

    Returns ordered list of TraversalEntry dicts. Each entry contains:
    - node_id: str
    - node_type: str
    - node: dict (full node from node_map)
    - is_terminal: bool (True if any successor is END)
    - successors: list[str] (target node IDs)
    - incoming_edge_control: dict | None (control metadata from parent edge)
    - branch_map: dict | None (pre-resolved IF branch routing)

    Args:
        entrypoint_id: ID of START node
        node_map: node_id → node dict mapping
        adjacency: source_id → [(target_id, control)] mapping

    Returns:
        Ordered list of TraversalEntry dicts (DFS preorder)
    """
    order: list[dict] = []
    visited: set[str] = set()

    def _dfs(node_id: str, parent_control: dict | None) -> None:
        if node_id in visited:
            return

        visited.add(node_id)

        node = node_map[node_id]
        node_type = node["type"]
        neighbors = adjacency.get(node_id, [])
        successors = [target_id for target_id, _ in neighbors]

        # is_terminal: True if any successor is END node
        is_terminal = any(
            node_map.get(succ_id, {}).get("type") == "END"
            for succ_id in successors
        )

        # Pre-resolve IF branch routing for if_builder
        branch_map = None
        if node_type == "IF":
            branch_map = {}
            for target_id, control in neighbors:
                if control and control.get("branch") in ("true", "false"):
                    tgt_node = node_map[target_id]
                    if tgt_node["type"] == "END":
                        task_name = "end"
                    else:
                        task_name = resolve_task_name(tgt_node)
                    branch_map[control["branch"]] = {
                        "node_id": target_id,
                        "task_name": task_name,
                    }

        # Append TraversalEntry
        order.append({
            "node_id": node_id,
            "node_type": node_type,
            "node": node,
            "is_terminal": is_terminal,
            "successors": successors,
            "incoming_edge_control": parent_control,
            "branch_map": branch_map,
        })

        # Recurse to children
        for target_id, control in neighbors:
            _dfs(target_id, control)

    _dfs(entrypoint_id, None)

    return order


def compile_workflow(workflow: dict) -> dict:
    """
    Compile workflow JSON into graph analysis artifacts.

    Args:
        workflow: dict with "nodes" and "edges" keys

    Returns:
        dict with:
        - node_map: dict
        - adjacency: dict
        - entrypoint: str
        - traversal: list[dict] (ordered TraversalEntry list)
    """
    node_map = generate_node_map(workflow["nodes"])
    adjacency = generate_adjacency_list(workflow["edges"])
    entrypoint = find_entrypoint(node_map)
    traversal = traverse_graph(entrypoint, node_map, adjacency)

    return {
        "node_map": node_map,
        "adjacency": adjacency,
        "entrypoint": entrypoint,
        "traversal": traversal,
    }


def validate_graph(
    nodes: list[dict],
    edges: list[dict],
    node_map: dict[str, dict],
    adjacency: dict[str, list[tuple[str, dict | None]]],
) -> None:
    """
    Validate graph topology, correctness, and connectivity rules.
    """
    # 1. Exactly one START node
    start_nodes = [n for n in nodes if n["type"] == "START"]
    if len(start_nodes) == 0:
        raise GraphValidationError("Workflow must have exactly one START node (none found)")
    if len(start_nodes) > 1:
        raise GraphValidationError(f"Workflow must have exactly one START node (found {len(start_nodes)})")
    start_node = start_nodes[0]
    start_id = start_node["id"]

    # 2. At least one END node
    end_nodes = [n for n in nodes if n["type"] == "END"]
    if len(end_nodes) == 0:
        raise GraphValidationError("Workflow must have at least one END node (none found)")

    # 3. END nodes cannot have outgoing edges
    for node_id, node in node_map.items():
        if node["type"] == "END":
            if len(adjacency.get(node_id, [])) > 0:
                raise GraphValidationError(f"END node '{node_id}' cannot have outgoing edges")

    # 4. Every IF node has exactly one true branch and exactly one false branch (and no duplicate branch labels)
    for node_id, node in node_map.items():
        if node["type"] == "IF":
            neighbors = adjacency.get(node_id, [])
            true_branches = 0
            false_branches = 0
            for _, control in neighbors:
                branch_val = control.get("branch") if control else None
                if branch_val == "true":
                    true_branches += 1
                elif branch_val == "false":
                    false_branches += 1
            if true_branches != 1 or false_branches != 1:
                raise MissingBranchError(
                    f"IF node '{node_id}' must have exactly one 'true' branch and exactly one 'false' branch. "
                    f"Found: true={true_branches}, false={false_branches}"
                )

    # 5. No cycles
    visiting = set()
    visited = set()
    def dfs_cycle(curr_id: str) -> None:
        if curr_id in visiting:
            raise CycleDetectedError(f"Workflow contains a cycle involving node '{curr_id}'")
        if curr_id in visited:
            return
        visiting.add(curr_id)
        for target_id, _ in adjacency.get(curr_id, []):
            dfs_cycle(target_id)
        visiting.remove(curr_id)
        visited.add(curr_id)

    # Detect cycles from START
    dfs_cycle(start_id)

    # Detect cycles in any disconnected components
    for node_id in node_map:
        if node_id not in visited:
            dfs_cycle(node_id)

    # 6. All nodes must be reachable from START
    # We collect all visited nodes from dfs_cycle(start_id)
    # But since we did dfs_cycle for disconnected nodes as well,
    # let's recalculate reachability strictly from start_id
    reachable = set()
    def dfs_reach(curr_id: str) -> None:
        if curr_id in reachable:
            return
        reachable.add(curr_id)
        for target_id, _ in adjacency.get(curr_id, []):
            dfs_reach(target_id)

    dfs_reach(start_id)

    all_nodes = set(node_map.keys())
    unreachable_nodes = all_nodes - reachable
    if unreachable_nodes:
        raise GraphValidationError(f"Unreachable nodes found in workflow: {sorted(unreachable_nodes)}")

