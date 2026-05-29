def _build_wait_duration(node_id: str, config: dict) -> dict:
    """
    Emit a Zigflow wait task for a timed pause.

    Args:
        node_id: node ID from the graph (used as task name prefix)
        config:  dict with exactly one time-unit key: seconds, minutes, or hours

    Returns:
        DSL fragment: { "{node_id}_wait": { "wait": config } }
    """
    task_name = f"{node_id}_wait"
    return {
        task_name: {
            "wait": config,
        }
    }

def _build_wait_listen(node_id: str, config: dict) -> dict:
    """
    Emit a Zigflow listen task for an external signal.

    Args:
        node_id: node ID from the graph (used as task name prefix)
        config:  dict with key "signal" — the Temporal signal name to wait for

    Returns:
        DSL fragment: { "{node_id}_wait": { "listen": { "to": { "one": { "with": { "id": signal } } } } } }
    """
    task_name = f"{node_id}_wait"
    return {
        task_name: {
            "listen": {
                "to": {
                    "one": {
                        "with": {
                            "id": config["signal"],
                        }
                    }
                }
            }
        }
    }

def build_wait(node: dict, *, traversal_entry=None, compiler_context=None) -> dict:
    """
    Convert a WAIT node into a wait or listen DSL fragment.

    Dispatches internally based on node["data"]["mode"]:
      - "duration" → Zigflow wait task (timed pause)
      - "listen"   → Zigflow listen task (external signal)

    Task name: {node_id}_wait

    Args:
        node: WAIT node dict from traversal

    Returns:
        DSL fragment dict — either a wait task or a listen task
    """
    node_id = node["id"]
    data = node["data"]
    mode = data["mode"]
    config = data["config"]
    if mode == "listen":
        fragment = _build_wait_listen(node_id, config)
    else:
        # mode == "duration"
        fragment = _build_wait_duration(node_id, config)

    task_name = f"{node_id}_wait"
    if traversal_entry and traversal_entry["is_terminal"]:
        fragment[task_name]["then"] = "end"
    return fragment
