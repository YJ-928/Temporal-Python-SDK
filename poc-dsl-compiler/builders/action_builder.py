def build_action(node: dict) -> dict:
    """
    Convert an ACTION node into a call: http DSL fragment.

    The operation name becomes the URL path. Each input maps a workflow
    variable to a request body parameter. The output is stored as a
    named workflow variable via output.as.

    Task name: {node_id}_{operation}

    Args:
        node: ACTION node dict from traversal

    Returns:
        DSL fragment dict with call: http task
    """
    node_id = node["id"]
    data = node["data"]

    operation = data["operation"]
    input_map = data["inputs"]   # {param_name: context_var}
    output_var = data["output"]

    # {param_name: "${ .<context_var> }"} — reads each param from workflow context
    body = {param: f"${{ .{ctx_var} }}" for param, ctx_var in input_map.items()}

    task_name = f"{node_id}_{operation}"

    return {
        task_name: {
            "call": "http",
            "with": {
                "method": "post",
                "endpoint": f"http://localhost:8080/{operation}",
                "body": body,
            },
            "output": {
                "as": {
                    output_var: "${ . }",
                }
            },
        }
    }
