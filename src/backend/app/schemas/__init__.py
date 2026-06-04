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
    # API schemas
    "CompileWorkflowRequest",
    "CompileWorkflowResponse",
    "GetWorkflowResponse",
    "ErrorResponse",
]


__all__ = [
    "InputField",
    "OutputField",
    "IfCondition",
    "AgentConfig",
    "WaitConfig",
    "NodeData",
    "Node",
    "EdgeControl",
    "Edge",
    "WorkflowDefinition",
    "CompileRequest",
    "CompileResponse",
]
