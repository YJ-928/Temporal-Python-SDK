import asyncio
import json
import re
import urllib.request
from fastapi import APIRouter, HTTPException, status
from temporalio.service import RPCError, RPCStatusCode
from ..config import get_logger
from ..schema.execution.execution_run_sch import (
    ExecuteWorkflowRequest,
    ExecuteWorkflowResponse,
    ExecutionListResponse,
    ExecutionTraceResponse,
)
from ..service.execution_service import execution_service

logger = get_logger(__name__)
router = APIRouter(prefix="/executions", tags=["Executions"])

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


def _check_runtime_sync() -> bool:
    """Blocking probe of the Zigflow runtime health endpoint (run via asyncio.to_thread)."""
    try:
        with urllib.request.urlopen(
            urllib.request.Request("http://localhost:3005/health"), timeout=1
        ) as r:
            return json.loads(r.read()).get("healthy", False)
    except Exception:
        return False


def _check_field(field: str, rules: dict, value) -> str | None:
    """Return an error string for a single contract field, or None if valid."""
    required = rules.get("required", False)
    if required and (value is None or value == ""):
        return f"'{field}' is required."
    is_invalid_email = not isinstance(value, str) or not _EMAIL_RE.match(value.strip())
    if value is not None and rules.get("type") == "email" and is_invalid_email:
        return f"'{field}' must be a valid email address (got: {value!r})."
    return None


def _validate_contract(workflow_id: str, dsl_hash: str, input_data: dict) -> None:
    """
    Load the compiled DSL for this workflow version and validate input_data against
    the metadata.contract block if one is present. Raises HTTP 422 on violations.
    """
    from ..service.storage_service import find_by_hash, load_dsl
    path = find_by_hash(workflow_id, dsl_hash)
    if path is None:
        return

    try:
        dsl = load_dsl(path)
    except Exception:
        return

    contract = dsl.get("document", {}).get("metadata", {}).get("contract", {})
    if not contract:
        return

    errors = [
        msg
        for field, rules in contract.items()
        if (msg := _check_field(field, rules, input_data.get(field))) is not None
    ]

    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Input validation failed: {'; '.join(errors)}",
        )


@router.post(
    "/{workflow_id}/execute",
    response_model=ExecuteWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger workflow execution",
    description=(
        "Starts a new workflow run on Temporal using the versioned compiled DSL matching the provided content hash."
    )
)
async def execute_workflow(workflow_id: str, request: ExecuteWorkflowRequest):
    # 1. Check if hash is registered and validated
    from ..service.registration_service import registration_service
    if not registration_service.is_registered(request.dsl_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow version is not registered. Please recompile and try again."
        )

    # 2. Check if it's hot-reloaded/runtime-loaded into the worker
    if not registration_service.is_runtime_loaded(request.dsl_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workflow is warming up. Please try again in a few seconds."
        )

    # 3. Check if runtime is healthy (bounded to 2s so a hanging daemon doesn't stall the handler)
    try:
        runtime_healthy = await asyncio.wait_for(
            asyncio.to_thread(_check_runtime_sync), timeout=2.0
        )
    except asyncio.TimeoutError:
        logger.warning("Runtime health check timed out after 2s")
        runtime_healthy = False

    if not runtime_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow runtime is offline. Please contact support or try again later."
        )

    # Validate input against compiled DSL contract (email format, required fields)
    _validate_contract(workflow_id, request.dsl_hash, request.input)

    try:
        result = await execution_service.execute_workflow(
            workflow_id=workflow_id,
            dsl_hash=request.dsl_hash,
            input_payload=request.input
        )
        return ExecuteWorkflowResponse(**result)
    except FileNotFoundError as e:
        logger.warning(f"Compiled workflow not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compiled workflow not found."
        ) from e
    except ValueError as e:
        logger.warning(f"Invalid DSL configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid workflow configuration."
        ) from e
    except Exception as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start workflow execution."
        ) from e


@router.get(
    "/{workflow_id}/history",
    response_model=ExecutionListResponse,
    summary="List past workflow executions",
    description="Queries Temporal visibility history to retrieve recent runs for this workflow."
)
async def list_executions(workflow_id: str):
    try:
        executions = await execution_service.list_executions(workflow_id)
        return ExecutionListResponse(executions=executions)
    except Exception as e:
        logger.error(f"Failed to retrieve history for {workflow_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch execution history."
        ) from e


@router.get(
    "/{workflow_id}/{run_id}/trace",
    response_model=ExecutionTraceResponse,
    summary="Get execution trace history",
    description="Parses Temporal event history for a run to map execution state back to ReactFlow canvas nodes."
)
async def get_execution_trace(workflow_id: str, run_id: str):
    try:
        trace = await execution_service.get_execution_trace(workflow_id, run_id)
        return ExecutionTraceResponse(**trace)
    except RPCError as e:
        if e.status == RPCStatusCode.NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow execution not found."
            ) from e
        logger.error(f"Temporal RPC error fetching trace for {workflow_id}/{run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch execution trace."
        ) from e
    except Exception as e:
        logger.error(f"Failed to retrieve trace for workflow {workflow_id} run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch execution trace."
        ) from e


@router.post(
    "/{workflow_id}/{run_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel a running workflow execution",
    description="Gracefully requests cancellation of the executing Temporal workflow."
)
async def cancel_workflow(workflow_id: str, run_id: str):
    try:
        await execution_service.cancel_workflow(workflow_id, run_id)
        return {"success": True, "message": "Cancellation requested successfully"}
    except Exception as e:
        logger.error(f"Failed to cancel workflow {workflow_id} run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel workflow."
        ) from e


@router.post(
    "/{workflow_id}/{run_id}/terminate",
    status_code=status.HTTP_200_OK,
    summary="Terminate a running workflow execution",
    description="Forcefully terminates the executing Temporal workflow."
)
async def terminate_workflow(workflow_id: str, run_id: str, reason: str = "Terminated by user"):
    try:
        await execution_service.terminate_workflow(workflow_id, run_id, reason)
        return {"success": True, "message": "Workflow terminated successfully"}
    except Exception as e:
        logger.error(f"Failed to terminate workflow {workflow_id} run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to terminate workflow."
        ) from e
