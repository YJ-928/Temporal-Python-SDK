def build_input(node: dict) -> dict:
    """
    Convert an INPUT node into a set DSL fragment.

    Each input field is read from $input and stored as a named workflow variable.

    Task name: {node_id}_capture

    Args:
        node: INPUT node dict from traversal

    Returns:
        DSL fragment dict with set task
    """
    node_id = node["id"]
    raw_inputs = node["data"]["inputs"]

    # {store_as: "${ $input.field }"} — reads each field from workflow input
    set_map = {}
    for entry in raw_inputs:
        store_as = entry["store_as"]
        field = entry["field"]
        set_map[store_as] = f"${{ $input.{field} }}"

    task_name = f"{node_id}_capture"

    return {
        task_name: {
            "set": set_map,
        }
    }
