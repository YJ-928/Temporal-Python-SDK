# 02 — Graph Schema V1

## Input Document

The compiler accepts a single JSON object with four top-level keys.

```json
{
  "version": "1.0",
  "metadata": {},
  "nodes": [],
  "edges": []
}
```

### `version`
String. Semantic version of this graph definition. `"1.0"` for all V1 graphs.

### `metadata`
Object. Optional workflow-level settings. Passed through to the Zigflow `document` block and `metadata.activityOptions`.

```json
{
  "metadata": {
    "workflowName": "my-workflow",
    "taskQueue": "my-queue",
    "workflowType": "my-type",
    "activityOptions": {
      "startToCloseTimeout": { "minutes": 5 }
    }
  }
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `workflowName` | yes | string | Becomes `document.name` |
| `taskQueue` | yes | string | Becomes `document.taskQueue` |
| `workflowType` | yes | string | Becomes `document.workflowType` |
| `activityOptions` | no | object | Passed to `document.metadata.activityOptions` |

### `nodes`
Array of node objects. See Node Schema below.

### `edges`
Array of edge objects. See Edge Schema below.

---

## Node Schema

Every node shares this base structure:

```json
{
  "id": "node-1",
  "type": "ACTION",
  "position": { "x": 0, "y": 0 },
  "data": {}
}
```

| Field | Required | Type | Notes |
|---|---|---|---|
| `id` | yes | string | Unique within the graph. Used as edge source/target. |
| `type` | yes | string enum | One of the 8 allowed node types (see below). |
| `position` | yes | object | UI rendering only. Compiler ignores `x`/`y`. |
| `data` | yes | object | Type-specific configuration. All logic lives here. |

### Allowed Node Types

```
START
END
ACTION
VARIABLE
WORKFLOW
IF
PARALLEL
WAIT
```

No other values are accepted. The validator must reject any node with an unrecognised type.

---

## Node `data` Schemas by Type

### START
Graph-only node. Marks the single entry point of the workflow. Emits no DSL task.

```json
{
  "id": "start-1",
  "type": "START",
  "position": { "x": 0, "y": 0 },
  "data": {}
}
```

`data` is empty or ignored. The compiler uses this node only to determine the traversal root.

---

### END
Graph-only node. Marks the single exit point of the workflow. Emits no DSL task.

```json
{
  "id": "end-1",
  "type": "END",
  "position": { "x": 0, "y": 0 },
  "data": {}
}
```

`data` is empty or ignored. The compiler uses this node only to confirm the traversal terminates.

---

### ACTION
Maps to one of four Zigflow task kinds. The `subtype` field in `data` controls which one.

```json
{
  "id": "action-1",
  "type": "ACTION",
  "position": {},
  "data": {
    "name": "fetchUser",
    "subtype": "call:http",
    "method": "get",
    "endpoint": "https://api.example.com/users/1",
    "outputAs": "user"
  }
}
```

| Subtype | Zigflow task | Required `data` fields |
|---|---|---|
| `call:http` | `call: http` | `method`, `endpoint` |
| `call:grpc` | `call: grpc` | `endpoint`, `proto` (optional) |
| `run:script` | `run: { script: { ... } }` | `language`, `code` |
| `run:shell` | `run: { shell: { ... } }` | `command` |

Common optional fields:
- `name` — used as the task name in the DSL `do` list (defaults to node `id`)
- `outputAs` — becomes `output.as` expression

---

### VARIABLE
Maps to a `set` or `export` task. Controls workflow state.

```json
{
  "id": "var-1",
  "type": "VARIABLE",
  "position": {},
  "data": {
    "name": "captureInput",
    "operation": "set",
    "assignments": {
      "userId": "${ $input.userId }",
      "requestId": "${ uuid }"
    }
  }
}
```

| Field | Required | Values | Zigflow mapping |
|---|---|---|---|
| `name` | no | string | Task name in `do` list |
| `operation` | yes | `"set"` or `"export"` | `set: {...}` or `export: { as: ... }` |
| `assignments` | yes | object | Key-value pairs; values are jq expressions |

---

### WORKFLOW
Maps to a Zigflow sub-workflow invocation.

```json
{
  "id": "wf-1",
  "type": "WORKFLOW",
  "position": {},
  "data": {
    "name": "runChildWorkflow",
    "workflowType": "child-workflow-type",
    "taskQueue": "child-queue",
    "input": "${ $data.someValue }"
  }
}
```

| Field | Required | Notes |
|---|---|---|
| `name` | no | Task name in DSL |
| `workflowType` | yes | Temporal workflow type of the child |
| `taskQueue` | no | Defaults to parent's task queue |
| `input` | no | jq expression for child input |

Maps to:
```yaml
run:
  workflow:
    name: child-workflow-type
    input: ${ $data.someValue }
```

---

### IF
Maps to a Zigflow `switch` task. The node itself contains the branching condition.

```json
{
  "id": "if-1",
  "type": "IF",
  "position": {},
  "data": {
    "name": "routeByStatus",
    "cases": [
      {
        "label": "active",
        "when": "${ $data.user.status == \"active\" }"
      },
      {
        "label": "inactive",
        "when": "${ $data.user.status == \"inactive\" }"
      }
    ],
    "default": true
  }
}
```

**Edge convention for IF:**
- The compiler resolves `cases[0]` to the first child edge, `cases[1]` to the second child edge, by edge order.
- The edge with `"default": true` in cases resolves to any remaining child that does not match a case label.
- Edge `data` carries NO conditions. All condition expressions live in `data.cases[].when`.

| Field | Required | Notes |
|---|---|---|
| `name` | no | Task name in DSL |
| `cases` | yes | Array of `{ label, when }` objects |
| `default` | no | If true, appends a `default` case pointing to the last unmatched child |

---

### PARALLEL
Maps to a Zigflow `fork` task.

```json
{
  "id": "parallel-1",
  "type": "PARALLEL",
  "position": {},
  "data": {
    "name": "runInParallel",
    "compete": false
  }
}
```

| Field | Required | Values | Notes |
|---|---|---|---|
| `name` | no | string | Task name |
| `compete` | yes | `true` or `false` | `true` = race (first wins); `false` = all must complete |

**Edge convention for PARALLEL:**
- Each outgoing edge from a PARALLEL node becomes one `branch` in the `fork` block.
- All children run concurrently. The compiler wraps each child subtree in a `do` branch.

---

### WAIT
Maps to one of three Zigflow task kinds. The `subtype` field controls which one.

```json
{
  "id": "wait-1",
  "type": "WAIT",
  "position": {},
  "data": {
    "name": "pauseFor5s",
    "subtype": "duration",
    "seconds": 5
  }
}
```

| Subtype | Zigflow task | Required `data` fields |
|---|---|---|
| `"duration"` | `wait: { seconds/minutes/hours }` | One of `seconds`, `minutes`, `hours` |
| `"signal"` | `listen: { to: { one: { with: { id, type } } } }` | `signalId`, `signalType` (default `"signal"`) |

Signal example:
```json
{
  "data": {
    "name": "waitForApproval",
    "subtype": "signal",
    "signalId": "approve",
    "signalType": "signal"
  }
}
```

---

## Edge Schema

Edges are intentionally minimal. No execution logic.

```json
{
  "id": "edge-1",
  "source": "node-a",
  "target": "node-b"
}
```

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Unique identifier |
| `source` | yes | ID of the source node |
| `target` | yes | ID of the target node |

All routing and condition logic lives in the **source node's `data`**, not in the edge. The compiler uses edge order (as supplied in the `edges` array) to resolve positional references (e.g., IF case[0] → first child edge).

---

## Graph Constraints (V1)

The compiler enforces these before emitting any DSL:

1. **Exactly one START node** — any other count is a validation error.
2. **Exactly one END node** — any other count is a validation error.
3. **No cycles** — the graph must be a DAG (directed acyclic graph). Detected by DFS with a "grey" visited set.
4. **Max one parent per node** — every node except START must have at most one incoming edge. This enforces the tree constraint.
5. **Every node reachable** — BFS/DFS from START must visit every node. Unreachable nodes are a validation error.
6. **END has no outgoing edges** — the END node must be a leaf.
7. **START has no incoming edges** — the START node must be the root.
8. **IF nodes must have at least 2 outgoing edges** — one per case.
9. **PARALLEL nodes must have at least 2 outgoing edges** — one per branch.
10. **All edge references are valid** — every `source` and `target` ID must exist in `nodes`.

---

## Full Example Graph

```json
{
  "version": "1.0",
  "metadata": {
    "workflowName": "user-onboarding",
    "taskQueue": "onboarding-queue",
    "workflowType": "user-onboarding"
  },
  "nodes": [
    { "id": "s", "type": "START", "position": {}, "data": {} },
    {
      "id": "v1",
      "type": "VARIABLE",
      "position": {},
      "data": {
        "name": "captureInput",
        "operation": "set",
        "assignments": { "userId": "${ $input.userId }" }
      }
    },
    {
      "id": "a1",
      "type": "ACTION",
      "position": {},
      "data": {
        "name": "fetchUser",
        "subtype": "call:http",
        "method": "get",
        "endpoint": "https://api.example.com/users/${ $data.userId }"
      }
    },
    {
      "id": "w1",
      "type": "WAIT",
      "position": {},
      "data": { "name": "pause", "subtype": "duration", "seconds": 5 }
    },
    { "id": "e", "type": "END", "position": {}, "data": {} }
  ],
  "edges": [
    { "id": "e1", "source": "s",  "target": "v1" },
    { "id": "e2", "source": "v1", "target": "a1" },
    { "id": "e3", "source": "a1", "target": "w1" },
    { "id": "e4", "source": "w1", "target": "e"  }
  ]
}
```
