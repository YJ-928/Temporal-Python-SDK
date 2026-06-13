"""
Schema package.

Pydantic models for request/response validation.
"""
from .workflow_sch import (
    InputField,
    OutputField,
    IfCondition,
    NodeData,
    Node,
    EdgeControl,
    Edge,
    WorkflowDefinition,
    CompileRequest,
    CompileResponse,
)
from .compiler_sch import (
    CompileWorkflowRequest,
    CompileWorkflowResponse,
    GetWorkflowResponse,
    ErrorResponse,
)
from .execution_sch import (
    ExecuteWorkflowRequest,
    ExecuteWorkflowResponse,
    ExecutionListItem,
    ExecutionListResponse,
    TraceStepResponse,
    ExecutionTraceResponse,
)

__all__ = [
    # Workflow schemas
    "InputField",
    "OutputField",
    "IfCondition",
    "NodeData",
    "Node",
    "EdgeControl",
    "Edge",
    "WorkflowDefinition",
    "CompileRequest",
    "CompileResponse",
    # Compiler API schemas
    "CompileWorkflowRequest",
    "CompileWorkflowResponse",
    "GetWorkflowResponse",
    "ErrorResponse",
    # Execution API schemas
    "ExecuteWorkflowRequest",
    "ExecuteWorkflowResponse",
    "ExecutionListItem",
    "ExecutionListResponse",
    "TraceStepResponse",
    "ExecutionTraceResponse",
]
