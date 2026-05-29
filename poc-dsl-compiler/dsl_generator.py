# ─────────────────────────────────────────────────────────────────────────────
# PHASE B — DSL ASSEMBLY
#
# Ownership: builder dispatch and DSL fragment collection.
#
# This module must not read adjacency, node_map, or any other graph internals.
# All execution semantics (is_terminal, branch routing, incoming_edge_control)
# arrive pre-computed inside TraversalEntry dicts produced by Phase A (compiler.py).
# ─────────────────────────────────────────────────────────────────────────────

import json
import os
from builders.dsl_boilerplate_builder import generate_dsl_boilerplate
from builders.terminal_builder import build_terminal
from builders.input_builder import build_input
from builders.action_builder import build_action
from builders.output_builder import build_output
from builders.wait_builder import build_wait
from builders.if_builder import build_if


# Dispatch table: node type -> builder function
NODE_BUILDERS = {
    "START": build_terminal,
    "INPUT": build_input,
    "ACTION": build_action,
    "OUTPUT": build_output,
    "WAIT": build_wait,
    "IF": build_if,
    "END": build_terminal,
}

def generate_dsl(
    traversal: list,
    compiler_context: dict | None = None,
    dsl_version: str = "1.0.0",
    version: str = "1.0.0",
    workflow_type: str = "compiled-workflow",
    task_queue: str = "zigflow",
) -> dict:
    """
    Build a Zigflow-compatible DSL dict from a pre-computed traversal.

    Args:
        traversal:        Ordered list of TraversalEntry dicts from traverse_graph()
        compiler_context: Deprecated. Retained for call-site compatibility while
                          LOOP/PARALLEL stabilise. Builders now receive all needed
                          metadata via traversal_entry. Pass None or {} safely.
        dsl_version:      DSL spec version string
        version:          Workflow definition version string
        workflow_type:    Temporal workflow type name
        task_queue:       Temporal task queue name

    Returns:
        Zigflow DSL dict: { "document": {...}, "do": [...] }
    """
    dsl = generate_dsl_boilerplate(
        dsl_version=dsl_version,
        version=version,
        workflow_type=workflow_type,
        task_queue=task_queue,
    )

    for entry in traversal:
        node = entry["node"]
        node_type = entry["node_type"]
        builder = NODE_BUILDERS.get(node_type)

        if builder is None:
            # Unknown node type — skip with a warning instead of crashing.
            print(f"[WARNING] No builder for node type '{node_type}' (id={entry['node_id']}). Skipped.")
            continue

        # traversal_entry carries all compiler-computed metadata (is_terminal,
        # branch_map, incoming_edge_control). Builders use it directly.
        # Phase B owns no graph reasoning — that all lives in Phase A.
        fragment = builder(node, traversal_entry=entry, compiler_context=compiler_context)

        if fragment is None:
            # START and END emit no DSL.
            # Traversal already deduplicates shared nodes.
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
