"""
Compiler request and response schemas.

Pydantic models for workflow compilation endpoints.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .workflow_sch import Node, Edge


class CompileWorkflowRequest(BaseModel):
    """Request schema for POST /api/v1/workflows/compile"""

    nodes: List[Node] = Field(..., description="List of workflow nodes")
    edges: List[Edge] = Field(..., description="List of workflow edges")
    workflow_id: Optional[str] = Field(None, description="Optional custom workflow ID")
    workflow_type: Optional[str] = Field(None, description="Temporal workflow type")
    task_queue: Optional[str] = Field(None, description="Temporal task queue")

    class Config:
        json_schema_extra = {
            "example": {
                "nodes": [
                    {"id": "N1", "type": "START"},
                    {"id": "N2", "type": "INPUT", "data": {"inputs": [{"id": "1", "field": "name", "store_as": "user_name", "type": "string"}]}},
                    {"id": "N3", "type": "ACTION", "data": {"operation": "greet", "inputs": {"name": "user_name"}, "output": "message"}},
                    {"id": "N4", "type": "OUTPUT", "data": {"outputs": [{"id": "1", "field": "message", "type": "string"}]}},
                    {"id": "N5", "type": "END"},
                ],
                "edges": [
                    {"id": "E1", "source": "N1", "target": "N2"},
                    {"id": "E2", "source": "N2", "target": "N3"},
                    {"id": "E3", "source": "N3", "target": "N4"},
                    {"id": "E4", "source": "N4", "target": "N5"},
                ],
                "workflow_id": "greeting-flow",
                "workflow_type": "greeting-workflow",
                "task_queue": "workflow-builder",
            }
        }


class CompileWorkflowResponse(BaseModel):
    """Response schema for POST /api/v1/workflows/compile"""

    success: bool = Field(..., description="Compilation success status")
    workflow_id: str = Field(..., description="Generated or provided workflow ID")
    dsl: Dict[str, Any] = Field(..., description="Compiled Zigflow DSL")
    file_path: str = Field(..., description="Path to saved DSL file")
    content_hash: str = Field(..., description="SHA-256 content hash of the compiled DSL")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "workflow_id": "greeting-flow",
                "dsl": {
                    "document": {
                        "dsl": "1.0.0",
                        "taskQueue": "workflow-builder",
                        "workflowType": "greeting-workflow",
                        "name": "greeting-flow"
                    }
                },
                "file_path": "runtime/compiled/2026/06/02/greeting-flow-a8d23e91c1bfe345.json",
                "content_hash": "a8d23e91c1bfe345"
            }
        }


class GetWorkflowResponse(BaseModel):
    """Response schema for GET /api/v1/workflows/{workflow_id}"""

    success: bool = Field(..., description="Retrieval success status")
    workflow_id: str = Field(..., description="Workflow identifier")
    dsl: Dict[str, Any] = Field(..., description="Compiled Zigflow DSL")
    file_path: str = Field(..., description="Path to DSL file")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "workflow_id": "greeting-flow",
                "dsl": {
                    "document": {
                        "dsl": "1.0.0",
                        "taskQueue": "workflow-builder",
                        "workflowType": "greeting-workflow",
                        "version": "1.0.0",
                    },
                    "do": [],
                },
                "file_path": "runtime/compiled/2026/06/02/greeting-flow_20260602_143052.json",
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response schema"""

    success: bool = Field(False, description="Always false for errors")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "Workflow not found",
                "detail": "Workflow 'greeting-flow' not found in storage",
            }
        }
