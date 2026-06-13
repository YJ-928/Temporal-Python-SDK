"""
IF node builder.

Converts IF node into a Zigflow `switch` task with true/false branches.
"""
from .condition_builder import build_condition_expression


def build_if(node: dict, *, traversal_entry: dict | None = None) -> dict:
    """
    Convert IF node into a switch DSL fragment.

    Reads the condition from node["data"] (left, operator, right) and
    uses pre-resolved branch_map from traversal_entry to construct
    true/false branch routing.

    Task name: {node_id}_if

    Args:
        node: IF node dict from traversal
        traversal_entry: Pre-computed metadata with branch_map

    Returns:
        DSL fragment dict with switch task
    """
    node_id = node["id"]
    task_name = f"{node_id}_if"

    # Extract condition from node["data"] (frontend format)
    left = node["data"]["left"]
    operator = node["data"]["operator"]
    right = node["data"]["right"]

    # Build jq condition expression
    condition_expr = build_condition_expression(left, operator, right)

    # Extract pre-resolved branch routing from traversal_entry
    if not traversal_entry or not traversal_entry.get("branch_map"):
        raise ValueError(
            f"IF node {node_id} missing branch_map in traversal_entry. "
            f"Ensure traverse_graph() pre-resolves IF branch routing."
        )

    branch_map = traversal_entry["branch_map"]

    # Build switch cases
    switch_cases = [
        {
            "case": {
                "when": condition_expr,
                "then": branch_map["true"]["task_name"],
            }
        },
        {
            "default": {
                "then": branch_map["false"]["task_name"],
            }
        },
    ]

    fragment = {
        task_name: {
            "switch": switch_cases,
        }
    }

    if traversal_entry and traversal_entry.get("is_terminal"):
        fragment[task_name]["then"] = "end"

    return fragment
