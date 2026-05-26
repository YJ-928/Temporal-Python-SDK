import json
import os
from builders.dsl_boilerplate_builder import generate_dsl_boilerplate
from builders.terminal_builder import build_terminal
from builders.input_builder import build_input
from builders.action_builder import build_action
from builders.output_builder import build_output
from builders.wait_builder import build_wait


# Dispatch table: node type -> builder function
NODE_BUILDERS = {
    "START": build_terminal,
    "INPUT": build_input,
    "ACTION": build_action,
    "OUTPUT": build_output,
    "WAIT": build_wait,
    "END": build_terminal,
}

def generate_dsl(
    traversal: list,
    dsl_version: str = "1.0.0",
    version: str = "1.0.0",
    workflow_type: str = "compiled-workflow",
    task_queue: str = "zigflow",
) -> dict:
    """
    Build a Zigflow-compatible DSL dict from a pre-computed traversal.

    Args:
        traversal:     Ordered list of node dicts from traverse_graph()
        dsl_version:   DSL spec version string
        version:       Workflow definition version string
        workflow_type: Temporal workflow type name
        task_queue:    Temporal task queue name

    Returns:
        Zigflow DSL dict: { "document": {...}, "do": [...] }
    """
    dsl = generate_dsl_boilerplate(
        dsl_version=dsl_version,
        version=version,
        workflow_type=workflow_type,
        task_queue=task_queue,
    )

    for node in traversal:
        node_type = node["type"]
        builder = NODE_BUILDERS.get(node_type)

        if builder is None:
            # Unknown node type skip with a warning instead of crashing.
            print(f"[WARNING] No builder for node type '{node_type}' (id={node['id']}). Skipped.")
            continue

        fragment = builder(node)

        if fragment is None:
            # START and END emit no DSL.
            # Traversal already deduplicates shared nodes.
            # Safe to continue iteration.
            continue

        dsl["do"].append(fragment)

    return dsl

def save_dsl(dsl: dict, output_path: str) -> None:
    """
    Write the DSL dict to a JSON file at output_path.
    Creates parent directories if they don't exist.

    Args:
        dsl:         DSL dict to serialise
        output_path: Absolute or relative path to the output JSON file
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dsl, f, indent=2)
