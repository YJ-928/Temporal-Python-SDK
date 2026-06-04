"""
Phase B: DSL Generation

Dispatches to node-specific builders to assemble Zigflow DSL.
"""
from typing import Any, Callable
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
) -> dict:
    """
    Build Zigflow DSL from traversal.

    Args:
        traversal: Ordered list of TraversalEntry dicts from compiler
        dsl_version: DSL spec version
        version: Workflow version
        workflow_type: Temporal workflow type
        task_queue: Temporal task queue name

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
            do_list.append(fragment)

    return {
        "document": {
            "dsl": dsl_version,
            "taskQueue": task_queue,
            "workflowType": workflow_type,
            "version": version,
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
    with open(output_path, "w") as f:
        json.dump(dsl, f, indent=2)
