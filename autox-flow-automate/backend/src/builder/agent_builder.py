"""
AGENT node builder.

Converts AGENT node into a Zigflow `call: http` task using AgentRegistry.
"""
from ..agent.registry import AgentRegistry


def build_agent(node: dict, *, traversal_entry: dict | None = None) -> dict:
    """
    Convert AGENT node into a call: http DSL fragment.

    Reads the selected agent ID, looks it up in AgentRegistry,
    and compiles it to a Zigflow native HTTP call task.

    Task name: {node_id}_agent

    Args:
        node: AGENT node dict from traversal
        traversal_entry: Pre-computed metadata

    Returns:
        DSL fragment dict with call: http task
    """
    node_id = node["id"]
    agent_id = node["data"]["agent"]
    inputs = node["data"].get("inputs") or {}
    output_name = node["data"].get("output") or "agent_result"
    output_path = node["data"].get("output_path")

    # Lookup agent metadata
    agent_meta = AgentRegistry.get_agent(agent_id)
    if not agent_meta:
        # Fallback local URL if not registered
        endpoint = "http://localhost:11000/execute"
        method = "post"
    else:
        endpoint = agent_meta["url"]
        method = agent_meta.get("method", "POST").lower()

    task_name = f"{node_id}_agent"

    # Determine JQ output/export selector path
    selector = f".{output_path}" if output_path else "."
    # Export the selected HTTP response part/whole into $context under output_name
    export_expr = f"${{ $context + {{{output_name}: {selector}}} }}"

    fragment = {
        task_name: {
            "call": "http",
            "with": {
                "method": method,
                "endpoint": endpoint,
                "headers": {
                    "Content-Type": "application/json"
                },
            },
            "export": {
                "as": export_expr,
            },
        }
    }

    # Construct input body for HTTP call.
    # Zigflow call:http body must be a single JQ expression that evaluates to an
    # object at runtime — NOT a dict with per-field JQ strings (which Zigflow
    # would JSON-encode as a string before sending).
    # Correct:  "body": "${ {city: $context.city} }"
    # Wrong:    "body": {"city": "${ $context.city }"}
    if inputs:
        # Build JQ object literal: {key1: $context.var1, key2: $context.var2, ...}
        jq_pairs = ", ".join(
            f"{input_key}: $context.{context_var}"
            for input_key, context_var in inputs.items()
        )
        body_expr = f"${{ {{{jq_pairs}}} }}"
        fragment[task_name]["with"]["body"] = body_expr

    if traversal_entry:
        then_val = traversal_entry.get("then_transition")
        if not then_val and traversal_entry.get("is_terminal"):
            then_val = "end"
        if then_val:
            fragment[task_name]["then"] = then_val

    return fragment
