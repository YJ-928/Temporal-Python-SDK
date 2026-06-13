# Temporal Python SDK + Zigflow — AI Agent Instructions

> **Purpose:** Repository orientation for AI agents. This file defines WHAT exists, WHERE it lives, and HOW to begin work. For deep technical reference, read the authoritative feature documents listed below — do not duplicate their content here.

---

## Repository Knowledge Sources

For any task in this repository, **read the corresponding feature document first.** These are the single source of truth for their respective domains.

| Domain | Document | When to Read |
|---|---|---|
| DSL Compiler / Visual Workflow Builder | [`.github/features/compiler.md`](.github/features/compiler.md) | Any work on `autox-flow-automate/backend/` — compiler, builders, schemas, services, API, registration, execution |
| Temporal Python SDK | [`.github/features/temporal.md`](.github/features/temporal.md) | Any work on Temporal workflows, activities, workers, signals, queries, updates |
| Zigflow YAML Workflows | [`.github/features/zigflow.md`](.github/features/zigflow.md) | Any work on Zigflow YAML files, DSL task types, runtime expressions, Zigflow CLI |

**Rule:** Never duplicate these documents here. Read them first. Make changes second. If this file and a feature doc disagree, the feature doc wins. If a feature doc and the source code disagree, the code wins.

---

## 1. Repository Identity

| Field | Value |
|---|---|
| **Name** | Temporal Python SDK + Zigflow |
| **Python** | ≥ 3.12 (managed via `uv` / `pyproject.toml`) |
| **Primary SDK** | `temporalio >= 1.24.0` |
| **Zigflow** | YAML declarative workflow engine on Temporal (CNCF Serverless Workflow DSL v1.0.0) |
| **Dev server** | `temporal server start-dev` — Web UI: `http://localhost:8233`, gRPC: `localhost:7233` |
| **Package manager** | `uv` (lockfile: `uv.lock`); `pip install -r requirements.txt` also works |
| **Virtual env** | `.venv/` — activate with `source .venv/bin/activate` |
| **Test runner** | `pytest` + `pytest-asyncio` |
| **Zigflow CLI** | `zigflow` — validate, run, and inspect YAML workflows |

---

## 2. Repository Map

```
.
├── demo/
│   └── temporal-poc-demo/              # ★ Main showcase POC — exercises every Temporal feature
│       ├── workflows.py                # TemporalShowcaseWorkflow (6 phases: counter, password,
│       │                               #   file processor, calculator, media, resilience)
│       ├── activities.py               # All activities
│       ├── child_workflows.py          # FileProcessingChildWorkflow + VideoProcessingChildWorkflow
│       ├── shared.py                   # Shared dataclasses (inputs, outputs, progress, results)
│       ├── worker.py                   # Worker registration
│       ├── starter.py                  # Workflow startup
│       └── clients.py                  # CLI driver (signals, queries, updates)
│
├── temporal-python-tutorial/           # 9 focused sub-tutorials, each self-contained
│   ├── activity-loop-until-output/
│   ├── child-workflows_and_continue_as_new/
│   ├── failing_activity_tutorial/
│   ├── learn_temporal_tutorial/
│   ├── long_running_workflow_calulator/
│   ├── mutiple_workflows_tutorial/
│   ├── parallel-file-processing-signals/
│   ├── query_signals_and_hearbeats_example/
│   └── signals_and_heartbeats/
│
├── temporal-python-learning/           # Structured 101/102 learning path
│   ├── docs/                           # 20 concept Markdown files (01–20)
│   ├── exercises/                      # 7 standalone exercise scripts
│   ├── notebooks/                      # Jupyter notebooks
│   ├── projects/                       # 3 runnable mini-projects
│   └── utils/                          # Shared helpers (client, retry policy, activity options)
│
├── temporal_101/                       # Official Temporal 101 course material
├── temporal_102/                       # Official Temporal 102 course material
│
├── zigflow/                            # ★ Zigflow YAML workflow examples
│   ├── Yaml/                           # Runnable YAML workflows
│   │   ├── hello_world.yaml
│   │   ├── http_call.yaml
│   │   ├── signal_driven_workflow.yaml
│   │   ├── parallel_task.yaml
│   │   ├── error_handling.yaml
│   │   ├── zigflow_temporal_heartbeat.yaml
│   │   ├── zigflow_temporal_signal.yaml
│   │   └── greet_user.yaml  (+ farewell_user variants, http_call_query_param, etc.)
│   └── Json/                           # JSON equivalents of the same workflows
│
├── src/
│   └── backend/                        # ★ Authoritative DSL Compiler + FastAPI backend
│       ├── app/
│       │   ├── compiler/               # Phase A: graph.py | Phase B: dsl_generator.py
│       │   │   ├── graph.py            # validate_graph(), traverse_graph(), compile_workflow()
│       │   │   ├── dsl_generator.py    # BUILDER_REGISTRY, register_builder(), generate_dsl()
│       │   │   ├── workflow_compiler.py # compile_workflow_to_dsl(), initialize_builders()
│       │   │   └── exceptions.py       # WorkflowValidationError → GraphValidationError
│       │   ├── builders/               # Node builders registered into BUILDER_REGISTRY
│       │   │   ├── __init__.py         # BUILDERS dict: START END INPUT OUTPUT ACTION AGENT IF
│       │   │   ├── input_builder.py    # build_input() → set + export.as
│       │   │   ├── output_builder.py   # build_output() → set (expose)
│       │   │   ├── action_builder.py   # build_action() → call: http + export.as
│       │   │   ├── agent_builder.py    # build_agent() → call: http (AgentRegistry lookup)
│       │   │   ├── if_builder.py       # build_if() → switch task
│       │   │   ├── condition_builder.py # build_condition_expression()
│       │   │   └── terminal_builder.py # build_terminal() → None (START/END emit nothing)
│       │   ├── schemas/
│       │   │   └── workflow_sch.py     # Pydantic v2 models: WorkflowDefinition, Node union, Edge
│       │   ├── services/
│       │   │   ├── compiler_service.py    # CompilerService: compile(), compile_and_save()
│       │   │   ├── registration_service.py # RegistrationService: register, hot-reload
│       │   │   ├── execution_service.py   # ExecutionService: execute, list, trace, cancel
│       │   │   └── storage_service.py     # Storage: save DSL, find by hash
│       │   ├── agents/
│       │   │   └── registry.py         # AgentRegistry: 4 agents (ports 11000–11003)
│       │   ├── api/
│       │   │   └── v1/                 # FastAPI route handlers
│       │   └── config/
│       │       ├── settings.py         # DEFAULT_TASK_QUEUE, TEMPORAL_ADDRESS, COMPILED_DIR
│       │       └── compiler_settings.py # workflow_type, task_queue, dsl_version defaults
│       ├── runtime/
│       │   ├── compiled/               # Compiled DSL JSON files (organized by workflow ID)
│       │   └── registrations.json      # Workflow registration registry
│       ├── scripts/
│       │   ├── start_runtime.sh        # Start Zigflow runtime daemon
│       │   └── stop_runtime.sh         # Stop Zigflow runtime daemon
│       └── tests/                      # Compiler test suite
│           ├── test_compiler.py        # Snapshot tests (compile fixture → compare stored snapshot)
│           ├── test_convergence.py     # 5 convergence scenarios
│           ├── test_validation.py      # 7 invalid fixture rejection tests
│           ├── test_builders.py        # Builder unit tests
│           ├── test_services.py        # Service integration tests
│           └── snapshots/              # Stored expected DSL output snapshots
│
├── poc-dsl-compiler/                   # Historical POC (reference only — NOT authoritative)
├── poc-react-flow/                     # V0 prototype (historical reference)
│
├── documents/                          # Reference documents (do NOT modify)
│   ├── Temporal_Capability_Reference.md
│   ├── Temporal_Checkpoints_Explanations.md
│   ├── Temporal_CLI_Cheatsheet.md
│   ├── Zigflow_DSL_Cheatsheet.md
│   ├── Zigflow_CLI_Cheatsheet.md
│   └── workflow_builder_architecture.md
│
├── docker-compose-postgres.yml         # Full local cluster with Postgres
├── docker-compose-mysql.yml            # Full local cluster with MySQL
├── start-temporal-dev.sh               # Installs Temporal CLI if missing, starts dev server
├── pyproject.toml / uv.lock / requirements.txt
└── .github/
    └── features/
        ├── compiler.md                 # ★ Authoritative compiler reference
        ├── temporal.md                 # ★ Authoritative Temporal SDK reference
        └── zigflow.md                  # ★ Authoritative Zigflow reference
```

---

## 3. Agent Startup Procedure

For any task in this repository, follow these steps in order:

**Step 1 — Identify task category:**

| If working on… | Read first |
|---|---|
| Compiler pipeline, builders, schemas, services, API, registration, execution | `.github/features/compiler.md` |
| Temporal workflows, activities, workers, signals, queries, updates, testing | `.github/features/temporal.md` |
| Zigflow YAML files, DSL task types, expressions, CLI | `.github/features/zigflow.md` |

**Step 2 — Read the corresponding feature document.**

**Step 3 — Inspect the actual implementation** in `autox-flow-automate/backend/` (compiler), `demo/temporal-poc-demo/`, `temporal-python-tutorial/`, or `zigflow/Yaml/` as relevant.

**Step 4 — Make changes.** Source code is the source of truth. If documentation and code disagree, code wins.

**Step 5 — If you changed the implementation, update the feature doc to match.** Feature documents must remain in sync with code.

---

## 4. How to Orient

| Task | Where to look |
|---|---|
| Add a Temporal workflow | `demo/temporal-poc-demo/workflows.py` — export `TASK_QUEUE`, register in `worker.py` |
| Add an activity | `demo/temporal-poc-demo/activities.py` — use `@activity.defn`, heartbeats for long tasks |
| Add a signal/query/update | `demo/temporal-poc-demo/workflows.py` — all three patterns in one class |
| Write a Temporal test | `temporal-python-learning/exercises/exercise_06_testing_workflow.py` |
| Work on the compiler | `autox-flow-automate/backend/app/compiler/` — read `.github/features/compiler.md` first |
| Add a new compiler node type | See Section 15 of `.github/features/compiler.md` for the complete checklist |
| Write a compiler test | `autox-flow-automate/backend/tests/` — snapshot tests in `test_compiler.py` |
| Write a Zigflow workflow | Copy from `zigflow/Yaml/` — read `.github/features/zigflow.md` for DSL reference |
| Debug a Zigflow workflow | `zigflow validate workflow.yaml`, then `zigflow run -f workflow.yaml --log-level debug` |
| Start everything locally | `./start-temporal-dev.sh`, then `cd autox-flow-automate/backend && uvicorn app.main:app --reload` |
| Understand parallel activities | `temporal-python-tutorial/parallel-file-processing-signals/` |
| Understand child workflows | `demo/temporal-poc-demo/child_workflows.py` |

---

## 5. Running Projects

### Demo — Temporal Showcase POC

The most complete Temporal example. `TemporalShowcaseWorkflow` exercises all 6 major feature areas.

```bash
# Terminal 1 — Start worker
python demo/temporal-poc-demo/worker.py

# Terminal 2 — Start workflow
python demo/temporal-poc-demo/starter.py --pin 742

# Terminal 3 — Drive workflow (signals, queries, updates)
python demo/temporal-poc-demo/clients.py <workflow_id> start --pin 742
python demo/temporal-poc-demo/clients.py <workflow_id> query_status
python demo/temporal-poc-demo/clients.py <workflow_id> stop_counter
```

Task queue: `"temporal-showcase-queue"`

### Zigflow Examples

```bash
# Terminal 1 — Start Temporal dev server
temporal server start-dev

# Terminal 2 — Start Zigflow worker
cd zigflow/Yaml
zigflow run -f hello_world.yaml

# Terminal 3 — Trigger the workflow
temporal workflow start \
  --type hello-world \
  --task-queue zigflow \
  --workflow-id hello-01 \
  --input '{}'
```

Available in `zigflow/Yaml/`: `hello_world.yaml`, `http_call.yaml`, `signal_driven_workflow.yaml`, `parallel_task.yaml`, `error_handling.yaml`, `zigflow_temporal_heartbeat.yaml`, `zigflow_temporal_signal.yaml`, `greet_user.yaml`, `farewell_user.yaml`, and variants.

### Backend Compiler API

```bash
cd autox-flow-automate/backend
uvicorn app.main:app --reload    # Runs at http://localhost:8000
```

---

## 6. Rules for Agents

1. **Read the feature document for the task domain before making any changes.** Do not rely on memory or inference for compiler, Temporal, or Zigflow behavior.
2. **Source code wins over documentation.** If `.github/features/compiler.md` and `autox-flow-automate/backend/` disagree, trust the code.
3. **`poc-dsl-compiler/` is historical.** The authoritative compiler is `autox-flow-automate/backend/`. Never use `poc-dsl-compiler/` as the basis for backend compiler changes.
4. **Do not modify files in `documents/`.** These are reference material.
5. **Do not invent compiler node types.** The backend supports exactly 7: `START`, `END`, `INPUT`, `OUTPUT`, `ACTION`, `AGENT`, `IF`. Full contracts in `.github/features/compiler.md` Section 9.
6. **Update documentation when you change implementation.** Feature docs must remain in sync with code.
7. **Do not duplicate feature doc content in this file.** This file is an orientation guide, not a knowledge base.

---

## 7. Coding Conventions

| Convention | Detail |
|---|---|
| Task queue constant | `TASK_QUEUE = "queue-name"` at module level, imported by worker and starter |
| Workflow ID | Business-meaningful string; often includes `uuid.uuid4().hex[:8]` suffix for uniqueness |
| Dataclasses | All I/O types in `shared.py` using `@dataclass`; never raw `dict` |
| Sandbox imports | Activity imports always inside `with workflow.unsafe.imports_passed_through():` |
| Entry point | `asyncio.run(main())` pattern universally |
| Non-retryable errors | `raise ApplicationError(..., non_retryable=True)` for business rule violations |
| Class-based activities | Used when activities need injected dependencies (DB, HTTP client) |
| Starter separate from worker | `starter.py` / `clients.py` always a separate file from `worker.py` |
