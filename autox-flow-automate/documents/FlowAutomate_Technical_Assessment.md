# FlowAutomate Technical Assessment

**Prepared by:** AutoX Engineering  
**Date:** 2026-06-13  
**Branch:** `refactor/flowautomate-rebrand`  
**Status:** FlowAutomate v1 — Rebrand Complete, Ready for Backend Restructure

---

## 1. Executive Summary

FlowAutomate is an AutoX visual workflow automation platform built on Temporal and Zigflow. It consists of a React 19 + ReactFlow frontend (visual workflow editor), a FastAPI backend (DSL compiler + Temporal execution engine), and a Zigflow YAML runtime that hot-reloads compiled workflows.

**Current state (v1):**
- Compiler pipeline: complete and production-grade — strict DAG validation, 7 node types, 11 validation rules, 17 golden snapshots, 52 passing tests
- API surface: 4 route modules (workflows, executions, health, catalog) — all functional
- Execution engine: Temporal integration working — compile → register → execute → trace → cancel/terminate
- Frontend: full editor + compile + execute + trace + history + cancel flow
- Temporal runtime: SQLite (dev mode only) — must migrate to PostgreSQL for production

**Gap to full FlowAutomate v4 specification:**
- 7 of 14 required node types implemented (missing: Loop, Wait-Timer, Wait-Process Any/All, Router, Human Task, Process/Flow Call, Connector multi-mode)
- No PostgreSQL persistence (file-based + Temporal SQLite dev mode)
- Frontend App.tsx (1074 LOC) needs hooks extraction for maintainability
- No vault/secrets, no typed error codes, no scheduler/webhook triggers

**Immediate next step:** `refactor/backend-structure` — move to production FastAPI layout + PostgreSQL models + Temporal PostgreSQL persistence.

---

## 2. Current State Assessment

### 2.1 What Works Today

| Capability | Status | Notes |
|---|---|---|
| Visual workflow editor | Working | React 19 + ReactFlow 11.11.4 |
| Drag-and-drop node canvas | Working | 7 node types rendered |
| Undo / Redo | Working | History stack in App.tsx |
| Load example workflows | Working | 4 built-in examples |
| Save / load locally | Working | localStorage (key: `flowautomate-saved-workflows`) |
| DSL compilation | Working | Strict DAG → Zigflow JSON |
| Compile validation errors | Working | Pydantic + graph errors surfaced to UI |
| Workflow registration | Working | Zigflow hot-reload via `registration_service` |
| Temporal execution | Working | `execution_service.py` → Temporal gRPC |
| Execution history | Working | `/api/v1/executions/{id}/history` |
| Execution trace | Working | `/api/v1/executions/{id}/{run_id}/trace` |
| Cancel workflow | Working | Temporal cancel signal |
| Terminate workflow | Working | Temporal terminate with reason |
| Agent catalog | Working | 4 registered agents (weather, email-validator, email-sender, + 1) |
| Operation catalog | Working | `/api/v1/catalog/operations` |
| Health check | Working | `/api/v1/health/system` — all services |
| Test suite | Working | 52 tests passing, 17 golden snapshots |

### 2.2 What Is Partial or Limited

| Capability | Status | Notes |
|---|---|---|
| Replay engine | Partial | `replay_engine.py` exists but not wired into trace UI |
| Execution metrics | Partial | Trace steps exist; aggregate metrics not exposed |
| Frontend hooks split | Deferred | App.tsx 1074 LOC — hooks mixed into component |
| Import/export JSON | Partial | Export works; import from JSON file not implemented |

### 2.3 What Is Not Implemented

| Capability | Notes |
|---|---|
| PostgreSQL persistence | File-based only; no SQLAlchemy models |
| Temporal PostgreSQL | Uses `temporal server start-dev` (SQLite) |
| Collaboration / multi-user | Not implemented |
| Workflow versioning (server-side) | File versioning only via content hash |
| Vault / secrets management | Not implemented |
| Scheduler / webhook triggers | Not implemented |
| Loop node type | Not implemented |
| Wait-Timer node type | Not implemented |
| Router node type (N-branch fan-out) | Not implemented |
| Human Task node type | Not implemented |
| Process/Flow Call node type | Not implemented |
| Connector node (3-mode) | Not implemented |

---

## 3. Feature Inventory

### 3.1 Backend Feature Inventory

| Subsystem | File(s) | LOC | Status |
|---|---|---|---|
| Compiler — entry point | `app/compiler/workflow_compiler.py` | 103 | Complete |
| Compiler — graph analysis | `app/compiler/graph.py` | 402 | Complete |
| Compiler — DSL generation | `app/compiler/dsl_generator.py` | 113 | Complete |
| Compiler — exceptions | `app/compiler/exceptions.py` | — | Complete |
| Builder — terminal (START/END) | `app/builders/terminal_builder.py` | — | Complete |
| Builder — INPUT | `app/builders/input_builder.py` | — | Complete |
| Builder — OUTPUT | `app/builders/output_builder.py` | — | Complete |
| Builder — ACTION | `app/builders/action_builder.py` | — | Complete |
| Builder — AGENT | `app/builders/agent_builder.py` | — | Complete |
| Builder — IF | `app/builders/if_builder.py` | — | Complete |
| Builder — condition util | `app/builders/condition_builder.py` | — | Complete |
| Pydantic schemas — workflow | `app/schemas/workflow_sch.py` | — | Complete |
| Pydantic schemas — compiler | `app/schemas/compiler_sch.py` | — | Complete |
| CompilerService | `app/services/compiler_service.py` | — | Complete |
| RegistrationService | `app/services/registration_service.py` | — | Complete |
| ExecutionService | `app/services/execution_service.py` | — | Complete |
| StorageService | `app/services/storage_service.py` | — | Complete (file-based) |
| ReplayEngine | `app/services/replay_engine.py` | — | Partial |
| AgentRegistry | `app/agents/registry.py` | — | Complete (4 agents) |
| Workflow routes | `app/api/v1/workflow_routes.py` | — | Complete |
| Execution routes | `app/api/v1/execution_routes.py` | — | Complete |
| Health routes | `app/api/v1/health_routes.py` | — | Complete |
| Catalog routes | `app/api/v1/catalog_routes.py` | — | Complete |
| Settings | `app/config/settings.py` | — | Complete |
| Compiler settings | `app/config/compiler_settings.py` | — | Complete |
| Test suite | `tests/` (10 modules) | — | 52 tests, 17 snapshots |

### 3.2 Frontend Feature Inventory

| Feature | File(s) | Status |
|---|---|---|
| Canvas / editor | `App.tsx`, `components/Canvas.tsx` | Complete |
| Node palette / sidebar | `components/NodePalette.tsx` | Complete |
| Node inspector | `components/Inspector.tsx` | Complete |
| Compile & validate button | `components/Header.tsx` | Complete |
| Execute button | `components/Header.tsx` | Complete |
| Simulator / trace panel | `components/Simulator.tsx` | Complete |
| Save / load modal | `components/SaveLoadModal.tsx` | Complete |
| Settings drawer | `components/SettingsDrawer.tsx` | Complete |
| localStorage persistence | `utils/localWorkflowStorage.ts` | Complete |
| Compiler API client | `services/compilerApi.ts` | Complete |
| Export utility | `utils/exportWorkflow.ts` | Complete |
| Error handler | `utils/errorHandler.ts` | Complete |
| Execution polling | App.tsx (inline) | Works; hooks extraction deferred |
| Undo / redo | App.tsx (inline) | Works; hooks extraction deferred |
| Import from JSON file | Not implemented | — |
| Collaboration | Not implemented | — |

---

## 4. Compiler Assessment

### 4.1 Architecture

The compiler is a two-phase pipeline:

**Phase A — Graph Analysis (`graph.py`, 402 LOC)**
- Builds an adjacency list from the node/edge input
- Runs `validate_graph()` — 11 validation rules (see §4.3)
- Runs `traverse_graph()` — DFS preorder traversal with visited set (cycle detection)
- Returns an ordered list of `(node, metadata)` pairs for Phase B

**Phase B — DSL Generation (`dsl_generator.py` + builders)**
- Iterates the traversal result in DFS preorder order
- Dispatches each node to its registered builder (`BUILDERS[node_type]`)
- Assembles the Zigflow DSL `document` object
- Returns the complete DSL dict; `CompilerService` validates, saves, and registers it

**Key guarantee:** The compiler is deterministic — identical input always produces identical output. This is enforced by 17 golden snapshot tests.

### 4.2 DFS Preorder Traversal

The traversal is DFS preorder with a visited set. Traversal starts from the START node and follows edges. The visited set prevents infinite recursion on any graph that passes validation (no cycles possible post-validate). The order determines the `states[]` order in the Zigflow DSL.

IF nodes: both `true` and `false` branches are traversed depth-first before advancing to the convergence point. The traversal discovers the convergence node at the earliest common ancestor reachable from both branches.

### 4.3 Validation Rules (11 rules in `graph.py`)

| # | Rule |
|---|---|
| 1 | Exactly one START node |
| 2 | Exactly one END node |
| 3 | All edges reference nodes that exist |
| 4 | START has exactly one outgoing edge |
| 5 | END has no outgoing edges |
| 6 | Every non-terminal node has at least one outgoing edge |
| 7 | IF node has exactly two outgoing edges (true/false labels required) |
| 8 | All non-START nodes are reachable from START |
| 9 | All nodes reach END |
| 10 | No cycles (DFS back-edge detection) |
| 11 | Non-IF nodes have exactly one outgoing edge |

### 4.4 Explicit Compiler Constraints (Current Limitations)

These are design constraints of the current v1 compiler, not bugs:

| Constraint | Implication |
|---|---|
| No back edges (rule 10) | Loop/iteration workflows cannot be compiled today |
| Single outgoing edge for non-IF nodes (rule 11) | True parallel fan-out (AND-split) is not supported |
| No LOOP node type | All iteration must be done inside ACTION/AGENT activities |
| No WAIT node type | Timer-based pauses require custom activity workarounds |
| No ROUTER node type | N-way branches require nested IF chains |
| No SUBPROCESS/FLOW-CALL node | Cannot call sub-workflows from DSL |
| No back-reference to previous node output except via `$` expressions | No complex data flow wiring in DSL |

### 4.5 Node Type Contract Summary

| Type | Color | Required Fields | DSL Output |
|---|---|---|---|
| START | Green | none | `{"name": "start", "type": "start"}` |
| END | Red | none | `{"name": "end", "type": "end"}` |
| INPUT | Blue | label, inputSchema | inject block + data |
| OUTPUT | Purple | label, outputMapping | inject block + set/export |
| ACTION | Orange | label, operation, parameters | action-type state |
| AGENT | Cyan | label, agentId, input, output | action-type via agent op |
| IF | Yellow | label, condition | switch-type state |

---

## 5. Requirement Gap Matrix — FlowAutomate v4 Specification

Based on the FlowAutomate v4 specification document.

### 5.1 Node Types

| Required Node Type | Implemented | Gap Notes |
|---|---|---|
| START | Yes | — |
| END | Yes | — |
| INPUT | Yes | — |
| OUTPUT | Yes | — |
| ACTION | Yes | — |
| AGENT | Yes | — |
| IF (binary branch) | Yes | — |
| LOOP | **No** | Requires DAG cycle support or separate iteration model |
| Wait-Timer | **No** | Temporal timer signal needed |
| Wait-Process Any | **No** | Temporal signal/promise.any pattern |
| Wait-Process All | **No** | Temporal promise.all pattern |
| Router (N-branch) | **No** | First-match or fan-out; N outgoing edges |
| Human Task | **No** | Signal-driven pause + external form |
| Process/Flow Call | **No** | Child workflow invocation in DSL |
| Connector (3-mode: HTTP/Agent/Internal) | **No** | ACTION covers HTTP; Agent mode works; internal not modeled |
| Default Inputs | **No** | Static node input defaults not stored per-node |
| Listener / Event Trigger | **No** | Webhook/event source not implemented |
| Notification Node | **No** | Notification action not a first-class type |
| Scheduler Trigger | **No** | Temporal schedule not wired to UI |

### 5.2 Platform Capabilities

| Required Capability | Implemented | Gap Notes |
|---|---|---|
| Visual workflow builder | Yes | — |
| DSL compile → Temporal execution | Yes | — |
| Execution history | Yes | — |
| Execution trace | Yes | — |
| Cancel / terminate | Yes | — |
| PostgreSQL persistence | **No** | File-based only |
| Workflow versioning (DB) | **No** | Content hash exists; no DB version table |
| Collaboration (multi-user) | **No** | — |
| Vault / secrets management | **No** | — |
| Typed error code registry | **No** | Errors are untyped strings |
| Scheduler / cron trigger | **No** | — |
| Webhook / event trigger | **No** | — |
| Audit log | **No** | — |
| Role-based access | **No** | — |
| Integrations menu (50+ connectors) | **No** | Manual ACTION node only |

---

## 6. Production Readiness Assessment

| Category | Score (0–10) | Notes |
|---|---|---|
| **Compiler correctness** | 9/10 | 17 golden snapshots, 52 tests passing, deterministic output; loses 1 point for missing LOOP/WAIT/ROUTER |
| **API completeness** | 7/10 | All core compile/execute/trace/cancel endpoints work; no auth, no pagination, no rate limiting |
| **Test coverage** | 7/10 | Compiler well-covered; execution_service and routing have lighter coverage; no integration tests |
| **Error handling** | 6/10 | Pydantic validation good; temporal errors surfaced; no structured error codes; no retry policy config in API |
| **Observability** | 5/10 | Temporal UI available; no structured logging to external system; no metrics endpoint; `replay_engine.py` partial |
| **Data persistence** | 3/10 | File-based only; no transactions; runtime directory gitignored (data lost on reset) |
| **Database** | 2/10 | Temporal SQLite dev only; no PostgreSQL; no migrations; no connection pooling |
| **Security** | 2/10 | No auth; no input sanitization beyond Pydantic; action URLs baked into DSL |
| **Frontend maintainability** | 5/10 | App.tsx 1074 LOC with hooks mixed in; types well-defined; CSS variables clean |
| **Deployment readiness** | 3/10 | No Dockerfile; no docker-compose for the stack; no healthcheck in start.sh; no env validation on startup |
| **Overall** | **5/10** | Excellent proof-of-concept / internal demo; not production-deployable without persistence, auth, and Temporal PostgreSQL |

---

## 7. Architecture Recommendation

### 7.1 Current Architecture

```
autox-flow-automate/
├── backend/
│   ├── app/             ← flat package: compiler + builders + schemas + services + agents + api + config
│   ├── runtime/         ← file-based DSL store (gitignored)
│   ├── scripts/
│   └── tests/
└── frontend/
    └── src/
        ├── components/  ← App.tsx + all UI components (App.tsx is 1074 LOC monolith)
        ├── services/    ← compilerApi.ts
        └── utils/
```

### 7.2 Recommended Architecture (refactor/backend-structure branch)

Move `app/` → `src/` and adopt the FastAPI production blueprint:

```
autox-flow-automate/backend/
├── src/
│   ├── compiler/        ← unchanged — isolated pipeline
│   ├── builders/        ← unchanged — isolated pipeline
│   ├── config/
│   │   ├── settings.py
│   │   ├── db_config.py        ← AsyncSession factory
│   │   └── lib_config.py       ← temporal client factory
│   ├── model/                  ← SQLAlchemy 2.0 async models
│   │   ├── workflow.py         ← Workflow, WorkflowVersion
│   │   ├── registration.py     ← WorkflowRegistration
│   │   └── run.py              ← WorkflowRun
│   ├── schema/                 ← Pydantic v2 request/response schemas (per-entity sub-packages)
│   ├── repo/                   ← DB access layer (AsyncSession)
│   ├── service/                ← ABCs for business logic
│   ├── service_impl/           ← Concrete implementations
│   ├── router/                 ← FastAPI routers (add_router pattern)
│   ├── dependency/             ← Depends() wiring (composition root)
│   ├── exception/              ← handlers + typed error codes
│   ├── security/               ← auth middleware (future)
│   ├── shared/                 ← shared types
│   └── utils/
├── migrations/                 ← Alembic; env.py + versions/
├── resources/                  ← logger.conf, static assets
└── tests/                      ← unchanged (compiler tests remain)
```

**Database models needed:**
- `Workflow` — id, workflow_id, name, created_at, updated_at
- `WorkflowVersion` — id, workflow_id (FK), version, dsl_json, content_hash, created_at
- `WorkflowRegistration` — id, workflow_id (FK), task_queue, registered_at, active
- `WorkflowRun` — id, workflow_id (FK), run_id, status, started_at, completed_at, input_json, trace_json

**Temporal migration:** Replace `temporal server start-dev` (SQLite) with `temporal server` using PostgreSQL config. Use `temporal-sql-tool` to create the Temporal schema in the `autox-flow-automate` database.

### 7.3 Frontend Recommendation

Extract hooks from App.tsx (1074 LOC) into dedicated hook files:
- `hooks/useUndoRedo.ts` — history stack
- `hooks/useExecutionPolling.ts` — polling loop
- `hooks/useWorkflowCanvas.ts` — node/edge state + ReactFlow callbacks
- Pure module-level helpers already extracted: `utils/localWorkflowStorage.ts`, `utils/exportWorkflow.ts`

---

## 8. Rebranding Impact Assessment

### 8.1 What Changed in refactor/flowautomate-rebrand

**Backend:**
- `APP_NAME`: `"Workflow Builder"` → `"FlowAutomate"`
- `APP_DESCRIPTION`: updated to AutoX reference
- `DEFAULT_TASK_QUEUE`: `"workflow-builder"` → `"flowautomate"`
- `compiler_settings.py` defaults: `workflow_type` + `task_queue` → `"flowautomate"`
- `test_contract.py` defaults updated to match
- OpenAPI schema examples updated
- `run.py` argparse description rebranded
- `start.sh` banner rebranded
- `README.md` rebranded

**Frontend:**
- `index.html` title: `"FlowAutomate · by AutoX"`
- Favicon slot: PLACEHOLDER comment for AutoX asset
- `Header.tsx`: brand logo slot with AutoX PLACEHOLDER, title `FlowAutomate`, subtitle `by AutoX · Visual Workflow Automation`
- `package.json` name: `flowautomate-frontend`
- localStorage key: `flowautomate-saved-workflows` (migration from `workflow-builder-saved-workflows`)
- `compilerApi.ts` defaults: `flowautomate`
- `App.tsx` blank metadata defaults: `flowautomate`
- `Simulator.tsx` greeting: updated to FlowAutomate
- `.env.example` updated

**Impact on existing data:**
- Runtime directory is gitignored — wiped and rebootstrapped (safe)
- Old localStorage key left as backup during migration
- Compiled DSL files with old `taskQueue: workflow-builder` are dropped on rebootstrap — users recompile

**Zero impact on:**
- Compiler logic — all 17 snapshots unchanged (fixtures specify `"default"`, not the default)
- API contracts — request/response shapes unchanged
- Zigflow DSL structure — only `taskQueue` field value changes for new compilations

### 8.2 Logo/Favicon Placeholder Locations

| Location | File | Comment |
|---|---|---|
| Browser tab favicon | `frontend/index.html:6` | `<!-- PLACEHOLDER: replace with FlowAutomate/AutoX favicon asset -->` |
| Header logo | `frontend/src/components/Header.tsx:54` | `{/* PLACEHOLDER: AutoX logo asset goes here */}` |

Replace the `<GitMerge>` icon in `Header.tsx:55` with an `<img>` tag pointing to the provided asset. Replace the `favicon.svg` link in `index.html:6` with the provided `.ico` or `.svg`.

---

## 9. Detailed Roadmap

### Phase 1 (Complete) — FlowAutomate v1 Stable
- Directory migration: `src/` → `autox-flow-automate/`
- Backend rebrand: FlowAutomate + flowautomate task queue
- Frontend rebrand: title, header, localStorage, API defaults
- Docs updated: CLAUDE.md, compiler.md, copilot-instructions.md

### Phase 2 — Backend Structure + PostgreSQL (`refactor/backend-structure`)
- `app/` → `src/` production blueprint layout
- SQLAlchemy 2.0 async: Workflow, WorkflowVersion, WorkflowRegistration, WorkflowRun
- Alembic migrations setup
- Temporal PostgreSQL persistence (temporal-sql-tool)
- DB: `autox-flow-automate`, user: `postgres`, host: `localhost:5432`

### Phase 3 — Loop + Wait Node Types (`feature/loop-support`)
- LOOP node: compiler DAG with back-edges OR Temporal `continue_as_new` pattern
- Wait-Timer node: Temporal `workflow.sleep()` wrapper
- Wait-Process Any/All: Temporal signal + asyncio.gather patterns
- Frontend node shapes for Loop and Wait
- Builder + schema + validation rules update

### Phase 4 — Router + Parallel Fan-out (`feature/router-parallel`)
- ROUTER node (N-branch, first-match + fan-out modes)
- Parallel execution: Temporal `asyncio.gather` over child workflows or activities
- Update graph traversal to support multi-outgoing edges for ROUTER
- Frontend node shapes

### Phase 5 — Process Call + Human Task (`feature/subflows`)
- PROCESS/FLOW-CALL node: invoke child workflow by ID
- HUMAN TASK node: pause + signal-driven external form
- Frontend: sub-workflow picker modal, human task form URL field

### Phase 6 — Listeners, Triggers, Integrations (`feature/triggers`)
- Scheduler trigger (Temporal schedules)
- Webhook / event trigger (FastAPI inbound webhook → signal)
- Connector node (3 modes: HTTP, Agent, Internal)
- Integrations catalog (seed 10+ HTTP-based connectors)

### Phase 7 — Enterprise (`feature/enterprise`)
- Auth middleware (JWT / API key)
- Vault / secrets management
- Typed error code registry
- Audit log
- Role-based access control
- Collaboration (workflow locking)

---

## 10. Recommended Next Sprint

**Branch:** `refactor/backend-structure`

**Goal:** Move from file-based, SQLite-backed demo infrastructure to a PostgreSQL-backed, production-structured FastAPI application.

**Sprint tasks (ordered):**

1. Rename `autox-flow-automate/backend/app/` → `autox-flow-automate/backend/src/` (pure move commit, identical to the `src/` → `autox-flow-automate/` move done in Phase 1)
2. Add `migrations/` at `autox-flow-automate/backend/` root — `alembic init migrations`, configure `env.py` for async SQLAlchemy
3. Add `resources/` at backend root — move `logger.conf` here
4. Inside `src/`, create: `config/db_config.py`, `model/` (4 models), `repo/` (4 repo classes), `service/` (ABCs), `service_impl/` (move existing service logic), `router/`, `dependency/`, `exception/`, `shared/`, `security/` (stub)
5. Create first Alembic migration: `create_workflow_tables`
6. Update `run.py` and `main.py` to use new package structure (`src.` prefix)
7. Run `temporal-sql-tool` to create Temporal PostgreSQL schema
8. Update `start.sh` to start `temporal server` (PostgreSQL mode) instead of `temporal server start-dev`
9. Update `app/config/settings.py` with `DATABASE_URL` (PostgreSQL DSN)
10. Verify all 52 tests still pass after structure move
11. Verify Golden Master DSL comparison still byte-identical (compiler is untouched)

**Definition of Done:**
- [ ] `pytest tests/ -q` → 52 passed, 0 failed
- [ ] `git diff tests/snapshots/` → empty
- [ ] `alembic upgrade head` creates 4 tables in `autox-flow-automate` database
- [ ] `temporal server` starts with PostgreSQL backend (no SQLite)
- [ ] Health check (`/api/v1/health/system`) returns all services green
- [ ] Compile → execute smoke test passes end-to-end on new structure
