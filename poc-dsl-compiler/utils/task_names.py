TASK_NAME_RESOLVERS: dict[str, object] = {
    "ACTION":   lambda node: f"{node['id']}_{node['data']['operation']}",
    "INPUT":    lambda node: f"{node['id']}_capture",
    "OUTPUT":   lambda node: f"{node['id']}_expose",
    "WAIT":     lambda node: f"{node['id']}_wait",
    "IF":       lambda node: f"{node['id']}_if",
    "PARALLEL": lambda node: f"{node['id']}_parallel",
}

def resolve_task_name(node: dict) -> str:
    """
    Return the DSL task name that the given node's builder will emit.

    START and END nodes produce no DSL task (terminal_builder returns None)
    and must never reach this function. Any unrecognised type raises
    ValueError rather than silently falling back to the bare node ID —
    an unknown name in switch/fork branches would only fail at Zigflow
    runtime, not at compile time.

    Args:
        node: Full node dict from node_map (must have "id" and "type").

    Returns:
        The string task name that will appear as the key in the DSL do list.

    Raises:
        ValueError: If the node type has no naming rule defined.
    """
    resolver = TASK_NAME_RESOLVERS.get(node["type"])
    if resolver is None:
        raise ValueError(
            f"No task naming rule for node type {node['type']!r} "
            f"(node id: {node['id']!r}). "
            f"START and END nodes must not be passed to resolve_task_name()."
        )
    return resolver(node)
