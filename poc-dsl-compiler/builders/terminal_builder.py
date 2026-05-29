def build_terminal(node: dict, *, traversal_entry=None, compiler_context=None) -> None:
    """
    START and END nodes produce no DSL output.

    The master builder skips None returns and continues iteration.
    """
    print(f"Building {node["type"]}")
    return None
