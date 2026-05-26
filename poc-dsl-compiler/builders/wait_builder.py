def build_wait(node: dict) -> dict:
    """
    Convert a WAIT node into a wait DSL fragment.

    The duration dict from node data is passed directly to the Zigflow
    wait task. Supported keys: seconds, minutes, hours.

    Task name: {node_id}_wait

    Args:
        node: WAIT node dict from traversal

    Returns:
        DSL fragment dict with wait task
    """
    node_id = node["id"]
    duration = node["data"]["duration"]  # e.g. {"seconds": 30} or {"minutes": 1}

    task_name = f"{node_id}_wait"

    return {
        task_name: {
            "wait": duration,
        }
    }
