"""
Terminal node builder (START and END nodes).

START and END nodes produce no DSL output.
"""


def build_terminal(node: dict, *, traversal_entry: dict | None = None) -> None:
    """
    START and END nodes produce no DSL task.

    Args:
        node: Node dict from traversal
        traversal_entry: Pre-computed metadata (unused)

    Returns:
        None (master builder skips None returns)
    """
    return None
