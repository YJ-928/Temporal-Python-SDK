# ─────────────────────────────────────────────────────────────────────────────
# PHASE A — GRAPH COMPILATION
#
# Ownership: graph structure, topology, adjacency, traversal order, and all
# execution-aware metadata (is_terminal, branch_map, incoming_edge_control).
#
# This module is the sole producer of TraversalEntry dicts. The DSL generator
# (Phase B) and all builders must not read adjacency, node_map, or any other
# graph internals. Everything they need arrives pre-computed in TraversalEntry.
# ─────────────────────────────────────────────────────────────────────────────

from utils.task_names import resolve_task_name


def generate_node_map(workflow: dict):
    node_map = {}

    for node in workflow["nodes"]:
        node_map[node["id"]] = node

    return node_map

def generate_adjaceny_list(workflow: dict):
    adjacency = {}

    for edge in workflow["edges"]:
        source = edge["source"]
        target = edge["target"]

        if source not in adjacency:
            adjacency[source] = []

        adjacency[source].append((target, edge.get("control")))

    return adjacency

def find_entrypoint(node_map: dict):
  for node_id, node in node_map.items():

    if node["type"] == "START":
      return node_id

  return "Entrypoint not found"

def generate_graph_structure(entrypoint, node_map, adjacency, graph=None):
    # NOTE: graph node dicts (the "node" values inside each graph entry) are
    # READ-ONLY after construction. Do not attach traversal-specific metadata
    # to them — they are shared references in the memoised DAG. A node
    # reachable from multiple parents has one graph entry shared across all
    # parents. Metadata that belongs to a traversal step must live in a
    # TraversalEntry, not on the graph node.
    if graph is None:
        graph = {}

    if entrypoint in graph:
        return graph[entrypoint]

    graph[entrypoint] = {"node": node_map[entrypoint], "children": []}
    children = adjacency.get(entrypoint, [])

    for target_id, control in children:
        child_graph = generate_graph_structure(target_id, node_map, adjacency, graph)
        graph[entrypoint]["children"].append({"control": control, "child": child_graph})

    return graph[entrypoint]

def print_graph(graph, level=0, visited=None, control=None):
    if visited is None:
        visited = set()

    node_id = graph["node"]["id"]
    prefix = "  " * level

    if node_id in visited:
        print(prefix + graph["node"]["type"] + " [REF]")
        return

    visited.add(node_id)
    node_type = graph["node"]["type"]
    branch = control.get("branch") if control else None
    display = node_type + (f" [branch={branch}]" if branch else "")
    print(prefix + display)

    for edge in graph["children"]:
        print_graph(edge["child"], level + 1, visited, edge["control"])

def traverse_graph(graph, adjacency, node_map, order=None, visited=None, parent_control=None):
    """
    Perform DFS on the graph and return a list of TraversalEntry dicts.

    Each entry wraps the original node with compiler-computed execution
    metadata. Entries are new objects created per traversal step — the
    shared graph node dicts are never mutated.

    Args:
        graph:          Current graph node (from generate_graph_structure).
        adjacency:      source_id → [(target_id, control)] mapping.
        node_map:       node_id → node dict mapping.
        order:          Accumulator for traversal entries (mutated in-place).
        visited:        Set of already-visited node IDs (deduplicates shared nodes).
        parent_control: Edge control dict from the parent edge, or None for START.

    Returns:
        Ordered list of TraversalEntry dicts in DFS preorder.
    """
    if order is None:
        order = []
    if visited is None:
        visited = set()

    node = graph["node"]
    node_id = node["id"]
    node_type = node["type"]

    if node_id in visited:
        return order

    visited.add(node_id)

    # Compute successors and terminal flag.
    # This logic belongs in Phase A — never in the generator or builders.
    neighbors = adjacency.get(node_id, [])
    successors = [target_id for target_id, _ in neighbors]
    is_terminal = any(
        node_map.get(succ_id, {}).get("type") == "END"
        for succ_id in successors
    )

    # Pre-resolve IF branch routing so if_builder never reads adjacency.
    branch_map = None
    if node_type == "IF":
        branch_map = {}
        for target_id, control in neighbors:
            if control and control.get("branch") in ("true", "false"):
                branch_map[control["branch"]] = {
                    "node_id": target_id,
                    "task_name": resolve_task_name(node_map[target_id]),
                }

    order.append({
        "node_id": node_id,
        "node_type": node_type,
        "node": node,           # READ-ONLY — never mutate this dict
        "is_terminal": is_terminal,
        "successors": successors,
        "incoming_edge_control": parent_control,
        "branch_map": branch_map,
    })

    for edge in graph["children"]:
        traverse_graph(edge["child"], adjacency, node_map, order, visited, edge["control"])

    return order

def run_compiler(workflow: dict) -> dict:
    """Compiler to generate Graph and Traversal Flow"""
    node_map = generate_node_map(workflow)
    adjacency = generate_adjaceny_list(workflow)
    starting_point = find_entrypoint(node_map)

    graph = generate_graph_structure(starting_point, node_map, adjacency)
    traversal = traverse_graph(graph, adjacency, node_map)

    return {
        "node_map": node_map,
        "adjacency": adjacency,
        "graph": graph,
        "traversal": traversal,
        "builder_context": {},  # Deprecated. All builder metadata is now in
                                # traversal entries. Kept for call-site compat
                                # until LOOP/PARALLEL stabilise.
    }
