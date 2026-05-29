def build_action(node: dict, *, traversal_entry=None, compiler_context=None) -> dict:
    """
    Convert an ACTION node into a call: http DSL fragment.

    The operation name becomes the URL path. Each input maps a workflow
    variable to a request body parameter. The output is stored as a
    named workflow variable via output.as AND persisted to $context via
    export.as so chained actions and later parallel-branch tasks can
    access it even after the flowing data context has been replaced.

    Body expressions read from $context (not from the transient flowing
    data) so they remain valid regardless of how many prior ACTION tasks
    have replaced the flowing context via output.as.

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

    # {param_name: "${ $context.<context_var> }"} - reads each param from
    # $context so variables captured by INPUT (and prior ACTION exports) are
    # available even after a previous ACTION has replaced the flowing data.
    body = {param: f"${{ $context.{ctx_var} }}" for param, ctx_var in input_map.items()}

    # export.as persists the output variable into $context so that chained
    # ACTION nodes (and later tasks in parallel branches) can access it.
    # ".output_var" references the field set by output.as above.
    export_expr = "${ $context + {" + output_var + ": ." + output_var + "} }"

    task_name = f"{node_id}_{operation}"

    fragment = {
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
            "export": {
                "as": export_expr,
            },
        }
    }
    if traversal_entry and traversal_entry["is_terminal"]:
        fragment[task_name]["then"] = "end"
    return fragment
