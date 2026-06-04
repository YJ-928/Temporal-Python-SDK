"""
AGENT node builder.

Converts AGENT node into a Zigflow `run: workflow` task for sub-workflow invocation.
"""


def build_agent(node: dict, *, traversal_entry: dict | None = None) -> dict:
    """
    Convert AGENT node into a run: workflow DSL fragment.

    Reads the selected agent ID and invokes it as a sub-workflow.

    Task name: {node_id}_agent

    Args:
        node: AGENT node dict from traversal
        traversal_entry: Pre-computed metadata

    Returns:
        DSL fragment dict with run: workflow task
    """
    node_id = node["id"]
    agent_id = node["data"]["agent"]

    task_name = f"{node_id}_agent"

    # Export agent result to $context under "agent_result"
    export_expr = "${ $context + {agent_result: .} }"

    fragment = {
        task_name: {
            "run": {
                "workflow": {
                    "type": agent_id,
                    "input": {},  # Pass empty object as input to the sub-workflow
                },
            },
            "export": {
                "as": export_expr,
            },
        }
    }

    if traversal_entry and traversal_entry.get("is_terminal"):
        fragment[task_name]["then"] = "end"

    return fragment
