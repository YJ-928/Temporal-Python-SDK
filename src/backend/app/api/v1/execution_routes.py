from fastapi import APIRouter, HTTPException, status
from ...config import get_logger
from ...schemas.execution_sch import (
    ExecuteWorkflowRequest,
    ExecuteWorkflowResponse,
    ExecutionListResponse,
    ExecutionTraceResponse,
)
from ...services.execution_service import execution_service

logger = get_logger(__name__)
router = APIRouter(prefix="/executions", tags=["Executions"])


@router.post(
    "/{workflow_id}/execute",
    response_model=ExecuteWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger workflow execution",
    description="Starts a new workflow run on Temporal using the versioned compiled DSL matching the provided content hash."
)
async def execute_workflow(workflow_id: str, request: ExecuteWorkflowRequest):
    # 1. Check if hash is registered and validated
    from ...services.registration_service import registration_service
    if not registration_service.is_registered(request.dsl_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow version (hash {request.dsl_hash}) is not registered."
        )

    # 2. Check if it's hot-reloaded/runtime-loaded into the worker
    if not registration_service.is_runtime_loaded(request.dsl_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow version (hash {request.dsl_hash}) is still pending runtime loading."
        )

    # 3. Check if runtime is healthy
    import urllib.request
    import json
    runtime_healthy = False
    try:
        req = urllib.request.Request("http://localhost:3005/health")
        with urllib.request.urlopen(req, timeout=1) as r:
            res = json.loads(r.read())
            runtime_healthy = res.get("healthy", False)
    except Exception:
        pass

    if not runtime_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Zigflow Runtime Daemon is offline or unhealthy."
        )

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
            detail=str(e)
        )
    except ValueError as e:
        logger.warning(f"Invalid DSL configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow execution: {e}"
        )


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
            detail=f"Failed to fetch execution history: {e}"
        )


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
    except Exception as e:
        logger.error(f"Failed to retrieve trace for workflow {workflow_id} run {run_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch execution trace: {e}"
        )


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
            detail=f"Failed to cancel workflow: {e}"
        )


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
            detail=f"Failed to terminate workflow: {e}"
        )
