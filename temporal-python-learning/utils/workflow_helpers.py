"""
Workflow Helpers

Convenience functions for starting and querying Workflows.

Usage:
    from utils.workflow_helpers import start_workflow, execute_workflow
"""

from __future__ import annotations

from typing import Any, Type

from temporalio.client import Client, WorkflowHandle


async def start_workflow(
    client: Client,
    workflow_cls: Type,
    arg: Any,
    *,
    workflow_id: str,
    task_queue: str,
) -> WorkflowHandle:
    """Start a Workflow and return its handle (does not wait for completion).

    Args:
        client: A connected Temporal client.
        workflow_cls: The ``@workflow.defn`` class.
        arg: The single argument to pass to the Workflow's ``run`` method.
        workflow_id: A unique identifier for the Workflow execution.
        task_queue: The Task Queue that Workers are polling.

    Returns:
        A :class:`WorkflowHandle` for the running Workflow.
    """
    handle = await client.start_workflow(
        workflow_cls.run,
        arg,
        id=workflow_id,
        task_queue=task_queue,
    )
    return handle


async def execute_workflow(
    client: Client,
    workflow_cls: Type,
    arg: Any,
    *,
    workflow_id: str,
    task_queue: str,
) -> Any:
    """Start a Workflow and wait for its result.

    This is a thin wrapper around ``client.execute_workflow`` that keeps the
    calling code consistent with :func:`start_workflow`.
    """
    return await client.execute_workflow(
        workflow_cls.run,
        arg,
        id=workflow_id,
        task_queue=task_queue,
    )


async def get_workflow_result(
    client: Client,
    workflow_id: str,
) -> Any:
    """Retrieve the result of a previously started Workflow by its ID."""
    handle = client.get_workflow_handle(workflow_id)
    return await handle.result()
