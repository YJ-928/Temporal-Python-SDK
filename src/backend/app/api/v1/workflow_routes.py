"""
Workflow compilation API routes.
"""
from fastapi import APIRouter, HTTPException, status
from ...config import get_logger, compiler_settings
from ...services import compiler_service, load_dsl, get_latest_workflow
from ...schemas.compiler_sch import (
    CompileWorkflowRequest,
    CompileWorkflowResponse,
    GetWorkflowResponse,
    ErrorResponse,
)


logger = get_logger(__name__)
router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post(
    "/compile",
    response_model=CompileWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid workflow JSON"},
        500: {"model": ErrorResponse, "description": "Compilation failed"},
    },
)
async def compile_workflow(request: CompileWorkflowRequest):
    """
    Compile workflow JSON to Zigflow DSL.

    Args:
        request: Workflow JSON with nodes and edges

    Returns:
        CompileWorkflowResponse with workflow_id, DSL, and file_path
    """
    try:
        from datetime import datetime, timezone
        workflow = {
            "nodes": [node.model_dump() for node in request.nodes],
            "edges": [edge.model_dump() for edge in request.edges],
        }

        resolved_workflow_type = request.workflow_type or compiler_settings.workflow_type
        resolved_task_queue = request.task_queue or compiler_settings.task_queue
        resolved_version = request.version or "1.0.0"
        resolved_description = request.description or ""

        result = compiler_service.compile_and_save(
            workflow=workflow,
            workflow_type=resolved_workflow_type,
            task_queue=resolved_task_queue,
            version=resolved_version,
            description=resolved_description,
            workflow_id=request.workflow_id,
        )

        logger.info(f"Compiled workflow: {result['workflow_id']} (hash: {result['content_hash']})")

        # Register the compiled workflow version (hot-reloads runtime in background)
        from ...services.registration_service import registration_service
        registration_service.register_workflow(
            dsl_hash=result["content_hash"],
            workflow_id=result["workflow_id"],
            workflow_type=resolved_workflow_type,
            file_path=result["file_path"],
        )

        generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        return CompileWorkflowResponse(
            success=True,
            workflow_id=result["workflow_id"],
            dsl=result["dsl"],
            file_path=str(result["file_path"]),
            content_hash=result["content_hash"],
            generated_at=generated_at,
        )

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Compilation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compilation failed: {str(e)}",
        )


@router.get(
    "/{workflow_id}",
    response_model=GetWorkflowResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Workflow not found"},
        500: {"model": ErrorResponse, "description": "Failed to load workflow"},
    },
)
async def get_workflow(workflow_id: str):
    """
    Retrieve compiled DSL by workflow ID.

    Args:
        workflow_id: Workflow identifier

    Returns:
        GetWorkflowResponse with workflow_id and DSL
    """
    try:
        file_path = get_latest_workflow(workflow_id)

        if not file_path:
            logger.warning(f"Workflow not found: {workflow_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow '{workflow_id}' not found",
            )

        dsl = load_dsl(file_path)
        logger.info(f"Retrieved workflow: {workflow_id}")

        return GetWorkflowResponse(
            success=True,
            workflow_id=workflow_id,
            dsl=dsl,
            file_path=str(file_path),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load workflow: {str(e)}",
        )
