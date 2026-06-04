# Workflow Runtime — Project Context

> **Authoritative context document for the `src/` layer.**
> Read this before touching any file in `src/backend/` or `src/frontend/`.

---

## 1. Project Overview

This project is a three-layer system for building, compiling, and executing declarative workflows visually.

| Layer | Status | Description |
|---|---|---|
| **Workflow Builder UI** | Active | ReactFlow-based visual editor. Produces a Workflow JSON. |
| **DSL Compiler** | Active | Transforms Workflow JSON → Zigflow DSL via graph traversal. |
| **Temporal Runtime** | Future | Executes the compiled DSL via Zigflow + Temporal workers. |

The frontend produces a structured JSON document. The backend receives that JSON, compiles it into Zigflow DSL, validates it, and (eventually) executes it.

---

## 2. Current Repository Structure

```
src/
├── README.md          ← this file
├── backend/           ← Python FastAPI backend (compiler + future runtime)
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── workflows.py   ← compile endpoint (to be implemented)
│   │   ├── compiler/              ← DSL compiler pipeline
│   │   ├── builders/              ← per-node-type DSL builder functions
│   │   ├── schemas/               ← Pydantic request/response models
│   │   ├── services/              ← business logic layer
│   │   ├── agents/                ← agent definitions
│   │   ├── repositories/          ← data access layer
│   │   ├── core/                  ← app config, dependencies
│   │   └── main.py                ← FastAPI app entry point
│   ├── temporal/                  ← Temporal worker stubs (future)
│   ├── tests/
│   ├── requirements.txt
│   └── run.py
└── frontend/          ← React + TypeScript + Vite + ReactFlow
    ├── src/
    │   ├── components/
    │   │   ├── CustomNodes.tsx     ← all node renderers
    │   │   ├── Inspector.tsx       ← right-panel node config form
    │   │   ├── Sidebar.tsx         ← node palette
    │   │   ├── Header.tsx
    │   │   ├── Simulator.tsx
    │   │   └── WorkflowStorageModal.tsx
    │   ├── constants/
    │   ├── utils/
    │   ├── types.ts                ← all shared TypeScript types
    │   ├── App.tsx
    │   └── main.tsx
    ├── package.json
    └── vite.config.ts
```

---

## 3. Frontend — Workflow Builder UI

**Stack:** React 18, TypeScript, ReactFlow, Vite.

The UI is a drag-and-drop workflow canvas. Users place nodes, connect them with edges, and configure each node in the Inspector panel. The result is a Workflow JSON that is sent to the backend compiler.

### 3.1 Supported Node Types

| Node Type | Purpose |
|---|---|
| `START` | Workflow entry point. No configuration. |
| `END` | Workflow exit point. No configuration. |
| `INPUT` | Declares external input fields and maps them to named workflow variables. |
| `OUTPUT` | Exposes named workflow variables as the final workflow result. |
| `ACTION` | Calls an external service or performs an operation using workflow context. |
| `AGENT` | Delegates a task to an AI agent. |
| `IF` | Conditional branch — evaluates a boolean expression; routes to two branches. |

### 3.2 Node Data Shape

Every node in the Workflow JSON follows this envelope:

```json
{
  "id": "N1",
  "type": "INPUT",
  "data": {}
}
```

**All node-specific configuration lives inside `data`.** The backend must never read configuration from root node fields — only from `node["data"]`.

#### Node `data` contracts

**INPUT**
```json
{
  "data": {
    "inputs": [
      { "field": "email", "store_as": "user_email", "type": "string" }
    ]
  }
}
```

**OUTPUT**
```json
{
  "data": {
    "outputs": [
      { "field": "message", "type": "string" }
    ]
  }
}
```

**ACTION**
```json
{
  "data": {
    "operation": "send_welcome_email",
    "inputs": { "recipient": "user_email" },
    "output": "send_result"
  }
}
```

**AGENT**
```json
{
  "data": {
    "agent": "agent-id-or-slug"
  }
}
```

**IF**
```json
{
  "data": {
    "left": "user_email",
    "operation": "!=",
    "right": ""
  }
}
```

**START / END** — `data` is empty (`{}`).

### 3.3 Workflow JSON Structure

The full payload sent to the backend:

```json
{
  "nodes": [
    { "id": "N1", "type": "START", "data": {} },
    { "id": "N2", "type": "INPUT", "data": { "inputs": [...] } },
    { "id": "N3", "type": "ACTION", "data": { "operation": "...", "inputs": {...}, "output": "..." } },
    { "id": "N4", "type": "OUTPUT", "data": { "outputs": [...] } },
    { "id": "N5", "type": "END", "data": {} }
  ],
  "edges": [
    { "id": "E1", "source": "N1", "target": "N2" },
    { "id": "E2", "source": "N2", "target": "N3" },
    { "id": "E3", "source": "N3", "target": "N4" },
    { "id": "E4", "source": "N4", "target": "N5" }
  ]
}
```

**IF branch edges** carry an additional `control` field:

```json
{ "id": "E5", "source": "N3", "target": "N4", "control": { "branch": "true" } }
{ "id": "E6", "source": "N3", "target": "N5", "control": { "branch": "false" } }
```

Non-IF edges carry no `control` field.

---

## 4. Backend — Compiler API

**Stack:** Python, FastAPI, Pydantic.

### 4.1 Current API

```
POST /api/v1/workflows/compile
```

**Request body:** Workflow JSON (nodes + edges as described above).

**Response:** Compiled Zigflow DSL (JSON or YAML).

### 4.2 Future APIs

```
POST /api/v1/workflows/execute      ← submit DSL for Temporal execution
GET  /api/v1/workflows/{run_id}     ← poll execution status and result
```

### 4.3 Compiler Pipeline

The compiler is a pure-function pipeline — no classes, no global state, no registry.

```
Workflow JSON  ({nodes, edges})
       │
       ▼
  generate_node_map()         →  node_id → node dict
       │
       ▼
  generate_adjacency_list()   →  source_id → [target_id, ...]
       │
       ▼
  find_entrypoint()           →  ID of the START node
       │
       ▼
  traverse_graph()            →  list[TraversalEntry]  (DFS preorder)
       │
       ▼
  generate_dsl()              →  Zigflow DSL dict
       │
       ▼
  zigflow validate            →  validation pass/fail
```

**Critical rules:**

- Do not use the raw `nodes` array order to determine execution order — use graph traversal only.
- Shared nodes (multiple incoming edges) appear exactly once in traversal output.
- Only `list[TraversalEntry]` crosses the Phase A / Phase B boundary.
- Each builder function owns exactly one node type. Builders never import from `compiler.py`.
- `compiler.py` owns graph logic and never imports from `builders/`.

### 4.4 DSL Output (Zigflow)

The compiler emits [CNCF Serverless Workflow DSL v1.0.0](https://github.com/serverlessworkflow/specification) compatible YAML/JSON, executed by the Zigflow runtime on top of Temporal.

Node type → Zigflow task mapping:

| Node Type | Zigflow Task |
|---|---|
| `INPUT` | `set` + `export.as` |
| `ACTION` | `call: http` + `export.as` |
| `OUTPUT` | `set` (expose result) |
| `IF` | `switch` |
| `AGENT` | `run` (sub-workflow or shell) |
| `START` / `END` | No DSL output |

---

## 5. Runtime Goal (Future)

Once the compiler produces validated DSL:

```
Zigflow DSL
    │
    ▼
Temporal Workflow (via Zigflow worker)
    │
    ▼
Activities  (HTTP calls, data transforms)
    │
    ▼
Agent Execution  (AI agent steps)
    │
    ▼
Workflow Result
```

The `src/backend/temporal/` directory is the placeholder for Temporal worker code. No execution logic exists there yet.

---

## 6. Key Rules for Future Contributors

1. **Read from `node["data"]` only.** Never read configuration from root node fields (`id`, `type` are structural only).
2. **Traversal determines order.** Never iterate `nodes[]` array position.
3. **IF branch edges carry `control.branch`.** All other edges have no `control` key.
4. **Builders are pure functions.** No classes, no side effects, no shared state.
5. **The compile endpoint is the integration point.** The frontend sends Workflow JSON; the backend returns DSL. These are the only two contracts that must stay stable.
