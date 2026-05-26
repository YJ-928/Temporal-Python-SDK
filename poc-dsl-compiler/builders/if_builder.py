from builders.condition_builder import build_condition_expression
from builders.task_names import resolve_task_name


def build_if(node: dict, compiler_context: dict | None = None) -> dict:
    """
    Convert an IF node into a Zigflow switch DSL fragment.

    Each branch is referenced by the task name the target node's builder
    would emit — goto-style routing. The flat do list in the DSL document
    relies on Zigflow's switch task routing to execute only one branch.

    Task name: {node_id}_if

    Args:
        node:             IF node dict from traversal
        compiler_context: {"adjacency": ..., "node_map": ...} from run_compiler()

    Returns:
        DSL fragment dict with switch task
    """
    node_id = node["id"]
    condition = node["condition"]
    when_expr = build_condition_expression(condition)

    cases = []

    if compiler_context is None:
        raise ValueError(
            f"IF builder requires compiler_context with 'adjacency' and 'node_map'. "
            f"Node: {node_id!r}"
        )

    adjacency = compiler_context["adjacency"]
    node_map = compiler_context["node_map"]

    true_child_id = None
    false_child_id = None

    for target_id, control in adjacency.get(node_id, []):
        if control and control.get("branch") == "true":
            true_child_id = target_id
        elif control and control.get("branch") == "false":
            false_child_id = target_id

    if true_child_id is None:
        raise ValueError(
            f"IF node {node_id!r} has no true branch edge "
            f'(expected edge with control={{"branch": "true"}})'
        )
    if false_child_id is None:
        raise ValueError(
            f"IF node {node_id!r} has no false branch edge "
            f'(expected edge with control={{"branch": "false"}})'
        )

    cases = [
        {"case":    {"when": when_expr, "then": resolve_task_name(node_map[true_child_id])}},
        {"default": {"then": resolve_task_name(node_map[false_child_id])}},
    ]

    task_name = f"{node_id}_if"
    return {
        task_name: {
            "switch": cases,
        }
    }
