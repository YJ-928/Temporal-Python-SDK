# 01 — Existing POC Analysis: `poc-react-flow`

## Overview

`poc-react-flow/` is a working prototype that converts a ReactFlow-like graph JSON into a Zigflow DSL YAML/JSON. It was built for a specific agent-routing use case: intent parsing → conditional branching → downstream agent execution.

The POC is **not generic**. Every piece of it was built for that one workflow shape and that one node type (`agent-node`). This document records what was built, what is reusable, and what must be discarded.

---

## Files in `poc-react-flow/`

| File | Purpose |
|---|---|
| `react-flow/output.json` | Sample ReactFlow graph JSON (nodes + edges) |
| `node_conversion.py` | Builder functions for individual Zigflow DSL task blocks |
| `react_flow_to_temporal_json.py` | Core converter: parses the graph, walks nodes, emits `do` list |
| `reactflow_to_zigflow.py` | Second-pass converter with typed dataclasses (more structured) |
| `bfs.py` | Standalone BFS utility (adjacency-list graph traversal) |
| `template_rendere.py` | Jinja2 template renderer for YAML fragments |
| `templates/condition.yaml` | Jinja2 template for the `switch` task block |
| `workflow/agent-router-workflow.json` | Hand-crafted reference output (JSON DSL) |
| `workflow/agent-router-workflow.yaml` | Hand-crafted reference output (YAML DSL, annotated) |
| `workflow/agent-router-workflow2.yaml` | Machine-generated output (via `convert_json_yaml.py`) |
| `workflow/external-activity-workflow.yaml` | Minimal example with `call: activity` |
| `workflow/convert_json_yaml.py` | JSON → YAML serialization utility |
| `run_worker.py` | Temporal Worker wiring (executes agent activities) |
| `activities/activity.py` | Activity implementations (agent registry lookup) |
| `agents/pydantic.py` | LLM agent calls (irrelevant to compiler) |
| `main.py` | Entry point that calls agent code directly |

---

## Input Graph Format (as used in `react-flow/output.json`)

```json
{
  "nodes": [
    {
      "id": "input-node-1",
      "type": "text-input",
      "position": { "x": 100, "y": 100 },
      "data": { "key": "userQuery", "type": "string" }
    },
    {
      "id": "agent-node-1",
      "type": "agent-node",
      "position": { "x": 100, "y": 200 },
      "data": {
        "name": "intent",
        "input": [{ "key": "userQuery", "type": "string" }],
        "output": { "key": "type", "type": "string" }
      }
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "input-node-1",
      "target": "agent-node-1"
    },
    {
      "id": "edge-2",
      "source": "agent-node-1",
      "target": "agent-node-2",
      "data": { "condition": "type == \"HOTEL\"" }
    }
  ]
}
```

### Observations

- Nodes carry a `type` string that is UI-layer specific (`text-input`, `agent-node`). There is no semantic node taxonomy.
- `data` is flat and untyped — every node type has a different shape with no shared base.
- Edges may carry execution logic in `data.condition`. This means edges are **not dumb** — they carry conditional routing logic. This is a design problem.
- `position` is only used for sorting nodes by Y-axis during pre-processing. It leaks UI concerns into the compiler.

---

## `node_conversion.py` — Analysis

This file is a collection of **imperative builder functions**. Each function returns a dict fragment that represents one Zigflow task block.

```python
get_input_node(input_vars)      # → set block (captureInput)
get_agent_node(input_var, name) # → call:activity block
save_output(task_name, key)     # → set block (saves $output)
save_from_output(...)           # → set block (saves $output.key)
run_agent_as_subflow(...)       # → do block wrapping a call
get_branch_node(reason, ...)    # → switch block
get_default_node(task_name)     # → do block with fallback set
get_dsl_metadata()              # → document header dict
```

### What it does well
- Each builder is small and composable.
- The `get_branch_node` function correctly emits a `switch` block from a condition dict.
- `get_dsl_metadata()` establishes the correct `document` header format.

### Problems
- All functions are hardcoded to the **agent** domain. There is no general abstraction.
- No validation — wrong arguments produce silently broken YAML.
- Node type is not inspected — the caller is responsible for knowing which function to call.
- No concept of graph traversal — node ordering is handled externally by the caller.
- There is no registry. Adding a new node type means adding a new freestanding function.

---

## `react_flow_to_temporal_json.py` — Analysis

This is the primary converter used to produce the output JSON. It operates in a single `convert(flow: dict) -> dict` function.

### Algorithm
1. Separate nodes by `type` (`text-input`, `agent-node`).
2. Identify router nodes (those with outgoing conditional edges).
3. Identify switch-target nodes (destinations of conditional edges).
4. Sort pre-switch nodes by `position.y` to determine execution order.
5. Emit `captureInput` from input nodes.
6. Emit `call` + `set` blocks for pre-switch agent nodes.
7. If a node is a router, emit a `switch` block inline.
8. Emit `do` blocks for each switch-target node.
9. Always append a `setDefaultMessage` fallback.

### Problems
- The entire function is procedural with no extensibility. Adding a new node type requires rewriting the main loop.
- Uses `position.y` for ordering — leaks UI coordinates into graph semantics.
- Conditional logic on edges is read inside the converter — edges are not dumb.
- No concept of a START or END node — entry and exit are inferred from graph shape.
- No cycle detection, no reachability check, no tree validation.
- The output is domain-specific: always produces `captureInput`, `parseIntent`, `routeByIntent` structure.

---

## `reactflow_to_zigflow.py` — Analysis

This is a second, more structured attempt at the same converter. It introduces typed dataclasses for both input (ReactFlow) and output (Zigflow).

### Input types
```
RFNode       id, type (NodeType literal), data (RFNodeData)
RFEdge       id, source, target, data (RFEdgeData)
RFNodeData   agent_name, condition_expr, tool_name, api_endpoint, method, ...
RFEdgeData   branch (branch1|branch2), condition, label
```

### Output types
```
ZigflowInputStep       kind="workflow_input"
ZigflowAgentStep       kind="execute_agent"
ZigflowConditionStep   kind="condition"
ZigflowActivityStep    kind="execute_activity"
ZigflowOutputStep      kind="workflow_output"
ZigflowWorkflow        name, version, entry_points, steps[]
```

### Conversion logic
- Uses BFS from entry points (nodes with no incoming edges).
- Has a dispatch table: `{ "input": handler, "agent": handler, ... }`.
- Each handler converts a single `RFNode` to the corresponding `ZigflowStep`.
- Condition nodes look up branch edges by `edge.data.branch` field.

### Problems
- The `ZigflowStep` output format is custom — it does not map directly to Zigflow DSL tasks. It is an intermediate IR that was never connected to a DSL serializer.
- Agent steps are first-class output types, which is irrelevant to the new compiler.
- Edge data (`condition`, `branch`) still carries execution logic — edges are not dumb.
- `ZigflowWorkflow` uses `entry_points: list[str]` which assumes there can be multiple entry points. The new compiler allows exactly one START.
- The BFS traversal is correct in principle but is tangled with node conversion.
- No validation of the tree constraint — cycles and multi-parent nodes are not rejected.

---

## `bfs.py` — Analysis

A standalone, clean BFS implementation over an adjacency list (integers). It is a reference implementation, not wired into any converter. The traversal logic in `reactflow_to_zigflow.py` re-implements BFS inline using `deque`.

**Reusable concept:** The BFS walk pattern from `reactflow_to_zigflow.py` is directly applicable to the compiler's graph traversal stage, but should operate on `str` node IDs and use an adjacency map.

---

## `template_rendere.py` and `templates/condition.yaml`

A Jinja2-based fragment renderer for the `switch` task. The template accepts an `agent` name and a list of routes. The output is a single Zigflow `switch` block.

**Reusable concept:** Template-driven generation is a valid pattern for the DSL generator phase. Jinja2 for YAML fragments is clean and avoids string concatenation bugs. However, the template is currently domain-specific (hardcoded to routing by agent intent).

---

## What Is Reusable

| Concept | Source | Reuse decision |
|---|---|---|
| `document` header structure | `node_conversion.get_dsl_metadata()` | Keep — same Zigflow DSL format |
| BFS graph walk | `reactflow_to_zigflow.ReactFlowToZigflow.convert()` | Keep — adapt to tree traversal |
| Dispatch table pattern | `reactflow_to_zigflow._convert_node()` | Keep — extend to 8 node types |
| `set` task builder | `node_conversion.get_input_node()` / `save_output()` | Keep — generalise |
| `switch` task builder | `node_conversion.get_branch_node()` | Keep — generalise |
| Jinja2 template rendering | `template_rendere.py` | Optional — useful for complex task bodies |
| JSON → YAML serialization | `workflow/convert_json_yaml.py` | Keep — trivial, reuse pattern |

---

## What Should Be Discarded

| Concept | Why |
|---|---|
| `agent-node` type | Domain-specific; not in the frozen node set |
| `text-input` node type | Replaced by START node |
| Edge `data.condition` / `data.branch` | Edges are dumb in v1; conditions move to node `data` |
| `position.y` sorting | UI concern; compiler uses topological order, not screen coordinates |
| `AgentRunner` registry | Agent execution is out of scope |
| `RFNodeData.agent_name`, `agent_id` | Agent-specific fields |
| `ZigflowAgentStep` | Agent-specific output type |
| `ZigflowInputStep` / `ZigflowOutputStep` as DSL tasks | START/END are graph-only; they emit no DSL tasks |
| Multiple entry points (`entry_points: list`) | V1 enforces exactly one START |
| Inline switch emission in the main loop | Logic belongs in the IF node handler, not the traversal |
| `setDefaultMessage` always appended | Hardcoded fallback — belongs in IF node config |
