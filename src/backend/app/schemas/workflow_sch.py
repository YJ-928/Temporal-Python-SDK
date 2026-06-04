"""
Pydantic schemas for workflow JSON validation.
"""
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class InputField(BaseModel):
    """Individual input field mapping."""
    id: Optional[str] = None
    field: str
    store_as: str
    type: str


class OutputField(BaseModel):
    """Individual output field definition."""
    id: Optional[str] = None
    field: str
    type: str


class IfCondition(BaseModel):
    """Conditional expression for IF nodes."""
    left: str
    operator: str
    right: Any


class NodeData(BaseModel):
    """Base node-specific configuration data."""
    model_config = {"extra": "allow"}


class StartNodeData(NodeData):
    """Configuration data for START node."""
    pass


class EndNodeData(NodeData):
    """Configuration data for END node."""
    pass


class InputNodeData(NodeData):
    """Configuration data for INPUT node."""
    inputs: List[InputField] = Field(..., min_length=1)


class OutputNodeData(NodeData):
    """Configuration data for OUTPUT node."""
    outputs: List[OutputField] = Field(..., min_length=1)


class ActionNodeData(NodeData):
    """Configuration data for ACTION node."""
    operation: str
    inputs: Dict[str, str]
    output: str


class AgentNodeData(NodeData):
    """Configuration data for AGENT node."""
    agent: str


class IfNodeData(NodeData):
    """Configuration data for IF node."""
    left: str
    operator: str
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
