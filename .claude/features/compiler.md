# DSL Compiler — Implementation Reference

> **Source of truth:** `src/backend/` — all sections derived from production code only.

---

## 1. Overview

The DSL Compiler transforms a workflow graph (nodes + edges JSON) into executable Zigflow DSL. It bridges the visual workflow builder and the Temporal execution engine.

```
Workflow JSON {nodes, edges}
    ↓
Phase 0: Validation  (Pydantic + graph topology)
    ↓
Phase A: Graph Compilation and Traversal  (graph.py)
    ↓
Phase B: DSL Generation  (dsl_generator.py + builders)
    ↓
Zigflow DSL JSON → validated → saved → registered → Temporal execution
```

The compiler is deterministic and reproducible: the same workflow JSON always produces the same DSL.

---

## 2. System Architecture

```
src/backend/app/
├── compiler/
│   ├── workflow_compiler.py   ← main entry point (compile_workflow_to_dsl)
│   ├── graph.py               ← Phase A: graph analysis and traversal
│   ├── dsl_generator.py       ← Phase B: DSL assembly and builder dispatch
│   └── exceptions.py          ← typed exception hierarchy
├── builders/
│   ├── __init__.py            ← BUILDERS registry dict
│   ├── terminal_builder.py    ← START, END
│   ├── input_builder.py       ← INPUT
│   ├── output_builder.py      ← OUTPUT
│   ├── action_builder.py      ← ACTION
│   ├── agent_builder.py       ← AGENT
│   ├── if_builder.py          ← IF
│   └── condition_builder.py   ← shared condition expression utility
├── schemas/
│   ├── workflow_sch.py        ← Pydantic node/edge/workflow models
│   └── compiler_sch.py        ← API request/response schemas
├── services/
│   ├── compiler_service.py    ← high-level CompilerService wrapper
│   ├── registration_service.py← workflow registration + hot-reload
│   ├── execution_service.py   ← Temporal client execution
│   └── storage_service.py     ← DSL file persistence
└── agents/
    └── registry.py            ← AgentRegistry: agent metadata lookup
```

---

## 3. Project Structure

```
src/backend/
├── app/
│   ├── compiler/       ← compilation pipeline
│   ├── builders/       ← node-specific DSL builders
│   ├── schemas/        ← Pydantic validation models
│   ├── services/       ← service layer (compiler, registration, execution)
│   ├── agents/         ← agent implementations and registry
│   ├── api/v1/         ← FastAPI routes
│   └── config/         ← settings and logger
└── tests/              ← test suites
```

---

## 4. Workflow Schema Layer

Defined in `src/backend/app/schemas/workflow_sch.py` (Pydantic v2).

### WorkflowDefinition

```python
class WorkflowDefinition(BaseModel):
    nodes: List[Node]   # discriminated union by "type" field
    edges: List[Edge]
```

### Node Types (discriminated union)

| Node Model    | `type` field | Required `data` fields                                    |
|---------------|-------------|-----------------------------------------------------------|
| `StartNode`   | `"START"`   | none                                                      |
| `EndNode`     | `"END"`     | none                                                      |
| `InputNode`   | `"INPUT"`   | `inputs: List[InputField]` (min 1, unique field + store_as names) |
| `OutputNode`  | `"OUTPUT"`  | `outputs: List[OutputField]` (min 1, unique field names)  |
| `ActionNode`  | `"ACTION"`  | `operation: str`, `inputs: Dict[str, str]`, `output: str` |
| `AgentNode`   | `"AGENT"`   | `agent: str` (must be in AgentRegistry), `inputs?`, `output?`, `output_path?` |
| `IfNode`      | `"IF"`      | `left: str`, `operator: Literal["==","!=",">","<",">=","<="]`, `right: Any` |

### InputField

```python
class InputField(BaseModel):
    id: Optional[str]
    field: str          # source field name from $input
    store_as: str       # variable name in $context
    type: Literal["string", "number", "boolean", "integer", "object", "array"]
```

### OutputField

```python
class OutputField(BaseModel):
    id: Optional[str]
    field: str          # variable name to read from $context
    type: Literal["string", "number", "boolean", "integer", "object", "array"]
```

### Edge

```python
class Edge(BaseModel):
    id: str
    source: str
    target: str
    branch: Optional[Literal["true", "false"]] = None    # top-level convenience field
    control: Optional[EdgeControl] = None                 # EdgeControl.branch also accepted
```

Both `branch` and `control.branch` are supported. The adjacency builder normalizes them both into `control = {"branch": value}`.

### Minimal Valid Workflow JSON

```json
{
  "nodes": [
    {"id": "N1", "type": "START"},
    {"id": "N2", "type": "INPUT", "data": {"inputs": [{"field": "name", "store_as": "user_name", "type": "string"}]}},
    {"id": "N3", "type": "ACTION", "data": {"operation": "greet", "inputs": {"name": "user_name"}, "output": "message"}},
    {"id": "N4", "type": "OUTPUT", "data": {"outputs": [{"field": "message", "type": "string"}]}},
    {"id": "N5", "type": "END"}
  ],
  "edges": [
    {"id": "E1", "source": "N1", "target": "N2"},
    {"id": "E2", "source": "N2", "target": "N3"},
    {"id": "E3", "source": "N3", "target": "N4"},
    {"id": "E4", "source": "N4", "target": "N5"}
  ]
}
```

---

## 5. Graph Validation Layer

Defined in `src/backend/app/compiler/graph.py` — `validate_graph()`.

Validation runs before graph compilation, after Pydantic schema validation.

### Validation Rules (in order)

| Rule | Exception |
|---|---|
| Exactly one START node | `GraphValidationError` |
| At least one END node | `GraphValidationError` |
| START node has no incoming edges | `GraphValidationError` |
| No self-loops (source == target) | `CycleDetectedError` |
| No duplicate connections (source, target, branch) | `GraphValidationError` |
| No cycles (DFS from START + all disconnected components) | `CycleDetectedError` |
| All nodes reachable from START | `GraphValidationError` |
| END nodes have no outgoing edges | `GraphValidationError` |
| Non-IF, non-END nodes have at most one outgoing edge | `GraphValidationError` |
| All non-END nodes have at least one outgoing edge (no dead ends) | `GraphValidationError` |
| IF nodes have exactly one `"true"` branch and one `"false"` branch | `MissingBranchError` |

### Exception Hierarchy

```python
WorkflowValidationError(ValueError)       # Pydantic schema failures
    └── GraphValidationError              # graph topology failures
            ├── CycleDetectedError        # cycle / self-loop
            └── MissingBranchError        # IF branch missing or duplicate
```

---

## 6. Traversal Generation

Defined in `src/backend/app/compiler/graph.py` — `traverse_graph()`.

### TraversalEntry Structure

Each entry is a plain dict with these keys:

| Field | Type | Meaning |
|---|---|---|
| `node_id` | `str` | Node identifier |
| `node_type` | `str` | `"START"`, `"INPUT"`, `"ACTION"`, `"AGENT"`, `"IF"`, `"OUTPUT"`, `"END"` |
| `node` | `dict` | Full node dict from node_map (read-only reference) |
| `is_terminal` | `bool` | True if any direct successor is an END node |
| `successors` | `list[str]` | Direct successor node IDs |
| `incoming_edge_control` | `dict \| None` | `None` for normal edges; `{"branch": "true"}` or `{"branch": "false"}` for IF branches |
| `branch_map` | `dict \| None` | IF nodes only: `{"true": {"node_id": ..., "task_name": ...}, "false": {...}}` |
| `then_transition` | `str \| None` | Pre-resolved next DSL task name for non-IF nodes (e.g. `"N3_greet"`, `"end"`) |

### Successor Resolution

`then_transition` is pre-computed by `resolve_successor_task()` for all non-IF, non-START, non-END nodes:

- If the successor is an END node → `"end"`
- Otherwise → `resolve_task_name(successor_node)` (the DSL task name the builder will emit)
- This handles convergence automatically: if two branches both point to the same downstream node, both get `then_transition` set to that node's task name

### Branch Routing

For IF nodes, `branch_map` is pre-resolved during traversal:

```python
branch_map = {
    "true": {"node_id": "N3", "task_name": "N3_greet"},
    "false": {"node_id": "N4", "task_name": "N4_expose"},
}
```

If either branch target is an END node, `task_name` is `"end"`.

### Traversal Order

DFS preorder from START. Each node is visited exactly once (visited set prevents re-entry). Shared convergence nodes (multiple incoming edges) appear once in the traversal output.

---

## 7. Builder Architecture

Defined in `src/backend/app/builders/`.

Builders are pure functions: `(node: dict, *, traversal_entry: dict | None) -> dict | None`.

### Builder Registry

`src/backend/app/builders/__init__.py` defines the `BUILDERS` dict:

```python
BUILDERS = {
    "START":  build_terminal,
    "END":    build_terminal,
    "INPUT":  build_input,
    "OUTPUT": build_output,
    "ACTION": build_action,
    "AGENT":  build_agent,
    "IF":     build_if,
}
```

`initialize_builders()` in `workflow_compiler.py` registers each entry into `BUILDER_REGISTRY` via `register_builder()` before compilation.

### Universal Builder Rules

1. Signature: `build_X(node: dict, *, traversal_entry: dict | None = None) -> dict | None`
2. Returns a single-key dict `{task_name: task_body}` or `None` (for START/END)
3. Injects `"then"` from `traversal_entry["then_transition"]` if set; falls back to `"end"` if `is_terminal` is True and no transition
4. No side effects, no global state

### Task Naming Convention

| Node Type | Task Name Pattern | Example |
|---|---|---|
| INPUT | `{node_id}_capture` | `N2_capture` |
| OUTPUT | `{node_id}_expose` | `N4_expose` |
| ACTION | `{node_id}_{operation}` | `N3_greet` |
| AGENT | `{node_id}_agent` | `N5_agent` |
| IF | `{node_id}_if` | `N6_if` |
| START | raises `ValueError` (no DSL task) | — |
| END | raises `ValueError` (no DSL task) | — |

---

## 8. DSL Generation

Defined in `src/backend/app/compiler/dsl_generator.py` — `generate_dsl()`.

### generate_dsl()

```python
def generate_dsl(
    traversal: list[dict],
    dsl_version: str,
    version: str,
    workflow_type: str,
    task_queue: str,
    description: str = "",
) -> dict:
```

**Returns:**

```json
{
  "document": {
    "dsl": "1.0.0",
    "taskQueue": "workflow-builder",
    "workflowType": "greeting-workflow",
    "version": "1.0.0",
    "summary": ""
  },
  "do": [...]
}
```

### Dispatch Loop

```
for entry in traversal:
    builder = BUILDER_REGISTRY.get(node_type)
    fragment = builder(node, traversal_entry=entry)
    if fragment is not None:
        if is_branch_target:        ← incoming_edge_control.branch in ("true", "false")
            wrap in subflow do block
        append to do_list
```

### Branch Wrapping

When a node's `incoming_edge_control` contains a branch label (`"true"` or `"false"`), the DSL generator wraps its fragment in a subflow:

```json
{
  "N3_greet": {
    "do": [
      {
        "N3_greet_inner": { ...task_body... }
      }
    ],
    "then": "end"
  }
}
```

The outer `then` transition is lifted out of the inner task body before wrapping.

### save_dsl()

```python
def save_dsl(dsl: dict, output_path: str) -> None
```

Writes DSL to JSON file with `indent=2`.

---

## 9. Supported Node Types

### START

- Builder: `build_terminal`
- DSL output: `None` (no task emitted)
- Purpose: Graph entry point only

### END

- Builder: `build_terminal`
- DSL output: `None` (no task emitted)
- Purpose: Causes `then_transition = "end"` on predecessors

### INPUT

- Builder: `build_input`
- Task name: `{node_id}_capture`
- DSL task type: `set` + `export.as`

```json
{
  "N2_capture": {
    "set": {
      "user_name": "${ $input.name }"
    },
    "export": {
      "as": "${ $context + {user_name: .user_name} }"
    },
    "then": "N3_greet"
  }
}
```

Reads fields from `$input`. Merges all captured variables into `$context` via `export.as`.

### OUTPUT

- Builder: `build_output`
- Task name: `{node_id}_expose`
- DSL task type: `set`

```json
{
  "N4_expose": {
    "set": {
      "message": "${ $context.message }"
    },
    "then": "end"
  }
}
```

Reads variables from `$context` and exposes them as the final workflow output.

### ACTION

- Builder: `build_action`
- Task name: `{node_id}_{operation}`
- DSL task type: `call: http`
- Endpoint: `http://localhost:8000/api/v1/actions/{operation}`
- Method: `POST`

```json
{
  "N3_greet": {
    "call": "http",
    "with": {
      "method": "post",
      "endpoint": "http://localhost:8000/api/v1/actions/greet",
      "headers": { "Content-Type": "application/json" },
      "body": "${ {name: $context.user_name} }"
    },
    "export": {
      "as": "${ $context + {message: .} }"
    },
    "then": "N4_expose"
  }
}
```

The `body` is a single JQ expression string evaluating to an object (not a dict of per-field JQ strings). Inputs are read from `$context`. Output is exported into `$context` under `output_name`.

### AGENT

- Builder: `build_agent`
- Task name: `{node_id}_agent`
- DSL task type: `call: http`
- Endpoint: looked up from `AgentRegistry` by `agent_id`; falls back to `http://localhost:11000/execute` if not registered
- Method: from registry metadata (default `post`)

```json
{
  "N5_agent": {
    "call": "http",
    "with": {
      "method": "post",
      "endpoint": "http://localhost:11000/execute",
      "headers": { "Content-Type": "application/json" },
      "body": "${ {city: $context.user_city} }"
    },
    "export": {
      "as": "${ $context + {weather_result: .} }"
    },
    "then": "N6_expose"
  }
}
```

`output_path` controls the JQ selector applied to the response before exporting: `.{output_path}` if set, else `.` (whole response).

### IF

- Builder: `build_if`
- Task name: `{node_id}_if`
- DSL task type: `switch`

```json
{
  "N6_if": {
    "switch": [
      {
        "case": {
          "when": "${ $context.user_email != \"\" }",
          "then": "N7_validate_email"
        }
      },
      {
        "default": {
          "then": "N8_expose"
        }
      }
    ]
  }
}
```

Condition is read from `node["data"]` (left, operator, right) and formatted by `build_condition_expression()`. Branch routing comes from `traversal_entry["branch_map"]` (pre-resolved by traversal).

---

## 10. Agent Integration

Defined in `src/backend/app/agents/registry.py`.

### AgentRegistry

Static metadata lookup table: `agent_id → metadata dict`. No lifecycle management.

```python
class AgentRegistry:
    _agents: Dict[str, Dict] = {
        "weather-agent": {
            "url": "http://localhost:11000/execute",
            "method": "POST",
            "port": 11000,
            "description": "Weather lookup service for cities worldwide",
            "request_schema": {"city": "string"},
            "response_schema": {"success": "boolean", "city": "string", "temperature": "integer", "condition": "string"}
        },
        "email-validator-agent": {
            "url": "http://localhost:11001/execute",
            "method": "POST",
            "port": 11001,
            ...
        },
        "email-sender-agent": {
            "url": "http://localhost:11002/execute",
            "method": "POST",
            "port": 11002,
            ...
        },
        "summarizer-agent": {
            "url": "http://localhost:11003/execute",
            "method": "POST",
            "port": 11003,
            ...
        },
    }
```

### Key Methods

| Method | Signature | Purpose |
|---|---|---|
| `get_agent(agent_id)` | `→ Optional[Dict]` | Full metadata dict or None |
| `get_url(agent_id)` | `→ Optional[str]` | Execution URL or None |
| `has_agent(agent_id)` | `→ bool` | Existence check (used by Pydantic validator) |
| `list_agents()` | `→ list[str]` | All registered agent IDs |
| `register_agent(agent_id, metadata)` | `→ None` | Register new agent |

### Agent Compilation

When an AGENT node is compiled, `build_agent()` calls `AgentRegistry.get_agent(agent_id)` to resolve the endpoint and HTTP method. If the agent is not registered, the builder falls back to `http://localhost:11000/execute` with method `post`.

The `AgentNodeData` Pydantic validator calls `AgentRegistry.has_agent()` during schema validation — a workflow referencing an unregistered agent fails validation before reaching the compiler.

---

## 11. Registration and Runtime

Defined in `src/backend/app/services/registration_service.py`.

### RegistrationService

Manages workflow registration state and triggers hot-reloads of the Zigflow daemon.

**Storage:** `runtime/registrations.json` — keyed by `dsl_hash` (SHA-256 of compiled DSL).

**Registration entry:**

```json
{
  "workflow_id": "greeting-flow",
  "workflow_type": "greeting-workflow",
  "validated": true,
  "registered": true,
  "runtime_loaded": false,
  "registered_at": "2026-06-06T12:00:00Z"
}
```

### register_workflow()

1. Check if already validated and registered (idempotent by hash)
2. Run `zigflow validate <file>` via subprocess
3. Write registration entry to `registrations.json`
4. If validated: `asyncio.create_task(trigger_reload())`

### trigger_reload()

Background async task with batching (reload lock + pending flag):

1. Run `scripts/stop_runtime.sh`
2. Run `scripts/start_runtime.sh`
3. Mark all registered entries as `runtime_loaded=True`

Multiple concurrent trigger calls are batched: if a reload is in progress, the pending flag is set and a second reload runs after the first completes.

### sync_pre_existing()

Called on backend startup. Scans `runtime/compiled/**/*.json`, computes DSL hashes, registers any unregistered compiled workflows, then triggers a reload.

---

## 12. Execution Flow

### Compile → Register → Execute pipeline

```
POST /api/v1/workflows/compile
    ↓
CompileWorkflowRequest validated (Pydantic)
    ↓
compiler_service.compile_and_save(workflow, workflow_type, ...)
    ├── compile_workflow_to_dsl()
    │   ├── Phase 0: validate_workflow_structure()
    │   │   ├── Pydantic validation (WorkflowDefinition)
    │   │   └── validate_graph()
    │   ├── Phase A: compile_workflow()
    │   │   ├── generate_node_map()
    │   │   ├── generate_adjacency_list()
    │   │   ├── find_entrypoint()
    │   │   └── traverse_graph()
    │   └── Phase B: generate_dsl()
    │       └── BUILDER_REGISTRY dispatch per traversal entry
    ├── zigflow validate <tmp_file>  ← subprocess validation
    └── save_dsl() to runtime/compiled/...
    ↓
registration_service.register_workflow(dsl_hash, ...)
    └── trigger_reload() [background]
    ↓
CompileWorkflowResponse: {workflow_id, dsl, file_path, content_hash}
```

### Execute Workflow

```
POST /api/v1/executions/{workflow_id}/execute
    ↓
execution_service.execute_workflow(workflow_id, dsl_hash, input_payload)
    ├── find_by_hash(workflow_id, dsl_hash) → DSL file path
    ├── load_dsl(path) → extract workflowType and taskQueue
    └── client.start_workflow(workflowType, input_payload, ...)
        ↓
    Returns: {workflow_id (temporal), run_id, workflow_type, status: "RUNNING"}
```

Temporal workflow ID format: `rf-{visual_workflow_id}-{uuid8hex}` (e.g. `rf-greeting-flow-a1b2c3d4`).

### Trace Execution

```
GET /api/v1/executions/{workflow_id}/runs/{run_id}/trace
    ↓
execution_service.get_execution_trace(workflow_id, run_id)
    ├── handle.fetch_history_events() → activity scheduled/completed/failed events
    ├── find_by_hash(visual_id, dsl_hash, ext=".rf") → ReactFlow JSON
    └── propagate_dag_states(rf_json, event_states, workflow_completed)
        ↓
    Returns: {run_id, status, steps: [{node_id, status, input, output, error, duration_seconds}]}
```

---

## 13. Testing

Test suites in `src/backend/tests/`.

### test_builders.py

Unit tests for each builder in isolation. Covers:
- `build_terminal`: START and END return `None`
- `build_input`: `set` map, `export.as` merge expression, terminal `then: end`
- `build_output`: `set` map from `$context`, terminal `then: end`
- `build_action`: `call: http` with body as single JQ expression, no body when inputs empty, terminal injection
- `build_agent`: registered and unregistered agent fallback, `output_path` selector, terminal injection
- `build_if`: switch cases, branch routing from `branch_map`, missing `branch_map` raises `ValueError`
- `build_condition_expression`: bool, string, numeric, null, list, dict, unsupported operator

### test_validation.py

Unit tests for schema and graph validation failures. Covers:
- Missing START, missing END, multiple STARTs
- Cycle detection (self-loop)
- Missing IF branch, duplicate IF branch
- END with outgoing edges
- Unreachable nodes
- Missing required fields on ACTION, AGENT, INPUT, OUTPUT, IF
- Golden invalid fixture files (7 fixtures: multi-start, no-start, cyclic, missing fields, unknown type, floating node, single-branch IF)
- `resolve_task_name` coverage for all branches including error paths

### test_compiler.py (Snapshot Tests)

Golden snapshot testing. Compiles valid fixtures from `tests/fixtures/valid/` and compares against stored snapshots in `tests/snapshots/`. Run with `UPDATE_SNAPSHOTS=true` to regenerate.

### test_convergence.py

Integration tests specifically for convergence (join node) behavior. Scenarios:
- Single convergence: two IF branches merge at one downstream node
- Double convergence: two branches merge across two downstream nodes
- Nested convergence: nested IF with shared convergence point
- Output convergence: two branches merge at an OUTPUT node
- Agent convergence: two AGENT branches merge at an OUTPUT node

All verify that `then` transitions on branch nodes correctly point to the convergence node's task name.

### test_regression.py

Regression tests against known past bugs. Loads fixtures from `tests/regressions/`:
- `bug_001_ctx_prefix.json`: input fields with `ctx.` prefix
- `bug_002_legacy_branch.json`: backward compatibility with `control.branch` edge metadata
- `bug_003_null_condition.json`: condition builder handles `None` → `null` correctly
- `bug_004_duplicate_branch.json`: duplicate IF branches raise the correct exception

### test_compiler_service.py

Integration tests for `CompilerService`. Tests valid compilation and validation-failure paths using mocks.

### test_stress_and_fuzz.py

Stress tests. Includes Phase 8.0 example workflow certification: compiles `13_weather_assistant.json`, `15_email_validation_sender.json`, and `16_account_routing.json`.

### test_contract.py, test_execution.py, test_runtime_failures.py

Additional contract, execution, and runtime failure coverage.

---

## 14. Convergence Handling

Convergence (join nodes — multiple incoming edges from different branches) is handled entirely at the traversal phase, not at DSL generation time.

### Mechanism

`resolve_successor_task()` in `graph.py` resolves the successor task name for any non-IF node at traversal time. Because `then_transition` is pre-computed based on the graph adjacency (what node a given node points to), any node that points to a shared downstream node automatically gets `then_transition` set to that downstream node's task name.

### then_transition

```python
then_transition = resolve_successor_task(node_id, node_map, adjacency)
```

- For nodes pointing to END: `then_transition = "end"`
- For nodes pointing to a real node: `then_transition = resolve_task_name(successor_node)`

### Branch Convergence

Example: IF node has two branches (A and B) both pointing to C:

```
IF → A → C → END
IF → B → C → END
```

- `A.then_transition = "C_op_c"` (via `resolve_successor_task`)
- `B.then_transition = "C_op_c"` (via `resolve_successor_task`)
- `C.then_transition = "end"` (C points to END)

C itself appears once in the traversal. A and B each carry the correct `then` pointing to C.

### Branch Wrapping

Branch target nodes (those with `incoming_edge_control.branch` in `("true", "false")`) are wrapped in a subflow `do` block by the DSL generator. The `then` transition is propagated to the outer wrapper level, not left inside the inner task body.

---

## 15. Adding New Node Types

Based on the pattern established by existing builders:

1. **Define the node data contract** — add a new `XxxNodeData` Pydantic model in `workflow_sch.py`
2. **Define the node model** — add `XxxNode(BaseModel)` with `type: Literal["NEWTYPE"]`
3. **Add to the discriminated union** — update the `Node` union in `workflow_sch.py`
4. **Create a builder file** — `src/backend/app/builders/new_builder.py`

```python
def build_new(node: dict, *, traversal_entry: dict | None = None) -> dict | None:
    node_id = node["id"]
    task_name = f"{node_id}_new"
    task_body = { ... }   # build from node["data"]

    if traversal_entry:
        then_val = traversal_entry.get("then_transition")
        if not then_val and traversal_entry.get("is_terminal"):
            then_val = "end"
        if then_val:
            task_body["then"] = then_val

    return {task_name: task_body}
```

5. **Register in BUILDERS** — add `"NEWTYPE": build_new` to `src/backend/app/builders/__init__.py`
6. **Add task naming rule** — update `resolve_task_name()` in `graph.py` with a branch for the new type
7. **Write tests** — add unit tests to `test_builders.py`; add valid and invalid fixtures; add snapshot

---

## 16. Constraints

The following constraints are visible in the current implementation:

- **ACTION endpoint is always localhost:8000**: `http://localhost:8000/api/v1/actions/{operation}` — no configurable host or port per node.
- **AGENT fallback endpoint**: unregistered agents fall back to `http://localhost:11000/execute` with no warning during compilation (warning is logged at runtime in `build_agent`).
- **No loop constructs**: no for-loop or while-loop node types are implemented.
- **Condition operators are fixed**: only `==`, `!=`, `>`, `<`, `>=`, `<=` are supported; `in`, `contains`, and complex expressions are not.
- **No VARIABLE node**: explicit variable binding without HTTP calls is not implemented.
- **Zigflow validation requires CLI**: `CompilerService.compile()` shells out to `zigflow validate` via subprocess; the binary must be in PATH.
- **DFS traversal visits shared nodes once**: convergence nodes appear exactly once in the traversal output regardless of how many branches point to them.
- **IF node always emits a `switch` task**: there is no optimized form for simple boolean branches.

---

## Validation Summary

### Deleted Files

- `poc-dsl-compiler/docs/*` (already deleted, confirmed absent)
- `src/backend/docs/*` (already deleted, confirmed absent)

### Sources Used

```
src/backend/app/compiler/graph.py
src/backend/app/compiler/dsl_generator.py
src/backend/app/compiler/workflow_compiler.py
src/backend/app/compiler/exceptions.py
src/backend/app/builders/__init__.py
src/backend/app/builders/terminal_builder.py
src/backend/app/builders/input_builder.py
src/backend/app/builders/output_builder.py
src/backend/app/builders/action_builder.py
src/backend/app/builders/agent_builder.py
src/backend/app/builders/if_builder.py
src/backend/app/builders/condition_builder.py
src/backend/app/schemas/workflow_sch.py
src/backend/app/schemas/compiler_sch.py
src/backend/app/services/compiler_service.py
src/backend/app/services/registration_service.py
src/backend/app/services/execution_service.py
src/backend/app/agents/registry.py
src/backend/app/api/v1/workflow_routes.py
src/backend/app/config/compiler_settings.py
src/backend/tests/test_builders.py
src/backend/tests/test_compiler.py
src/backend/tests/test_validation.py
src/backend/tests/test_convergence.py
src/backend/tests/test_regression.py
src/backend/tests/test_compiler_service.py
src/backend/tests/test_stress_and_fuzz.py
```

### Traceability Mapping

```
Section 1 — Overview
    ← workflow_compiler.py (compile_workflow_to_dsl docstring + phases)

Section 2 — System Architecture
    ← all __init__.py, directory structure

Section 3 — Project Structure
    ← filesystem layout

Section 4 — Workflow Schema Layer
    ← workflow_sch.py (all models)

Section 5 — Graph Validation Layer
    ← graph.py (validate_graph), exceptions.py

Section 6 — Traversal Generation
    ← graph.py (traverse_graph, resolve_successor_task, resolve_task_name)

Section 7 — Builder Architecture
    ← builders/__init__.py, dsl_generator.py (register_builder, BUILDER_REGISTRY)
    ← all builder files (signature, naming convention)

Section 8 — DSL Generation
    ← dsl_generator.py (generate_dsl, branch wrapping logic, save_dsl)

Section 9 — Supported Node Types
    ← terminal_builder.py, input_builder.py, output_builder.py
    ← action_builder.py, agent_builder.py, if_builder.py
    ← test_builders.py (expected DSL output)

Section 10 — Agent Integration
    ← agents/registry.py (AgentRegistry class, _agents dict)
    ← agent_builder.py (build_agent)
    ← workflow_sch.py (AgentNodeData validator)

Section 11 — Registration and Runtime
    ← services/registration_service.py

Section 12 — Execution Flow
    ← services/compiler_service.py
    ← services/registration_service.py
    ← services/execution_service.py
    ← api/v1/workflow_routes.py

Section 13 — Testing
    ← tests/test_builders.py
    ← tests/test_compiler.py
    ← tests/test_validation.py
    ← tests/test_convergence.py
    ← tests/test_regression.py
    ← tests/test_compiler_service.py
    ← tests/test_stress_and_fuzz.py

Section 14 — Convergence Handling
    ← graph.py (resolve_successor_task, traverse_graph)
    ← dsl_generator.py (branch wrapping logic)
    ← tests/test_convergence.py (verified behavior)

Section 15 — Adding New Node Types
    ← pattern derived from all existing builders + workflow_sch.py + graph.py

Section 16 — Constraints
    ← action_builder.py (hardcoded endpoint)
    ← agent_builder.py (fallback endpoint, no warning)
    ← compiler_settings.py, condition_builder.py (operator set)
    ← graph.py (DFS visited set)
```
