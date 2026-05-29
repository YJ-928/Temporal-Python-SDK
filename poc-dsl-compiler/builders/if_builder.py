from builders.condition_builder import build_condition_expression


def build_if(node: dict, *, traversal_entry=None, compiler_context=None) -> dict:
    """
    Convert an IF node into a Zigflow switch DSL fragment.

    Each branch is referenced by the task name the target node's builder
    would emit — goto-style routing. The flat do list in the DSL document
    relies on Zigflow's switch task routing to execute only one branch.

    Branch routing is pre-resolved by Phase A (traverse_graph) into
    traversal_entry["branch_map"]. This builder must not read adjacency
    or node_map directly.

    Task name: {node_id}_if

    Args:
        node:             IF node dict from traversal
        traversal_entry:  TraversalEntry from traverse_graph() — must contain branch_map
        compiler_context: Deprecated. Unused. Retained for signature consistency.

    Returns:
        DSL fragment dict with switch task
    """
    node_id = node["id"]
    condition = node["condition"]
    when_expr = build_condition_expression(condition)

    if traversal_entry is None or not traversal_entry.get("branch_map"):
        raise ValueError(
            f"IF builder requires a traversal entry with 'branch_map'. "
            f"Node: {node_id!r}. Ensure run_compiler() ran before generate_dsl()."
        )

    branch_map = traversal_entry["branch_map"]

    if "true" not in branch_map:
        raise ValueError(
            f"IF node {node_id!r} has no true branch in branch_map "
            f'(expected edge with control={{"branch": "true"}})'
        )
    if "false" not in branch_map:
        raise ValueError(
            f"IF node {node_id!r} has no false branch in branch_map "
            f'(expected edge with control={{"branch": "false"}})'
        )

    cases = [
        {"case":    {"when": when_expr, "then": branch_map["true"]["task_name"]}},
        {"default": {"then": branch_map["false"]["task_name"]}},
    ]

    task_name = f"{node_id}_if"
    return {
        task_name: {
            "switch": cases,
        }
    }
