def build_output(node: dict, *, traversal_entry=None, compiler_context=None) -> dict:
    """
    Convert an OUTPUT node into a set DSL fragment.

    Each output field is read from the current workflow context and
    written into the final output object.

    Task name: {node_id}_expose

    Args:
        node: OUTPUT node dict from traversal

    Returns:
        DSL fragment dict with set task
    """
    node_id = node["id"]
    raw_outputs = node["data"]["outputs"]

    # {field: "${ .<field> }"} — reads each field from the current data context
    set_map = {}
    for entry in raw_outputs:
        field = entry["field"]
        set_map[field] = f"${{ .{field} }}"

    task_name = f"{node_id}_expose"

    fragment = {
        task_name: {
            "set": set_map,
        }
    }
    if traversal_entry and traversal_entry["is_terminal"]:
        fragment[task_name]["then"] = "end"
    return fragment
