def generate_dsl_boilerplate(
    dsl_version: str,
    version: str,
    workflow_type: str,
    task_queue: str,
) -> dict:
    """
    Return the base DSL document with an empty do list.

    The master builder feeds task fragments into dsl["do"].

    Args:
        dsl_version:   DSL spec version (e.g. "1.0.0")
        version:       Workflow definition version (e.g. "1.0.0")
        workflow_type: Temporal workflow type name
        task_queue:    Temporal task queue name

    Returns:
        {
          "document": { "dsl": ..., "taskQueue": ..., "workflowType": ..., "version": ... },
          "do": []
        }
    """
    return {
        "document": {
            "dsl": dsl_version,
            "taskQueue": task_queue,
            "workflowType": workflow_type,
            "version": version,
            "metadata": {},
        },
        "do": [],
    }
