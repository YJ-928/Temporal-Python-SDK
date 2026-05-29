def build_parallel(
    node: dict,
    *,
    traversal_entry=None,
    compiler_context=None,
    branch_do_lists: dict | None = None,
) -> dict:
    """
    Convert a PARALLEL node into a ``fork`` DSL fragment.

    Branch do-lists must be pre-built by the DSL generator (Phase B) before
    this function is called, because building them requires recursive
    ``_build_do_list()`` calls that live in dsl_generator.py.  This builder
    therefore never touches adjacency, node_map, or traversal internals.

    Task name: {node_id}_parallel

    Fork structure
    --------------
    {
      "<id>_parallel": {
        "fork": {
          "compete": <bool>,       # true = race (first wins), false = all must finish
          "branches": [
            { "branch_0": { "do": [...] } },
            { "branch_1": { "do": [...] } },
            ...
          ]
        }
      }
    }

    Notes
    -----
    - PARALLEL nodes are never directly terminal.  The convergence node that
      follows them handles ``then: end`` if needed.
    - ``compete`` defaults to False when absent from node data.
    - Branch order is determined by the sorted branch_id keys (branch_0,
      branch_1, …) which Phase A assigns in outgoing-edge declaration order.

    Args:
        node:             PARALLEL node dict from the graph.
        traversal_entry:  Pre-computed TraversalEntry from Phase A (read-only).
        compiler_context: Deprecated pass-through; never read by this builder.
        branch_do_lists:  Mapping of branch_id -> list of DSL task dicts,
                          pre-built by dsl_generator._build_do_list().

    Returns:
        DSL fragment dict with the fork task.
    """
    node_id = node["id"]
    compete: bool = node.get("data", {}).get("compete", False)
    task_name = f"{node_id}_parallel"

    if branch_do_lists is None:
        branch_do_lists = {}

    branches = [
        {bid: {"do": branch_do_lists[bid]}}
        for bid in sorted(branch_do_lists.keys())
    ]

    return {
        task_name: {
            "fork": {
                "compete": compete,
                "branches": branches,
            }
        }
    }
