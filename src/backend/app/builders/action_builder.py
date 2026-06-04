"""
ACTION node builder.

Converts ACTION node into a Zigflow `call: http` task.
"""


def build_action(node: dict, *, traversal_entry: dict | None = None) -> dict:
    """
    Convert ACTION node into a call: http DSL fragment.

    Reads inputs from $context (populated by INPUT node), calls an HTTP
    endpoint, and exports the result back to $context.

    Task name: {node_id}_{operation}

    Args:
        node: ACTION node dict from traversal
        traversal_entry: Pre-computed metadata

    Returns:
        DSL fragment dict with call: http task
    """
    node_id = node["id"]
    operation = node["data"]["operation"]
    raw_inputs = node["data"]["inputs"]  # dict: {input_name: context_variable}
    output_name = node["data"]["output"]

    task_name = f"{node_id}_{operation}"

    # Construct input body for HTTP call
    # Each input maps to a $context variable
    body_map = {}
    if raw_inputs:
        for input_key, context_var in raw_inputs.items():
            body_map[input_key] = f"${{ $context.{context_var} }}"

    # Export the HTTP response into $context under the output name
    export_expr = f"${{ $context + {{{output_name}: .}} }}"

    fragment = {
        task_name: {
            "call": "http",
            "with": {
                "method": "post",
                "endpoint": f"http://localhost:8000/api/v1/actions/{operation}",
            },
            "export": {
                "as": export_expr,
            },
        }
    }

    # Only add body if inputs exist
    if body_map:
        fragment[task_name]["with"]["body"] = body_map

    if traversal_entry and traversal_entry.get("is_terminal"):
        fragment[task_name]["then"] = "end"

    return fragment
