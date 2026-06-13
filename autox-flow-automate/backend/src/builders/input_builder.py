"""
INPUT node builder.

Converts INPUT node into a Zigflow `set` task that captures external input
fields and exports them to $context for downstream tasks.
"""


def build_input(node: dict, *, traversal_entry: dict | None = None) -> dict:
    """
    Convert INPUT node into a set DSL fragment.

    Each input field is read from $input and stored as a named workflow variable.
    All captured fields are persisted to $context via export.as.

    Task name: {node_id}_capture

    Args:
        node: INPUT node dict from traversal
        traversal_entry: Pre-computed metadata

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

    # export.as merges all captured inputs into $context
    pairs = ", ".join(f"{entry['store_as']}: .{entry['store_as']}" for entry in raw_inputs)
    export_expr = f"${{ $context + {{{pairs}}} }}"

    task_name = f"{node_id}_capture"

    fragment = {
        task_name: {
            "set": set_map,
            "export": {
                "as": export_expr,
            },
        }
    }

    if traversal_entry:
        then_val = traversal_entry.get("then_transition")
        if not then_val and traversal_entry.get("is_terminal"):
            then_val = "end"
        if then_val:
            fragment[task_name]["then"] = then_val

    return fragment
