"""
Pydantic schemas for workflow JSON validation.
"""
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, model_validator


class InputField(BaseModel):
    """Individual input field mapping."""
    id: Optional[str] = None
    field: str = Field(..., min_length=1)
    store_as: str = Field(..., min_length=1)
    type: Literal["string", "number", "boolean", "integer", "object", "array"]


class OutputField(BaseModel):
    """Individual output field definition."""
    id: Optional[str] = None
    field: str = Field(..., min_length=1)
    type: Literal["string", "number", "boolean", "integer", "object", "array"]


class IfCondition(BaseModel):
    """Conditional expression for IF nodes."""
    left: str = Field(..., min_length=1)
    operator: Literal["==", "!=", ">", "<", ">=", "<="]
    right: Any


class NodeData(BaseModel):
    """Base node-specific configuration data."""
    model_config = {"extra": "allow"}


class StartNodeData(NodeData):
    """Configuration data for START node."""


class EndNodeData(NodeData):
    """Configuration data for END node."""


class InputNodeData(NodeData):
    """Configuration data for INPUT node."""
    inputs: List[InputField] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_fields(self) -> "InputNodeData":
        fields = [f.field for f in self.inputs]
        store_as_names = [f.store_as for f in self.inputs]
        if len(fields) != len(set(fields)):
            raise ValueError("Duplicate input field names are not allowed")
        if len(store_as_names) != len(set(store_as_names)):
            raise ValueError("Duplicate 'store_as' variable names are not allowed")
        return self


class OutputNodeData(NodeData):
    """Configuration data for OUTPUT node."""
    outputs: List[OutputField] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_unique_fields(self) -> "OutputNodeData":
        fields = [f.field for f in self.outputs]
        if len(fields) != len(set(fields)):
            raise ValueError("Duplicate output field names are not allowed")
        return self


class ActionNodeData(NodeData):
    """Configuration data for ACTION node."""
    operation: str = Field(..., min_length=1)
    inputs: Dict[str, str]
    output: str = Field(..., min_length=1)


class AgentNodeData(NodeData):
    """Configuration data for AGENT node."""
    agent: str = Field(..., min_length=1)
    inputs: Optional[Dict[str, str]] = None
    output: Optional[str] = Field(None, min_length=1)
    output_path: Optional[str] = Field(None, min_length=1)

    @model_validator(mode="after")
    def validate_agent(self) -> "AgentNodeData":
        from app.agents.registry import AgentRegistry
        if not AgentRegistry.has_agent(self.agent):
            raise ValueError(f"Agent '{self.agent}' is not registered in the system")
        return self


class IfNodeData(NodeData):
    """Configuration data for IF node."""
    left: str = Field(..., min_length=1)
    operator: Literal["==", "!=", ">", "<", ">=", "<="]
    right: Any


class StartNode(BaseModel):
    id: str
    type: Literal["START"]
    data: StartNodeData = Field(default_factory=StartNodeData)


class EndNode(BaseModel):
    id: str
    type: Literal["END"]
    data: EndNodeData = Field(default_factory=EndNodeData)


class InputNode(BaseModel):
    id: str
    type: Literal["INPUT"]
    data: InputNodeData


class OutputNode(BaseModel):
    id: str
    type: Literal["OUTPUT"]
    data: OutputNodeData


class ActionNode(BaseModel):
    id: str
    type: Literal["ACTION"]
    data: ActionNodeData


class AgentNode(BaseModel):
    id: str
    type: Literal["AGENT"]
    data: AgentNodeData


class IfNode(BaseModel):
    id: str
    type: Literal["IF"]
    data: IfNodeData


Node = Annotated[
    Union[StartNode, EndNode, InputNode, OutputNode, ActionNode, AgentNode, IfNode],
    Field(discriminator="type")
]


class EdgeControl(BaseModel):
    """Edge control metadata for IF branches."""
    branch: Literal["true", "false"]


class Edge(BaseModel):
    """Workflow edge definition."""
    id: str
    source: str
    target: str
    branch: Optional[Literal["true", "false"]] = None
    control: Optional[EdgeControl] = None


class WorkflowDefinition(BaseModel):
    """Complete workflow JSON structure."""
    nodes: List[Node]
    edges: List[Edge]


class CompileRequest(BaseModel):
    """Request body for workflow compilation endpoint."""
    workflow: WorkflowDefinition
    dsl_version: Optional[str] = None
    version: Optional[str] = None
    workflow_type: Optional[str] = None
    task_queue: Optional[str] = None


class CompileResponse(BaseModel):
    """Response body for workflow compilation endpoint."""
    success: bool
    dsl: Optional[Dict] = None
    error: Optional[str] = None
