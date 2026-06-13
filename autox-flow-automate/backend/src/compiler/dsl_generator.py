"""
Phase B: DSL Generation

Dispatches to node-specific builders to assemble Zigflow DSL.
"""
from typing import Callable
from ..config import get_logger


logger = get_logger(__name__)

# Builder registry populated by individual builder modules
BUILDER_REGISTRY: dict[str, Callable] = {}


def register_builder(node_type: str, builder_fn: Callable) -> None:
    """
    Register a builder function for a node type.

    Args:
        node_type: Node type string (START, INPUT, etc.)
        builder_fn: Callable that takes (node, traversal_entry) and returns DSL fragment dict or None
    """
    BUILDER_REGISTRY[node_type] = builder_fn


def generate_dsl(
    traversal: list[dict],
    dsl_version: str,
    version: str,
    workflow_type: str,
    task_queue: str,
    description: str = "",
) -> dict:
    """
    Build Zigflow DSL from traversal.

    Args:
        traversal: Ordered list of TraversalEntry dicts from compiler
        dsl_version: DSL spec version
        version: Workflow version
        workflow_type: Temporal workflow type
        task_queue: Temporal task queue name
        description: Workflow description

    Returns:
        Complete Zigflow DSL dict
    """
    do_list: list[dict] = []

    for entry in traversal:
        node = entry["node"]
        node_type = entry["node_type"]

        builder = BUILDER_REGISTRY.get(node_type)

        if builder is None:
            logger.warning(f"No builder registered for node type '{node_type}' (id={entry['node_id']}). Skipped.")
            continue

        fragment = builder(node, traversal_entry=entry)

        if fragment is not None:
            # Wrap conditional branch targets in subflow do blocks
            incoming_control = entry.get("incoming_edge_control")
            is_branch_target = (
                incoming_control is not None
                and incoming_control.get("branch") in ("true", "false")
            )
            if is_branch_target:
                task_name = list(fragment.keys())[0]
                task_body = fragment[task_name]
                inner_name = f"{task_name}_inner"

                # Propagate transition to the outer wrapper level
                then_target = task_body.pop("then", None)

                fragment = {
                    task_name: {
                        "do": [
                            {
                                inner_name: task_body
                            }
                        ]
                    }
                }
                if then_target:
                    fragment[task_name]["then"] = then_target
            do_list.append(fragment)

    return {
        "document": {
            "dsl": dsl_version,
            "taskQueue": task_queue,
            "workflowType": workflow_type,
            "version": version,
            "summary": description,
        },
        "do": do_list,
    }


def save_dsl(dsl: dict, output_path: str) -> None:
    """
    Save DSL to JSON file.

    Args:
        dsl: Complete DSL dict
        output_path: File path to write
    """
    import json
    with output_path.open("w") as f:
        json.dump(dsl, f, indent=2)
