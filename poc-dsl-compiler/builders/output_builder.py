def build_output(node: dict, *, traversal_entry=None, compiler_context=None) -> dict:
    """
    Convert an OUTPUT node into a set DSL fragment.

    Each output field is read from the current workflow data and written into
    the final output object.  When the OUTPUT node is the convergence point
    after a PARALLEL (``reads_from_context=True`` in traversal_entry), branch
    ACTION outputs land in ``$context`` rather than the transient flowing data,
    so the expression source switches to ``$context.<field>`` accordingly.

    Task name: {node_id}_expose

    Args:
        node:            OUTPUT node dict from traversal.
        traversal_entry: Pre-computed TraversalEntry from Phase A (read-only).
        compiler_context: Deprecated pass-through; never read by this builder.

    Returns:
        DSL fragment dict with set task.
    """
    node_id = node["id"]
    raw_outputs = node["data"]["outputs"]
    reads_from_ctx = bool(traversal_entry and traversal_entry.get("reads_from_context"))

    set_map = {}
    for entry in raw_outputs:
        field = entry["field"]
        if reads_from_ctx:
            # Branch ACTION exports flow into $context; read from there.
            set_map[field] = f"${{ $context.{field} }}"
        else:
            set_map[field] = f"${{ .{field} }}"

    task_name = f"{node_id}_expose"

    fragment = {
        task_name: {
            "set": set_map,
        }
    }
    if traversal_entry and traversal_entry["is_terminal"]:
        fragment[task_name]["then"] = "end"
    return fragment
