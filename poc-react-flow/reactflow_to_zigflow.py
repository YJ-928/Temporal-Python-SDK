"""
ReactFlow → Zigflow Temporal DSL Converter (Python)

Supported node types:
    input      - Workflow entry point / data source
    agent      - Agent step identified by name/id
    condition  - Explicit branching (branch1 / branch2)
    tool       - Activity / API call
    output     - Workflow exit point / data sink

Edge conventions:
    condition → *   : edge must carry data.branch = "branch1" | "branch2"
    agent → agent   : edge may carry data.condition = "<expr>" for routing
    input/tool → *  : plain edges, no extra data required
    * → output      : terminal sink, no outgoing edges expected
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

# ─── Input types (ReactFlow) ──────────────────────────────────────────────────

NodeType = Literal["agent", "condition", "tool", "input", "output"]


@dataclass
class RFNodeData:
    # agent
    agent_name: Optional[str] = None
    agent_id: Optional[str] = None
    # condition
    condition_expr: Optional[str] = None
    # tool
    tool_name: Optional[str] = None
    api_endpoint: Optional[str] = None
    method: Optional[str] = None          # GET | POST | PUT | DELETE
    # input
    source_type: Optional[str] = None
    input_schema: Optional[str] = None
    # output
    sink_type: Optional[str] = None
    output_schema: Optional[str] = None
    # shared
    label: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RFNodeData":
        """Accept both camelCase and snake_case keys from ReactFlow JSON."""
        def get(*keys: str) -> Any:
            for k in keys:
                if k in d:
                    return d[k]
            return None

        return cls(
            agent_name=get("agentName", "agent_name"),
            agent_id=get("agentId", "agent_id"),
            condition_expr=get("conditionExpr", "condition_expr"),
            tool_name=get("toolName", "tool_name"),
            api_endpoint=get("apiEndpoint", "api_endpoint"),
            method=get("method"),
            source_type=get("sourceType", "source_type"),
            input_schema=get("inputSchema", "input_schema"),
            sink_type=get("sinkType", "sink_type"),
            output_schema=get("outputSchema", "output_schema"),
            label=get("label"),
        )


@dataclass
class RFEdgeData:
    branch: Optional[Literal["branch1", "branch2"]] = None
    condition: Optional[str] = None
    label: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RFEdgeData":
        return cls(
            branch=d.get("branch"),
            condition=d.get("condition"),
            label=d.get("label"),
        )


@dataclass
class RFNode:
    id: str
    type: NodeType
    data: RFNodeData

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RFNode":
        return cls(
            id=d["id"],
            type=d["type"],
            data=RFNodeData.from_dict(d.get("data", {})),
        )


@dataclass
class RFEdge:
    id: str
    source: str
    target: str
    data: RFEdgeData = field(default_factory=RFEdgeData)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RFEdge":
        return cls(
            id=d["id"],
            source=d["source"],
            target=d["target"],
            data=RFEdgeData.from_dict(d.get("data") or {}),
        )


# ─── Output types (Zigflow DSL) ───────────────────────────────────────────────

@dataclass
class ZigflowTransition:
    target_id: str
    condition: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {"target_id": self.target_id}
        if self.condition:
            d["condition"] = self.condition
        return d


@dataclass
class ZigflowInputStep:
    kind: str = "workflow_input"
    id: str = ""
    source_type: str = "manual"
    input_schema: Optional[str] = None
    next: list[ZigflowTransition] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {"kind": self.kind, "id": self.id, "source_type": self.source_type}
        if self.input_schema:
            d["input_schema"] = self.input_schema
        d["next"] = [t.to_dict() for t in self.next]
        return d


@dataclass
class ZigflowAgentStep:
    kind: str = "execute_agent"
    id: str = ""
    agent_name: str = ""
    agent_id: Optional[str] = None
    next: list[ZigflowTransition] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {"kind": self.kind, "id": self.id, "agent_name": self.agent_name}
        if self.agent_id:
            d["agent_id"] = self.agent_id
        d["next"] = [t.to_dict() for t in self.next]
        return d


@dataclass
class ZigflowConditionStep:
    kind: str = "condition"
    id: str = ""
    expression: str = ""
    branch1: Optional[ZigflowTransition] = None
    branch2: Optional[ZigflowTransition] = None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "id": self.id,
            "expression": self.expression,
            "branch1": self.branch1.to_dict() if self.branch1 else {},
            "branch2": self.branch2.to_dict() if self.branch2 else {},
        }


@dataclass
class ZigflowActivityStep:
    kind: str = "execute_activity"
    id: str = ""
    tool_name: str = ""
    api_endpoint: Optional[str] = None
    method: Optional[str] = None
    next: list[ZigflowTransition] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {"kind": self.kind, "id": self.id, "tool_name": self.tool_name}
        if self.api_endpoint:
            d["api_endpoint"] = self.api_endpoint
        if self.method:
            d["method"] = self.method
        d["next"] = [t.to_dict() for t in self.next]
        return d


@dataclass
class ZigflowOutputStep:
    kind: str = "workflow_output"
    id: str = ""
    sink_type: str = "default"
    output_schema: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"kind": self.kind, "id": self.id, "sink_type": self.sink_type}
        if self.output_schema:
            d["output_schema"] = self.output_schema
        return d


ZigflowStep = (
    ZigflowInputStep
    | ZigflowAgentStep
    | ZigflowConditionStep
    | ZigflowActivityStep
    | ZigflowOutputStep
)


@dataclass
class ZigflowWorkflow:
    name: str
    version: str
    entry_points: list[str]
    steps: list[ZigflowStep]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "entry_points": self.entry_points,
            "steps": [s.to_dict() for s in self.steps],
        }


# ─── Converter ────────────────────────────────────────────────────────────────

class ReactFlowToZigflow:
    def __init__(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> None:
        self.rf_nodes = [RFNode.from_dict(n) for n in nodes]
        self.rf_edges = [RFEdge.from_dict(e) for e in edges]

        self._node_map: dict[str, RFNode] = {n.id: n for n in self.rf_nodes}
        self._out_edges: dict[str, list[RFEdge]] = {}
        for edge in self.rf_edges:
            self._out_edges.setdefault(edge.source, []).append(edge)

    # ── Public ────────────────────────────────────────────────────────────────

    def convert(self, workflow_name: str = "generated_workflow") -> ZigflowWorkflow:
        self._validate()

        steps: list[ZigflowStep] = []
        visited: set[str] = set()
        queue: deque[str] = deque(self._find_entry_points())

        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)

            node = self._node_map[node_id]
            steps.append(self._convert_node(node))

            for edge in self._out_edges.get(node_id, []):
                if edge.target not in visited:
                    queue.append(edge.target)

        return ZigflowWorkflow(
            name=workflow_name,
            version="1.0.0",
            entry_points=self._find_entry_points(),
            steps=steps,
        )

    # ── Node converters ───────────────────────────────────────────────────────

    def _convert_node(self, node: RFNode) -> ZigflowStep:
        dispatch = {
            "input":     self._convert_input,
            "agent":     self._convert_agent,
            "condition": self._convert_condition,
            "tool":      self._convert_tool,
            "output":    self._convert_output,
        }
        handler = dispatch.get(node.type)
        if not handler:
            raise ValueError(f"Unknown node type '{node.type}' on node '{node.id}'")
        return handler(node)

    def _convert_input(self, node: RFNode) -> ZigflowInputStep:
        edges = self._out_edges.get(node.id, [])
        return ZigflowInputStep(
            id=node.id,
            source_type=node.data.source_type or "manual",
            input_schema=node.data.input_schema,
            next=[ZigflowTransition(target_id=e.target) for e in edges],
        )

    def _convert_agent(self, node: RFNode) -> ZigflowAgentStep:
        edges = self._out_edges.get(node.id, [])
        return ZigflowAgentStep(
            id=node.id,
            agent_name=node.data.agent_name or node.data.label or node.id,
            agent_id=node.data.agent_id,
            next=[
                ZigflowTransition(
                    target_id=e.target,
                    condition=e.data.condition,
                )
                for e in edges
            ],
        )

    def _convert_condition(self, node: RFNode) -> ZigflowConditionStep:
        edges = self._out_edges.get(node.id, [])
        b1 = next((e for e in edges if e.data.branch == "branch1"), None)
        b2 = next((e for e in edges if e.data.branch == "branch2"), None)

        # Already guaranteed by _validate(), but be safe
        if not b1 or not b2:
            raise ValueError(f"Condition node '{node.id}' missing branch edges")

        return ZigflowConditionStep(
            id=node.id,
            expression=node.data.condition_expr or "/* TODO: set conditionExpr */",
            branch1=ZigflowTransition(target_id=b1.target),
            branch2=ZigflowTransition(target_id=b2.target),
        )

    def _convert_tool(self, node: RFNode) -> ZigflowActivityStep:
        edges = self._out_edges.get(node.id, [])
        return ZigflowActivityStep(
            id=node.id,
            tool_name=node.data.tool_name or node.data.label or node.id,
            api_endpoint=node.data.api_endpoint,
            method=node.data.method,
            next=[ZigflowTransition(target_id=e.target) for e in edges],
        )

    def _convert_output(self, node: RFNode) -> ZigflowOutputStep:
        return ZigflowOutputStep(
            id=node.id,
            sink_type=node.data.sink_type or "default",
            output_schema=node.data.output_schema,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_entry_points(self) -> list[str]:
        """Input nodes, or any node with no incoming edges."""
        has_incoming = {e.target for e in self.rf_edges}
        return [
            n.id
            for n in self.rf_nodes
            if n.type == "input" or n.id not in has_incoming
        ]

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate(self) -> None:
        errors: list[str] = []
        all_ids = {n.id for n in self.rf_nodes}

        for edge in self.rf_edges:
            if edge.source not in all_ids:
                errors.append(f"Edge '{edge.id}': source node '{edge.source}' does not exist")
            if edge.target not in all_ids:
                errors.append(f"Edge '{edge.id}': target node '{edge.target}' does not exist")

        for node in self.rf_nodes:
            out = self._out_edges.get(node.id, [])

            if node.type == "condition":
                branches = [e.data.branch for e in out]
                if "branch1" not in branches:
                    errors.append(
                        f"Condition node '{node.id}': missing outgoing edge with branch='branch1'"
                    )
                if "branch2" not in branches:
                    errors.append(
                        f"Condition node '{node.id}': missing outgoing edge with branch='branch2'"
                    )
                if len(out) > 2:
                    errors.append(
                        f"Condition node '{node.id}': has {len(out)} outgoing edges, expected exactly 2"
                    )

            if node.type == "output" and out:
                errors.append(
                    f"Output node '{node.id}': should have no outgoing edges (has {len(out)})"
                )

            if node.type == "input" and not out:
                errors.append(
                    f"Input node '{node.id}': has no outgoing edges — workflow would be empty"
                )

        if errors:
            bullet_list = "\n".join(f"  • {e}" for e in errors)
            raise ValueError(f"ReactFlow graph validation failed:\n{bullet_list}")


# ─── DSL Serializer ───────────────────────────────────────────────────────────

def serialize_to_zigflow_dsl(wf: ZigflowWorkflow) -> str:
    """Render a ZigflowWorkflow as a YAML-like DSL string."""
    lines: list[str] = [
        f"workflow: {wf.name}",
        f"version: {wf.version}",
        f"entry_points: [{', '.join(wf.entry_points)}]",
        "",
        "steps:",
    ]

    for step in wf.steps:
        lines.append(f"  - id: {step.id}")
        lines.append(f"    kind: {step.kind}")

        if isinstance(step, ZigflowInputStep):
            lines.append(f"    source_type: {step.source_type}")
            if step.input_schema:
                lines.append(f"    input_schema: {step.input_schema}")
            _append_transitions(lines, step.next)

        elif isinstance(step, ZigflowAgentStep):
            lines.append(f"    agent_name: {step.agent_name}")
            if step.agent_id:
                lines.append(f"    agent_id: {step.agent_id}")
            _append_transitions(lines, step.next)

        elif isinstance(step, ZigflowConditionStep):
            lines.append(f'    expression: "{step.expression}"')
            lines.append(f"    branch1: {step.branch1.target_id if step.branch1 else 'null'}")
            lines.append(f"    branch2: {step.branch2.target_id if step.branch2 else 'null'}")

        elif isinstance(step, ZigflowActivityStep):
            lines.append(f"    tool_name: {step.tool_name}")
            if step.api_endpoint:
                lines.append(f"    api_endpoint: {step.api_endpoint}")
            if step.method:
                lines.append(f"    method: {step.method}")
            _append_transitions(lines, step.next)

        elif isinstance(step, ZigflowOutputStep):
            lines.append(f"    sink_type: {step.sink_type}")
            if step.output_schema:
                lines.append(f"    output_schema: {step.output_schema}")

        lines.append("")  # blank line between steps

    return "\n".join(lines)


def _append_transitions(lines: list[str], transitions: list[ZigflowTransition]) -> None:
    if not transitions:
        return
    if len(transitions) == 1 and not transitions[0].condition:
        lines.append(f"    next: {transitions[0].target_id}")
        return
    lines.append("    next:")
    for t in transitions:
        lines.append(f"      - target: {t.target_id}")
        if t.condition:
            lines.append(f'        condition: "{t.condition}"')


# ─── Convenience wrapper ──────────────────────────────────────────────────────

def convert_reactflow_to_zigflow(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    workflow_name: str = "generated_workflow",
) -> tuple[ZigflowWorkflow, str]:
    """
    Convert ReactFlow nodes + edges dicts to a ZigflowWorkflow and DSL string.

    Args:
        nodes:         List of ReactFlow node dicts (from JSON / React state)
        edges:         List of ReactFlow edge dicts
        workflow_name: Name embedded in the DSL header

    Returns:
        (workflow, dsl_string)
    """
    converter = ReactFlowToZigflow(nodes, edges)
    workflow = converter.convert(workflow_name)
    dsl = serialize_to_zigflow_dsl(workflow)
    return workflow, dsl


# ─── Example / smoke test ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    nodes = [
        {
            "id": "n-input",
            "type": "input",
            "data": {
                "sourceType": "http",
                "inputSchema": "UserRequestSchema",
                "label": "User Request",
            },
        },
        {
            "id": "n-triage",
            "type": "agent",
            "data": {
                "agentName": "TriageAgent",
                "agentId": "agent-001",
                "label": "Triage",
            },
        },
        {
            "id": "n-cond",
            "type": "condition",
            "data": {
                "conditionExpr": "result.intent === 'billing'",
                "label": "Billing?",
            },
        },
        {
            "id": "n-billing",
            "type": "agent",
            "data": {
                "agentName": "BillingAgent",
                "agentId": "agent-002",
            },
        },
        {
            "id": "n-support",
            "type": "agent",
            "data": {
                "agentName": "SupportAgent",
                "agentId": "agent-003",
            },
        },
        {
            "id": "n-lookup",
            "type": "tool",
            "data": {
                "toolName": "AccountLookup",
                "apiEndpoint": "/api/accounts/{id}",
                "method": "GET",
            },
        },
        {
            "id": "n-output",
            "type": "output",
            "data": {
                "sinkType": "webhook",
                "label": "Send Response",
            },
        },
    ]

    edges = [
        {"id": "e1", "source": "n-input",   "target": "n-triage"},
        {"id": "e2", "source": "n-triage",  "target": "n-cond"},
        {"id": "e3", "source": "n-cond",    "target": "n-billing", "data": {"branch": "branch1"}},
        {"id": "e4", "source": "n-cond",    "target": "n-support", "data": {"branch": "branch2"}},
        {"id": "e5", "source": "n-billing", "target": "n-lookup"},
        {"id": "e6", "source": "n-support", "target": "n-output"},
        {"id": "e7", "source": "n-lookup",  "target": "n-output"},
    ]

    workflow, dsl = convert_reactflow_to_zigflow(nodes, edges, "customer_support_workflow")

    print("=== Zigflow DSL ===\n")
    print(dsl)
    print("\n=== JSON Workflow Object ===\n")
    print(json.dumps(workflow.to_dict(), indent=2))
