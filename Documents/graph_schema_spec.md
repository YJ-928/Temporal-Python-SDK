# Graph Schema Specification

> **Status:** R&D / Design Phase
> **Purpose:** Defines the exact JSON structure of a `WorkflowGraph` — the primary input to the compiler pipeline.

---

## 1. What Is a WorkflowGraph?

A `WorkflowGraph` is a directed graph that describes workflow behavior at the structural level. It is the *source of truth* produced by the UI canvas and stored as a JSONB blob in `workflow_versions.graph_json`.

The graph contains:
- **Nodes** — typed units of work or control flow
- **Edges** — typed connections between node handles
- **Document metadata** — task queue, workflow type, version

The compiler transforms this graph into Zigflow YAML in several passes. The graph itself never contains Zigflow syntax — it is DSL-agnostic.

---

## 2. Top-Level Schema

```json
{
  "task_queue": "string (required, no spaces)",
  "workflow_type": "string (required, no spaces)",
  "version": "string (semver, default '1.0.0')",
  "metadata": { ... },
  "nodes": [ Node, ... ],
  "edges": [ Edge, ... ]
}
```

### Field constraints

| Field | Type | Required | Rules |
|---|---|---|---|
| `task_queue` | string | yes | no spaces; must match Zigflow worker config |
| `workflow_type` | string | yes | no spaces; must match Temporal workflow type |
| `version` | string | no | semver recommended; stored in `document.version` |
| `metadata` | object | no | passed through to `document.metadata` |
| `nodes` | array | yes | min 1 START, min 1 END |
| `edges` | array | yes | may be empty for trivial (START→END) graphs |

---

## 3. Node Schema

```json
{
  "id": "string (unique within graph)",
  "type": "NodeType enum",
  "label": "string (optional, UI display)",
  "config": { ... },
  "inputs": [ NodeHandle, ... ],
  "outputs": [ NodeHandle, ... ],
  "position": { "x": float, "y": float },
  "metadata": { ... }
}
```

### NodeHandle schema

```json
{
  "id": "string (unique within node)",
  "label": "string (optional)"
}
```

Handles are the named connection points on a node. An edge connects from a *source handle* on one node to a *target handle* on another. The `inputs` and `outputs` arrays define which handles exist. The compiler uses handles to determine edge semantics (is this the `true` branch output? the `error` output?).

### NodeType enum — V1 (8 types)

```
START      END        ACTION     VARIABLE
IF         PARALLEL   WAIT       WORKFLOW
```

---

## 4. Edge Schema

```json
{
  "id": "string (unique within graph)",
  "source": "node id",
  "target": "node id",
  "source_handle": "handle id on source node (optional)",
  "target_handle": "handle id on target node (optional)",
  "edge_type": "EdgeType enum (default: DEFAULT)",
  "label": "string (optional)"
}
```

### EdgeType enum — V1 (6 types)

```
DEFAULT    SUCCESS    ERROR    TRUE    FALSE    LOOP
```

**Important:** `edge_type` is what gives the edge semantic meaning. Two edges from the same IF node with `edge_type: TRUE` and `edge_type: FALSE` respectively tell the compiler which branch is which. The `source_handle` corresponds to the output handle ID on the source node (e.g., `"true"` or `"false"`). Both carry the same information — the compiler uses `edge_type` as the primary routing key and `source_handle` as validation.

---

## 5. Complete Schema Example — Hello World

A minimal workflow: START → ACTION (HTTP GET) → END.

```json
{
  "task_queue": "my-queue",
  "workflow_type": "hello-world",
  "version": "1.0.0",
  "nodes": [
    {
      "id": "node-start",
      "type": "START",
      "label": "Start",
      "config": {},
      "inputs": [],
      "outputs": [{ "id": "output", "label": "Output" }],
      "position": { "x": 100, "y": 200 }
    },
    {
      "id": "node-fetch",
      "type": "ACTION",
      "label": "Fetch User",
      "config": {
        "protocol": "http",
        "method": "GET",
        "endpoint": "https://api.example.com/users/1",
        "outputKey": "user"
      },
      "inputs": [{ "id": "input", "label": "Input" }],
      "outputs": [
        { "id": "success", "label": "Success" },
        { "id": "error", "label": "Error" }
      ],
      "position": { "x": 300, "y": 200 }
    },
    {
      "id": "node-end",
      "type": "END",
      "label": "End",
      "config": {},
      "inputs": [{ "id": "input", "label": "Input" }],
      "outputs": [],
      "position": { "x": 500, "y": 200 }
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "node-start",
      "target": "node-fetch",
      "source_handle": "output",
      "target_handle": "input",
      "edge_type": "DEFAULT"
    },
    {
      "id": "edge-2",
      "source": "node-fetch",
      "target": "node-end",
      "source_handle": "success",
      "target_handle": "input",
      "edge_type": "SUCCESS"
    }
  ]
}
```

**Expected Zigflow YAML output:**

```yaml
document:
  dsl: "1.0.0"
  taskQueue: my-queue
  workflowType: hello-world
  version: "1.0.0"
do:
  - fetchUser:
      call: http
      with:
        method: GET
        endpoint: https://api.example.com/users/1
      output:
        as: "${ $context + {user: .} }"
      export:
        as: "${ $context + {user: .} }"
```

START and END emit no Zigflow tasks.

---

## 6. Conditional Branch Example — IF Node

A workflow that checks if a user is active and routes accordingly.

```json
{
  "task_queue": "check-queue",
  "workflow_type": "check-user",
  "version": "1.0.0",
  "nodes": [
    { "id": "n-start", "type": "START", ... },
    {
      "id": "n-fetch",
      "type": "ACTION",
      "config": {
        "protocol": "http",
        "method": "GET",
        "endpoint": "https://api.example.com/users/${ $input.userId }",
        "outputKey": "user"
      }
    },
    {
      "id": "n-if",
      "type": "IF",
      "label": "Is Active?",
      "config": {
        "condition": "${ $context.user.active == true }"
      },
      "outputs": [
        { "id": "true", "label": "Active" },
        { "id": "false", "label": "Inactive" }
      ]
    },
    {
      "id": "n-notify",
      "type": "ACTION",
      "label": "Send Active Notification",
      "config": {
        "protocol": "http",
        "method": "POST",
        "endpoint": "https://api.example.com/notify",
        "body": { "message": "${ 'User ' + $context.user.name + ' is active' }" }
      }
    },
    {
      "id": "n-flag",
      "type": "VARIABLE",
      "label": "Flag Inactive",
      "config": {
        "assignments": { "status": "\"inactive\"" }
      }
    },
    { "id": "n-end", "type": "END", ... }
  ],
  "edges": [
    { "id": "e1", "source": "n-start", "target": "n-fetch", "edge_type": "DEFAULT" },
    { "id": "e2", "source": "n-fetch", "target": "n-if", "edge_type": "SUCCESS" },
    { "id": "e3", "source": "n-if", "target": "n-notify", "source_handle": "true", "edge_type": "TRUE" },
    { "id": "e4", "source": "n-if", "target": "n-flag", "source_handle": "false", "edge_type": "FALSE" },
    { "id": "e5", "source": "n-notify", "target": "n-end", "edge_type": "SUCCESS" },
    { "id": "e6", "source": "n-flag", "target": "n-end", "edge_type": "SUCCESS" }
  ]
}
```

**Visual representation:**

```
START → fetchUser → [IF: active?]
                         │ TRUE  → sendNotification → END
                         │ FALSE → flagInactive     → END
```

---

## 7. Parallel Execution Example — PARALLEL Node

```json
{
  "id": "n-parallel",
  "type": "PARALLEL",
  "label": "Fetch All",
  "config": { "compete": false },
  "outputs": [
    { "id": "success", "label": "All Done" },
    { "id": "error", "label": "Error" }
  ]
}
```

For a PARALLEL node, the outbound edges must be **branch edges** — each edge connects to a different branch. The edge type on branch edges is conventionally `SUCCESS` (not `TRUE`/`FALSE`). The compiler identifies branches by enumerating all non-ERROR outbound edges from the PARALLEL node.

```
PARALLEL node
    │ SUCCESS (branch 1) → fetchUsers → ...
    │ SUCCESS (branch 2) → fetchOrders → ...
    │ SUCCESS (branch 3) → fetchProducts → ...
    │ ERROR             → handleError → END
```

**Open question:** How does the compiler distinguish "branch edges" from a single sequential SUCCESS edge on a PARALLEL node? Current proposal: all SUCCESS outbound edges from PARALLEL are treated as branches. The compiler raises `INSUFFICIENT_BRANCHES` if there is only one.

---

## 8. Signal Wait Example — WAIT Node

```json
{
  "id": "n-wait",
  "type": "WAIT",
  "label": "Wait for Approval",
  "config": {
    "mode": "signal",
    "signalName": "approve",
    "signalType": "signal",
    "outputKey": "approvalData"
  }
}
```

**Expected Zigflow task:**
```yaml
- waitForApproval:
    listen:
      to:
        one:
          with:
            id: approve
            type: signal
    export:
      as: "${ $context + {approvalData: .} }"
```

Timer variant:
```json
{
  "config": {
    "mode": "timer",
    "duration": { "minutes": 30 }
  }
}
```

**Expected Zigflow task:**
```yaml
- waitTimer:
    wait:
      minutes: 30
```

---

## 9. Schema Alternatives Considered

### Alternative A: Separate node/edge tables in the database

**Rejected.** The graph is always read and written as a unit. Relational tables would require joins to reconstruct the graph, add migration complexity per schema change, and provide no query benefit in V1. Blobs also allow structural evolution without DB migrations.

### Alternative B: GraphQL for the API (instead of REST + JSON blob)

**Deferred to V2.** GraphQL would enable fine-grained node/edge queries. Not needed until the UI canvas needs partial graph updates (V2 collaborative editing).

### Alternative C: Edge semantics via handle ID only (no `edge_type`)

**Rejected.** Relying solely on `source_handle` (e.g., handle id `"true"`) for routing would require the compiler to know the semantic meaning of each handle name per node type, and would break if the UI generates generic handle IDs (UUIDs). `edge_type` is an explicit, validated enum that makes routing unambiguous regardless of handle naming.

### Alternative D: Separate edge schemas per node type

**Rejected for V1.** A single `EdgeType` enum across all nodes is simpler. Per-type edge schemas would enable richer validation but would complicate the validator. Deferred to V2.

---

## 10. Validation Rules Derived from Schema

The following rules are checked by `graph_engine/validator.py` on the raw graph before normalization:

| Rule | Error Code |
|---|---|
| Exactly one `START` node | `MISSING_START` / `MULTIPLE_START` |
| At least one `END` node reachable from `START` | `MISSING_END` |
| No isolated nodes (unreachable from `START`) | `UNREACHABLE_NODE:{id}` |
| No self-loops on non-LOOP edges | `INVALID_SELF_LOOP:{id}` |
| `IF` node has exactly one `TRUE` and one `FALSE` outbound edge | `MISSING_BRANCH:{id}` |
| `PARALLEL` node has ≥ 2 non-ERROR outbound edges | `INSUFFICIENT_BRANCHES:{id}` |
| All `config` required fields present per node type | `MISSING_CONFIG:{node_id}.{field}` |
| Edge `source_handle` exists in source node's `outputs` (if specified) | `INVALID_HANDLE:{edge_id}` |
| Edge `target_handle` exists in target node's `inputs` (if specified) | `INVALID_HANDLE:{edge_id}` |
| No cycles except `LOOP`-typed back-edges | `CYCLE_DETECTED` |
| `task_queue` and `workflow_type` non-empty, no spaces | `INVALID_METADATA` |

---

## 11. Graph Schema Open Questions

| Question | Why It Matters |
|---|---|
| Should `config` be validated against a per-node JSON Schema at the raw graph level, or only after normalization? | If at raw level, the validator needs to load the node registry. If after normalization, validation errors report later and may be harder to surface to the user. |
| How should the graph represent a PARALLEL node's JOIN point? Is there an implicit join at the downstream merge, or does the UI need to draw an explicit join node? | Affects how the IR builder reconstructs branches and when it considers a branch complete. |
| What is the graph representation of an IF node where both true and false branches converge on the same downstream node? | Two edges from different source nodes to the same target — is this valid? The IR builder must detect this convergence pattern. |
| Should `position` be stripped before storing in `graph_json` (compiler never needs it), or kept for round-tripping back to the UI? | Storage size vs. UI fidelity tradeoff. |
