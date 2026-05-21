"""Pydantic v2 request schemas."""
from typing import Any, Dict

from pydantic import BaseModel, Field


class ExecuteWorkflowRequest(BaseModel):
    """Request body for POST /api/v1/execute."""

    workflow: str = Field(
        ...,
        description="Workflow filename relative to the workflows directory (e.g. hello-world.json)",
        examples=["hello-world.json"],
    )
    workflowPath: str = Field(
        ...,
        description="Absolute path to the workflow file inside the container",
        examples=["/app/workflows/json/hello-world.json"],
    )
    input: Dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow input data forwarded to the Zigflow workflow",
        examples=[{"name": "Yash"}],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "workflow": "hello-world.json",
                "workflowPath": "/app/workflows/json/hello-world.json",
                "input": {"name": "Yash"},
            }
        }
    }
