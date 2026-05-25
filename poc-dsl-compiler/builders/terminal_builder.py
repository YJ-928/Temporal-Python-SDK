def build_terminal(node: dict) -> None:
    """
    START and END nodes produce no DSL output.

    The master builder skips None returns and continues iteration.
    """
    print(f"Building {node["type"]}")
    return None
