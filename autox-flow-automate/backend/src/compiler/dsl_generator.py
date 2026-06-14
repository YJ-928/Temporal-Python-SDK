"""
Phase B: DSL Generation

Dispatches to node-specific builders to assemble Zigflow DSL.
"""
from typing import Callable
from ..config import get_logger, settings


logger = get_logger(__name__)

# Builder registry populated by individual builder modules
BUILDER_REGISTRY: dict[str, Callable] = {}


def register_builder(node_type: str, builder_fn: Callable) -> None:
    BUILDER_REGISTRY[node_type] = builder_fn


def _set_map_to_export_expr(set_map: dict) -> str:
    """Build a jq merge expression that re-captures set-map keys from $context."""
    if not set_map:
        return "${ $context }"
    fields = ", ".join(f"{k}: $context.{k}" for k in set_map)
    return "${ $context + {" + fields + "} }"


def _wrap_as_child_workflow(fragment: dict) -> dict:
    """Wrap a DSL fragment as a Zigflow child workflow do-block.

    Zigflow dispatches switch/then targets as child workflows, so all branch
    targets must live inside a `do` block. `set`-only inner tasks are not
    valid in that context; they are converted to a noop HTTP call + export
    so Zigflow can execute the branch without errors.
    """
    task_name = next(iter(fragment))
    task_body = fragment[task_name]
    inner_name = f"{task_name}_inner"
    then_target = task_body.pop("then", None)

    if "set" in task_body and "call" not in task_body:
        inner_body: dict = {
            "call": "http",
            "with": {
                "method": "post",
                "endpoint": f"{settings.ACTIONS_BASE_URL}/api/v1/actions/noop",
                "headers": {"Content-Type": "application/json"},
                "body": "{}",
            },
            "export": {"as": _set_map_to_export_expr(task_body.get("set", {}))},
        }
    else:
        inner_body = task_body

    wrapped: dict = {task_name: {"do": [{inner_name: inner_body}]}}
    if then_target:
        wrapped[task_name]["then"] = then_target
    return wrapped


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
            incoming_control = entry.get("incoming_edge_control")
            is_branch_target = (
                incoming_control is not None
                and incoming_control.get("branch") in ("true", "false")
            )
            if is_branch_target:
                fragment = _wrap_as_child_workflow(fragment)
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
