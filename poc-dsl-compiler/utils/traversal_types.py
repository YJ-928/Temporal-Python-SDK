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


class ParallelBranchEntry(TypedDict):
    """
    Metadata for one branch of a PARALLEL node.

    branch_id
        Stable identifier for this branch (e.g. "branch_0", "branch_1").
        Assigned by Phase A in declaration order of the outgoing edges.
    entry_node_id
        Node ID of the first node in this branch (the direct successor of
        the PARALLEL node along this edge).
    traversal
        Ordered list of TraversalEntry dicts for the nodes inside this branch,
        in DFS preorder. Does NOT include the PARALLEL node itself or the
        convergence node. May itself contain nested PARALLEL entries.
    """
    branch_id: str
    entry_node_id: str
    traversal: list  # list[TraversalEntry] — forward reference avoids circular TypedDict


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
    parallel_map
        For PARALLEL nodes only — pre-resolved branch traversals.
        Keys are branch IDs ("branch_0", "branch_1", ...) in declaration
        order of outgoing edges from the PARALLEL node.
        None for all other node types.
    reads_from_context
        Set to True on the convergence node of a PARALLEL (the node
        immediately after the branches rejoin). Signals output_builder
        and any other builder that reads accumulated data to source field
        values from ``$context`` rather than the transient flowing data.
        False for all other nodes (including the default when absent).
    """
    node_id: str
    node_type: str
    node: dict
    is_terminal: bool
    successors: list[str]
    incoming_edge_control: NotRequired[dict | None]
    branch_map: NotRequired[BranchMap | None]
    parallel_map: NotRequired[dict | None]  # dict[str, ParallelBranchEntry] | None
    reads_from_context: NotRequired[bool]
