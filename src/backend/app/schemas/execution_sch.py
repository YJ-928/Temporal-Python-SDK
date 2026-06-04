from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List, Optional


class ExecuteWorkflowRequest(BaseModel):
    """Request schema for triggering a workflow execution."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dsl_hash": "a8d23e91c1bfe345",
                "input": {
                    "user_id": "12345"
                }
            }
        }
    )

    dsl_hash: str = Field(..., description="SHA-256 content hash of the compiled workflow version to run")
    input: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input parameters passed to the workflow execution context"
    )


class ExecuteWorkflowResponse(BaseModel):
    """Response schema for triggered workflow execution."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "workflow_id": "rf-my-awesome-flow-a1b2c3d4",
                "run_id": "019e906b-b52f-7bcf-8034-8c6223511083",
                "workflow_type": "fetch-user",
                "status": "RUNNING"
            }
        }
    )

    workflow_id: str = Field(..., description="Unique Temporal ID assigned to the workflow run")
    run_id: str = Field(..., description="Execution Run ID of the workflow run")
    workflow_type: str = Field(..., description="Registered type name of the workflow")
    status: str = Field("RUNNING", description="Initial execution status")


class ExecutionListItem(BaseModel):
    """Execution details for list queries."""
    workflow_id: str
    run_id: str
    workflow_type: str
    status: str
    start_time: Optional[str] = None
    close_time: Optional[str] = None


class ExecutionListResponse(BaseModel):
    """Response schema listing workflow executions."""
    executions: List[ExecutionListItem]


class TraceStepResponse(BaseModel):
    """Execution status and input/output for a single graph node step."""
    status: str = Field(..., description="Step status: completed, running, failed, or scheduled")
    input: Optional[Dict[str, Any]] = Field(None, description="Decoded input data passed to the step")
    output: Optional[Dict[str, Any]] = Field(None, description="Decoded output data returned by the step")
    error: Optional[str] = Field(None, description="Error message if the step failed")


class ExecutionTraceResponse(BaseModel):
    """Response schema returning execution traces mapped to ReactFlow node IDs."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "run_id": "019e906b-b52f-7bcf-8034-8c6223511083",
                "steps": {
                    "N2_capture": {
                        "status": "completed",
                        "input": {"user_id": "12345"},
                        "output": {"id": "12345"}
                    },
                    "N3_get_user": {
                        "status": "completed",
                        "input": {"id": "12345"},
                        "output": {"name": "Leanne Graham", "email": "Sincere@april.biz"}
                    }
                }
            }
        }
    )

    run_id: str = Field(..., description="Temporal execution Run ID being traced")
    status: str = Field(..., description="Temporal workflow execution status (e.g. RUNNING, COMPLETED, FAILED)")
    steps: Dict[str, TraceStepResponse] = Field(
        default_factory=dict,
        description="Map of ReactFlow node IDs to their step execution statuses"
    )
