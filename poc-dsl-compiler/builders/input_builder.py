def build_input(node: dict, compiler_context: dict | None = None) -> dict:
    """
    Convert an INPUT node into a set DSL fragment.

    Each input field is read from $input and stored as a named workflow variable.
    All captured fields are also persisted to $context via export.as so they
    remain accessible to later tasks even after an ACTION's output.as has
    replaced the flowing data context.

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

    # export.as merges all captured inputs into $context so they survive
    # subsequent ACTION output.as replacements in parallel-branch workflows.
    # ".var" references the value just written by the set task above.
    pairs = ", ".join(f"{entry['store_as']}: .{entry['store_as']}" for entry in raw_inputs)
    export_expr = "${ $context + {" + pairs + "} }"

    task_name = f"{node_id}_capture"

    return {
        task_name: {
            "set": set_map,
            "export": {
                "as": export_expr,
            },
        }
    }
