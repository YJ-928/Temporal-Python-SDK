"""Pydantic v2 response schemas."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.execution import ExecutionStatus


class ExecutionResponse(BaseModel):
    """Structured response for a single workflow execution."""

    status: ExecutionStatus
    workflow: str
    executionId: str
    containerId: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    logs: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    createdAt: float
    updatedAt: float

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "completed",
                "workflow": "hello-world.json",
                "executionId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "containerId": "a1b2c3d4e5f6",
                "result": {"greeting": "Hello, Yash!"},
                "logs": ["Validating workflow...", "Container started.", "Completed."],
                "error": None,
                "createdAt": 1700000000.0,
                "updatedAt": 1700000010.0,
            }
        }
    }


class ExecutionListResponse(BaseModel):
    executions: List[ExecutionResponse]
    total: int
