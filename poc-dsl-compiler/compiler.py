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

#PARALLEL helpers
def _bfs_reachable(start_id: str, adjacency: dict) -> set:
    """
    Return the set of all node IDs reachable from start_id (excluding start_id).

    Args:
        start_id:  ID of the starting node.
        adjacency: source_id → [(target_id, control)] mapping.

    Returns:
        Set of node IDs reachable via forward edges, NOT including start_id.
    """
    reachable: set = set()
    queue = [start_id]
    while queue:
        current = queue.pop(0)
        for target_id, _ in adjacency.get(current, []):
            if target_id not in reachable:
                reachable.add(target_id)
                queue.append(target_id)
    return reachable

def _find_parallel_convergence(parallel_node_id: str, adjacency: dict, node_map: dict) -> str:
    """
    Return the ID of the convergence node for a PARALLEL node.

    Algorithm
    ---------
    1. Collect the reachable sets for every branch start (including the start
       node itself).
    2. Intersect all sets — the result is every node reachable from ALL branches.
    3. Among the candidates, find the root: the candidate that no other
       candidate can reach (i.e. it has no predecessors inside the candidate
       set). This is the first join point in topological order.

    Raises:
        ValueError: Branches never converge, or ambiguous convergence
                    (two independent roots in the candidate set).
    """
    branch_starts = [t for t, _ in adjacency.get(parallel_node_id, [])]
    if not branch_starts:
        raise ValueError(
            f"PARALLEL node {parallel_node_id!r} has no outgoing edges — "
            f"every PARALLEL must have at least two branches."
        )

    # Reachable set per branch start (inclusive of the start node itself)
    reachable_sets = []
    for start in branch_starts:
        rs = _bfs_reachable(start, adjacency)
        rs.add(start)
        reachable_sets.append(rs)

    # Intersection across all branches
    candidates: set = reachable_sets[0].copy()
    for rs in reachable_sets[1:]:
        candidates &= rs

    if not candidates:
        raise ValueError(
            f"PARALLEL node {parallel_node_id!r}: branches never converge. "
            f"All branches must join at a single convergence node."
        )

    # Root candidate: no other candidate can reach it
    convergence = None
    for c in candidates:
        reachable_from_others: set = set()
        for d in candidates:
            if d != c:
                reachable_from_others |= _bfs_reachable(d, adjacency)
        if c not in reachable_from_others:
            if convergence is not None:
                raise ValueError(
                    f"PARALLEL node {parallel_node_id!r}: ambiguous convergence — "
                    f"multiple root candidates found: {convergence!r} and {c!r}. "
                    f"All branches must converge at exactly one node."
                )
            convergence = c

    if convergence is None:
        raise ValueError(
            f"PARALLEL node {parallel_node_id!r}: could not determine a unique "
            f"convergence node from candidates: {candidates!r}."
        )

    return convergence

def _detect_back_edge_to_parallel(
    parallel_node_id: str, branch_starts: list, adjacency: dict
) -> None:
    """
    Raise ValueError if any branch loops back to the PARALLEL node itself.

    A back-edge to the PARALLEL node indicates a cycle (the workflow wants to
    loop), which is not a fork/join pattern. Use a LOOP node type instead.

    Args:
        parallel_node_id: ID of the PARALLEL node.
        branch_starts:    Direct successor IDs (one per branch).
        adjacency:        Full adjacency list.

    Raises:
        ValueError: If a cycle through the PARALLEL node is detected.
    """
    for start in branch_starts:
        if parallel_node_id in _bfs_reachable(start, adjacency):
            raise ValueError(
                f"PARALLEL node {parallel_node_id!r}: branch starting at "
                f"{start!r} contains a back-edge to the PARALLEL node itself. "
                f"Use a LOOP node type for cyclic patterns."
            )

def _traverse_branch(
    branch_start_id: str,
    convergence_id: str,
    adjacency: dict,
    node_map: dict,
) -> list:
    """
    Return ordered TraversalEntry list for one PARALLEL branch.

    Traverses in DFS preorder from branch_start_id, stopping before
    convergence_id. Handles nested IF and nested PARALLEL correctly.

    Args:
        branch_start_id: First node in this branch (direct PARALLEL successor).
        convergence_id:  Node where all branches re-join — NOT included in output.
        adjacency:       Full adjacency list.
        node_map:        Full node map.

    Returns:
        Ordered list of TraversalEntry dicts in DFS preorder.
    """
    order: list = []
    visited: set = {convergence_id}
    pending_convergences: set = set()

    def _dfs(node_id: str, parent_control) -> None:
        if node_id in visited:
            return
        visited.add(node_id)

        node = node_map[node_id]
        node_type = node["type"]
        neighbors = adjacency.get(node_id, [])
        successors = [t for t, _ in neighbors]

        is_terminal = any(
            node_map.get(s, {}).get("type") == "END" for s in successors
        )

        # Pre-resolve IF branch routing
        branch_map = None
        if node_type == "IF":
            branch_map = {}
            for target_id, control in neighbors:
                if control and control.get("branch") in ("true", "false"):
                    branch_map[control["branch"]] = {
                        "node_id": target_id,
                        "task_name": resolve_task_name(node_map[target_id]),
                    }

        # Handle nested PARALLEL inside a branch
        parallel_map = None
        inner_convergence_id = None
        if node_type == "PARALLEL":
            branch_starts_inner = [t for t, _ in neighbors]
            _detect_back_edge_to_parallel(node_id, branch_starts_inner, adjacency)
            inner_convergence_id = _find_parallel_convergence(node_id, adjacency, node_map)
            parallel_map = {}
            for i, (bs, _) in enumerate(neighbors):
                bid = f"branch_{i}"
                inner_trav = _traverse_branch(bs, inner_convergence_id, adjacency, node_map)
                parallel_map[bid] = {
                    "branch_id": bid,
                    "entry_node_id": bs,
                    "traversal": inner_trav,
                }
                for entry in inner_trav:
                    visited.add(entry["node_id"])  # skip branch nodes in outer DFS
            pending_convergences.add(inner_convergence_id)

        order.append({
            "node_id": node_id,
            "node_type": node_type,
            "node": node,
            "is_terminal": is_terminal,
            "successors": successors,
            "incoming_edge_control": parent_control,
            "branch_map": branch_map,
            "parallel_map": parallel_map,
            "reads_from_context": node_id in pending_convergences,
        })

        if node_type == "PARALLEL":
            # Skip branches (already captured in parallel_map).
            # Continue DFS from the inner convergence node.
            _dfs(inner_convergence_id, None)
        else:
            for target_id, control in neighbors:
                _dfs(target_id, control)

    _dfs(branch_start_id, None)
    return order

# Main traversal
def traverse_graph(
    graph,
    adjacency,
    node_map,
    order=None,
    visited=None,
    parent_control=None,
    convergence_nodes=None,
):
    """
    Perform DFS on the graph and return a list of TraversalEntry dicts.

    Each entry wraps the original node with compiler-computed execution
    metadata. Entries are new objects created per traversal step — the
    shared graph node dicts are never mutated.

    Args:
        graph:             Current graph node (from generate_graph_structure).
        adjacency:         source_id → [(target_id, control)] mapping.
        node_map:          node_id → node dict mapping.
        order:             Accumulator for traversal entries (mutated in-place).
        visited:           Set of already-visited node IDs (deduplicates shared nodes).
        parent_control:    Edge control dict from the parent edge, or None for START.
        convergence_nodes: Set of node IDs that are PARALLEL convergence points.
                           These nodes receive reads_from_context=True so their
                           builders know to source data from $context.

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

    # Pre-resolve PARALLEL branch routing so parallel_builder never reads adjacency.
    parallel_map = None
    convergence_id = None
    if node_type == "PARALLEL":
        branch_starts = [t for t, _ in neighbors]
        _detect_back_edge_to_parallel(node_id, branch_starts, adjacency)
        convergence_id = _find_parallel_convergence(node_id, adjacency, node_map)
        parallel_map = {}
        for i, (branch_start, _) in enumerate(neighbors):
            bid = f"branch_{i}"
            branch_traversal = _traverse_branch(branch_start, convergence_id, adjacency, node_map)
            parallel_map[bid] = {
                "branch_id": bid,
                "entry_node_id": branch_start,
                "traversal": branch_traversal,
            }
            # Mark branch nodes as visited so the outer DFS skips them.
            for entry in branch_traversal:
                visited.add(entry["node_id"])
        if convergence_nodes is None:
            convergence_nodes = set()
        convergence_nodes.add(convergence_id)

    order.append({
        "node_id": node_id,
        "node_type": node_type,
        "node": node,
        "is_terminal": is_terminal,
        "successors": successors,
        "incoming_edge_control": parent_control,
        "branch_map": branch_map,
        "parallel_map": parallel_map,
        "reads_from_context": bool(convergence_nodes and node_id in convergence_nodes),
    })

    if node_type == "PARALLEL":
        # Skip the branch children (they live inside parallel_map).
        # Jump directly to the convergence node to continue the main traversal.
        conv_graph = generate_graph_structure(convergence_id, node_map, adjacency)
        traverse_graph(conv_graph, adjacency, node_map, order, visited, None, convergence_nodes)
    else:
        for edge in graph["children"]:
            traverse_graph(
                edge["child"], adjacency, node_map, order, visited,
                edge["control"], convergence_nodes,
            )

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
        "builder_context": {},
    }
