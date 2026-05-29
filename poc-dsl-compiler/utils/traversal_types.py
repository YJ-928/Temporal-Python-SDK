# utils/traversal_types.py
#
# Typed contract for TraversalEntry — the sole data structure that crosses the
# Phase A / Phase B boundary (compiler → DSL assembler).
#
# All fields that the generator or builders need must be declared here.
# This prevents silent field drift (e.g. "branchmap" vs "branch_map") as new
# node types are added in future phases (PARALLEL, LOOP, JOIN).

from typing import NotRequired, TypedDict


class BranchTarget(TypedDict):
    """Resolved routing target for one branch of an IF node."""
    node_id: str
    task_name: str


class BranchMap(TypedDict):
    """Pre-resolved branch routing for IF nodes. Keys are branch labels."""
    true: BranchTarget
    false: BranchTarget


class TraversalEntry(TypedDict):
    """
    Compiler-computed metadata wrapper for a single traversal step.

    This is the sole interface between Phase A (graph compilation) and
    Phase B (DSL assembly). Builders and the generator must not read raw
    adjacency or node_map — all structural knowledge is pre-computed here
    by traverse_graph().

    Fields
    ------
    node_id
        Node ID shortcut — avoids repeated entry["node"]["id"] in builders
        and in the generator dispatch loop.
    node_type
        Node type shortcut — avoids repeated entry["node"]["type"].
    node
        Original node dict from the graph. READ-ONLY. Never mutate this.
    is_terminal
        True when any direct successor is an END node.
        Builders use this to self-inject ``then: end`` on their emitted task.
    successors
        Ordered list of direct successor node IDs.
    incoming_edge_control
        Full control dict from the parent edge that led to this node,
        or None for the entry-point node (START).

        Storing the full dict (not a derived field like branch_label) keeps
        this field general across all future edge types:
          IF branches:     {"branch": "true"} / {"branch": "false"}
          Phase 2 (LOOP):  {"loop": "back"} / {"loop": "exit"}
          Phase 2 (retry): {"on_error": "retry"}

        Builders derive what they need:
          branch_label = entry["incoming_edge_control"]["branch"]
    branch_map
        For IF nodes only — pre-resolved true/false branch routing.
        None for all other node types.
        Phase 2: PARALLEL will add fork_branches here or as a sibling key.
    """
    node_id: str
    node_type: str
    node: dict
    is_terminal: bool
    successors: list[str]
    incoming_edge_control: NotRequired[dict | None]
    branch_map: NotRequired[BranchMap | None]
