"""
OUTPUT node builder.

Converts OUTPUT node into a Zigflow `set` task that exposes named workflow
variables as the final workflow result.
"""


def build_output(node: dict, *, traversal_entry: dict | None = None) -> dict:
    """
    Convert OUTPUT node into a set DSL fragment.

    Each output field is read from the current workflow data and written into
    the final output object.

    Task name: {node_id}_expose

    Args:
        node: OUTPUT node dict from traversal
        traversal_entry: Pre-computed metadata

    Returns:
        DSL fragment dict with set task
    """
    node_id = node["id"]
    raw_outputs = node["data"]["outputs"]

    set_map = {}
    for entry in raw_outputs:
        field = entry["field"]
        # Read from context since ACTION nodes export their outputs there
        set_map[field] = f"${{ $context.{field} }}"

    task_name = f"{node_id}_expose"

    fragment = {
        task_name: {
            "set": set_map,
        }
    }

    if traversal_entry:
        then_val = traversal_entry.get("then_transition")
        if not then_val and traversal_entry.get("is_terminal"):
            then_val = "end"
        if then_val:
            fragment[task_name]["then"] = then_val

    return fragment
