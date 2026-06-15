# PHASE B — DSL ASSEMBLY
#
# Ownership: builder dispatch and DSL fragment collection.
#
# This module must not read adjacency, node_map, or any other graph internals.
# All execution semantics (is_terminal, branch routing, incoming_edge_control)
# arrive pre-computed inside TraversalEntry dicts produced by Phase A (compiler.py).

import json
import os
from builders.dsl_boilerplate_builder import generate_dsl_boilerplate
from builders.terminal_builder import build_terminal
from builders.input_builder import build_input
from builders.action_builder import build_action
from builders.output_builder import build_output
from builders.wait_builder import build_wait
from builders.if_builder import build_if
from builders.parallel_builder import build_parallel


# Dispatch table: node type -> builder function
# PARALLEL is handled via a special dispatch path in generate_dsl() because it
# requires pre-built branch do-lists (recursive _build_do_list calls) before
# the builder is invoked.  All other types route through this table.
NODE_BUILDERS = {
    "START": build_terminal,
    "INPUT": build_input,
    "ACTION": build_action,
    "OUTPUT": build_output,
    "WAIT": build_wait,
    "IF": build_if,
    "END": build_terminal,
}

def _build_do_list(branch_traversal: list, compiler_context=None) -> list:
    """
    Build a flat DSL do-list from a pre-computed branch traversal.

    This is the recursive counterpart of generate_dsl() used to produce
    the ``branches[n].do`` lists inside a fork task.  It handles nested
    PARALLEL nodes by calling itself recursively.

    Args:
        branch_traversal: Ordered list of TraversalEntry dicts for one branch.
        compiler_context:  Deprecated pass-through; forwarded to builders.

    Returns:
        List of DSL task dicts in traversal order (None entries excluded).
    """
    result: list = []
    for entry in branch_traversal:
        node = entry["node"]
        node_type = entry["node_type"]

        if node_type == "PARALLEL":
            # Nested PARALLEL: recursively build branch do-lists first.
            parallel_map = entry.get("parallel_map") or {}
            branch_do_lists = {
                bid: _build_do_list(branch_entry["traversal"], compiler_context)
                for bid, branch_entry in parallel_map.items()
            }
            fragment = build_parallel(
                node,
                traversal_entry=entry,
                compiler_context=compiler_context,
                branch_do_lists=branch_do_lists,
            )
        else:
            builder = NODE_BUILDERS.get(node_type)
            if builder is None:
                print(
                    f"[WARNING] No builder for node type '{node_type}' "
                    f"(id={entry['node_id']}) inside branch. Skipped."
                )
                continue
            fragment = builder(node, traversal_entry=entry, compiler_context=compiler_context)

        if fragment is not None:
            result.append(fragment)

    return result


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

        if node_type == "PARALLEL":
            # Special dispatch: branch do-lists must be pre-built here because
            # _build_do_list() lives in this module and builders must not import
            # from dsl_generator.py.  Build them, then hand off to build_parallel().
            parallel_map = entry.get("parallel_map") or {}
            branch_do_lists = {
                bid: _build_do_list(branch_entry["traversal"], compiler_context)
                for bid, branch_entry in parallel_map.items()
            }
            fragment = build_parallel(
                node,
                traversal_entry=entry,
                compiler_context=compiler_context,
                branch_do_lists=branch_do_lists,
            )
        else:
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
