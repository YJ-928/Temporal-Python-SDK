"""FastAPI route definitions for the Execution Orchestrator API."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.requests import ExecuteWorkflowRequest
from app.schemas.responses import ExecutionListResponse, ExecutionResponse
from app.services.execution_service import execute_workflow, get_execution_store
from app.docker.docker_service import DockerService

logger = logging.getLogger(__name__)
router = APIRouter()


# Helpers

def _to_response(record) -> ExecutionResponse:
    return ExecutionResponse(
        status=record.status,
        workflow=record.workflow,
        executionId=record.execution_id,
        containerId=record.container_id,
        result=record.result,
        logs=record.logs,
        error=record.error,
        createdAt=record.created_at,
        updatedAt=record.updated_at,
    )


# Routes

@router.post(
    "/execute",
    response_model=ExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a Zigflow workflow in an isolated Docker container",
    description=(
        "Validates the workflow file, creates an ephemeral Docker container, runs "
        "the specified Zigflow workflow, collects the structured output, destroys "
        "the container, and returns the execution result.\n\n"
        "This call **blocks** until the container exits. For long-running workflows "
        "set an appropriate client timeout (default container timeout is 1 hour)."
    ),
)
async def execute(request: ExecuteWorkflowRequest) -> ExecutionResponse:
    try:
        record = await execute_workflow(
            workflow=request.workflow,
            workflow_path=request.workflowPath,
            input_data=request.input,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error executing workflow %s", request.workflow)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution failed: {exc}",
        ) from exc

    return _to_response(record)


@router.get(
    "/executions",
    response_model=ExecutionListResponse,
    summary="List all workflow executions",
)
async def list_executions() -> ExecutionListResponse:
    store = get_execution_store()
    records = store.list_all()
    # Return newest first
    records.sort(key=lambda r: r.created_at, reverse=True)
    return ExecutionListResponse(
        executions=[_to_response(r) for r in records],
        total=len(records),
    )


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionResponse,
    summary="Get a single execution by ID",
)
async def get_execution(execution_id: str) -> ExecutionResponse:
    store = get_execution_store()
    record = store.get(execution_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution '{execution_id}' not found",
        )
    return _to_response(record)


@router.get("/health", summary="Service health check")
async def health() -> dict:
    docker_ok = DockerService().health_check()
    return {
        "status": "healthy" if docker_ok else "degraded",
        "docker": "connected" if docker_ok else "disconnected",
    }
