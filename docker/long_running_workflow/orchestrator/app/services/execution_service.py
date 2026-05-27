"""Execution orchestration service.

Coordinates between the API layer, the Docker service, and the execution store.
All public functions are async and safe to call from FastAPI route handlers.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

from app.docker.docker_service import DockerService
from app.models.execution import ExecutionRecord, ExecutionStatus, ExecutionStore
from app.utils.config import get_settings

logger = logging.getLogger(__name__)

# ── Module-level singletons ────────────────────────────────────────────────────
# These are created once at import time and shared across all requests.
_execution_store = ExecutionStore()
_docker_service = DockerService()


def get_execution_store() -> ExecutionStore:
    return _execution_store


def get_docker_service() -> DockerService:
    return _docker_service


# ── Core orchestration ────────────────────────────────────────────────────────

async def execute_workflow(
    workflow: str,
    workflow_path: str,
    input_data: Dict[str, Any],
) -> ExecutionRecord:
    """
    Validate the workflow, spin up an isolated container, collect the result,
    and return the final ``ExecutionRecord``.

    Raises
    ------
    FileNotFoundError
        If ``workflow_path`` does not exist on the orchestrator's filesystem.
    """
    settings = get_settings()

    # Resolve path if caller passed a relative name
    if not os.path.isabs(workflow_path):
        workflow_path = os.path.join(settings.WORKFLOWS_DIR, workflow)

    if not os.path.isfile(workflow_path):
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")

    record = _execution_store.create(workflow, workflow_path, input_data)
    execution_id = record.execution_id

    logger.info(
        "Execution created",
        extra={"execution_id": execution_id, "workflow": workflow},
    )
    _execution_store.update(execution_id, status=ExecutionStatus.RUNNING)

    try:
        container_id, result, logs, error = await _docker_service.run_workflow_container(
            workflow=workflow,
            workflow_path=workflow_path,
            input_data=input_data,
            execution_id=execution_id,
            timeout_secs=settings.EXECUTION_TIMEOUT_SECONDS,
        )

        if error:
            _execution_store.update(
                execution_id,
                status=ExecutionStatus.FAILED,
                container_id=container_id,
                logs=logs,
                error=error,
            )
            logger.error(
                "Execution failed",
                extra={"execution_id": execution_id, "error": error},
            )
        else:
            _execution_store.update(
                execution_id,
                status=ExecutionStatus.COMPLETED,
                container_id=container_id,
                result=result,
                logs=logs,
            )
            logger.info(
                "Execution completed",
                extra={"execution_id": execution_id, "container_id": container_id},
            )

    except FileNotFoundError:
        raise
    except Exception as exc:
        logger.exception("Unexpected error for execution %s", execution_id)
        _execution_store.update(
            execution_id,
            status=ExecutionStatus.FAILED,
            error=f"Internal error: {exc}",
        )

    return _execution_store.get(execution_id)  # type: ignore[return-value]
