# Temporal Python SDK + Zigflow — Copilot Instructions

> **Purpose:** This file is the authoritative AI-agent context document for this repository. It describes every project, pattern, convention, and concept present in the codebase so any AI assistant can orient instantly and generate accurate, idiomatic **Temporal Python** code and **Zigflow YAML** workflows.
>
> **Scope (as of May 2026):** This repo now covers three workflow layers:
> - **Temporal Python SDK** — programmatic workflows in Python (existing content, sections 1–25)
> - **Zigflow** — declarative YAML-driven workflows on top of Temporal (sections 26–31)
> - **DSL Compiler** — visual workflow builder that compiles a graph JSON into Zigflow DSL (sections 32–38)

---

## 1. Repository Identity

| Field | Value |
|---|---|
| **Name** | Temporal Python SDK + Zigflow — Learning Repository |
| **Python** | ≥ 3.12 (managed via `uv` / `pyproject.toml`) |
| **Primary SDK** | `temporalio >= 1.24.0` |
| **Zigflow** | YAML declarative workflow engine built on Temporal (CNCF Serverless Workflow DSL v1.0.0) |
| **Dev server** | `temporal server start-dev` — Web UI at `http://localhost:8233`, gRPC at `localhost:7233` |
| **Package manager** | `uv` (lockfile: `uv.lock`); `pip install -r requirements.txt` also works |
| **Virtual env** | `.venv/` — activate with `source .venv/bin/activate` |
| **Test runner** | `pytest` + `pytest-asyncio` |
| **Zigflow CLI** | `zigflow` — validate, run, and inspect YAML workflows |

### Key non-Temporal dependencies
- `fastapi` + `uvicorn` — REST API layer in tutorial integrations
- `aiohttp` — async HTTP client inside Activities
- `flask` — used in some older tutorial endpoints

---

## 2. Repository Map

```
.
├── Demo/                          # ★ Main showcase POC — exercises every Temporal feature
├── Projects/
│   ├── temporal-banking-system/   # ★ Production-style banking workflow project
│   └── temporal-restaurant-management-system/  # (empty — placeholder)
├── Zigflow/                       # ★ Zigflow YAML workflow examples (Temporal + DSL layer)
│   ├── Examples/                  # Runnable YAML workflows (hello_world, http_call, signals, parallel, error handling)
│   └── Tutorials/                 # (placeholder for tutorial YAML files)
├── Tutorial/                      # 9 focused sub-tutorials, each self-contained
│   ├── activity-loop-until-output/
│   ├── child-workflows_and_continue_as_new/
│   ├── failing_activity_tutorial/
│   ├── learn_temporal_tutorial/
│   ├── long_running_workflow_calulator/
│   ├── mutiple_workflows_tutorial/
│   ├── parallel-file-processing-signals/
│   ├── query_signals_and_hearbeats_example/
│   └── signals_and_heartbeats/
├── temporal-python-learning/      # Structured 101/102 learning path
│   ├── docs/                      # 20 concept markdown files (01–20)
│   ├── exercises/                 # 7 standalone exercise scripts
│   ├── notebooks/                 # 6 Jupyter notebooks
│   ├── projects/                  # 3 runnable mini-projects
│   └── utils/                     # Shared helpers (client, retry policy, activity options)
├── poc-react-flow/                # ★ V0 prototype: ReactFlow graph → Zigflow DSL (agent-routing use case)
│   ├── node_conversion.py         # Builder functions for Zigflow DSL task blocks
│   ├── react_flow_to_temporal_json.py  # Core graph → do-list converter
│   ├── reactflow_to_zigflow.py    # Second-pass converter with typed dataclasses
│   └── bfs.py                     # BFS traversal utility
├── poc-dsl-compiler/              # ★ V1 compiler POC: generic graph JSON → Zigflow DSL
│   ├── docs/                      # Compiler design docs (01–05 + new compiler_*.md files)
│   └── examples/
│       ├── workflow_compiler.py   # Core compiler pipeline implementation
│       ├── workflow_generator.py  # Random workflow generator (fuzz testing)
│       ├── workflow_1_output.json # Sample input: simple hello-world workflow
│       └── workflow_2_output.json # Sample input: branching workflow
├── Documents/
│   ├── workflow_builder_architecture.md  # Full system architecture (three-tier, V2 vision)
│   ├── Zigflow_DSL_Cheatsheet.md  # DSL task-type reference
│   └── Zigflow_CLI_Cheatsheet.md  # Zigflow CLI commands
├── Resources/
│   ├── temporal_101/              # Official Temporal 101 course material (demos, exercises, samples)
│   └── temporal_102/              # Official Temporal 102 course material
├── TEMPORAL_CAPABILITY_REFERENCE.md  # Deep-dive: 17 capability categories with code examples
├── Temporal_Checkpoints_Explanations.md  # Same 17 categories — ELI5 + key notes format
├── README.md                      # Master README covering 101 + 102 (very detailed)
├── docker-compose-postgres.yml    # Full local cluster with Postgres
├── docker-compose-mysql.yml       # Full local cluster with MySQL
├── start-temporal-dev.sh          # Helper: installs Temporal CLI if missing, then starts dev server
└── .github/
    ├── copilot-instructions.md    # ← this file (AI agent context)
    └── docs/
        └── zigflow.md             # Full Zigflow knowledge base + DSL/CLI cheatsheets
```

---

## 3. Core Temporal Concepts (as used in this repo)

### 3.1 Workflow
- Decorated with `@workflow.defn` (class) and `@workflow.run` (entry method, must be `async`)
- Must be **deterministic** — no I/O, no `random`, no `datetime.now()`, no threading
- All side effects go through **Activities**
- Use `workflow.now()` for safe time access inside a Workflow
- Workflows can run for days, months, or years

```python
from temporalio import workflow
from datetime import timedelta

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            my_activity, name, start_to_close_timeout=timedelta(seconds=10)
        )
```

### 3.2 Activity
- Decorated with `@activity.defn`
- Does all real work: HTTP, DB, file I/O
- Automatically retried on failure (configurable via `RetryPolicy`)
- Use `activity.logger` for logging, `activity.heartbeat()` for progress on long tasks
- Can be function-based or class-based

```python
from temporalio import activity

@activity.defn
async def my_activity(name: str) -> str:
    activity.heartbeat("starting...")
    return f"Hello, {name}!"
```

**Class-based** (for dependency injection — DB sessions, HTTP clients):
```python
class MyActivities:
    def __init__(self, session):
        self.session = session

    @activity.defn
    async def fetch_data(self, url: str) -> str:
        async with self.session.get(url) as resp:
            return await resp.text()
```

### 3.3 Worker
- Connects to the Temporal Cluster and polls a Task Queue
- Runs your Workflow and Activity code
- Must register every Workflow and Activity it serves

```python
from temporalio.client import Client
from temporalio.worker import Worker

async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="my-queue",
        workflows=[MyWorkflow],
        activities=[my_activity],
    )
    await worker.run()
```

### 3.4 Task Queue
- Named channel routing work from Temporal Cluster → Workers
- Must **exactly match** (case-sensitive) between `Worker(...)` and `client.start_workflow(...)`
- Convention in this repo: define `TASK_QUEUE = "queue-name"` as a module-level constant

### 3.5 Client
- Used to start workflows, get handles, send signals/queries/updates
```python
client = await Client.connect("localhost:7233")
handle = await client.start_workflow(MyWorkflow.run, "arg", id="wf-id", task_queue="my-queue")
result = await handle.result()
# OR — start and wait in one call:
result = await client.execute_workflow(MyWorkflow.run, "arg", id="wf-id", task_queue="my-queue")
```

---

## 4. Signals, Queries, and Updates

All three are declared as methods on the Workflow class.

### Signals — fire-and-forget, no return value
```python
@workflow.signal
def pause(self) -> None:
    self._paused = True

@workflow.signal
def queue_file(self, file_id: int) -> None:
    self._file_queue.append(file_id)
```
Sending from external client:
```python
await handle.signal(MyWorkflow.pause)
await handle.signal(MyWorkflow.queue_file, 101)
```

### Queries — synchronous read of workflow state, no side effects
```python
@workflow.query
def get_status(self) -> WorkflowStatus:
    return WorkflowStatus(phase=self._phase, started=self._started, ...)
```
Reading from external client:
```python
result = await handle.query(MyWorkflow.get_status)
```

### Updates — synchronous request that can modify state AND return a value
```python
@workflow.update
async def run_calculator(self, input: CalculatorInput) -> str:
    result = await workflow.execute_activity(calculate, args=[input.a, input.b, input.op], ...)
    return result

@workflow.update_validator(run_calculator)
def validate_calculator(self, input: CalculatorInput) -> None:
    if input.op not in ("add", "subtract", "multiply", "divide"):
        raise ValueError(f"Unknown op: {input.op}")
```
Sending from external client (blocks until activity completes):
```python
result = await handle.execute_update(MyWorkflow.run_calculator, args=[CalculatorInput(a=9, b=3, op="divide")])
```

---

## 5. Retry Policies

Always set a `RetryPolicy` on Activities that call external services.

```python
from temporalio.common import RetryPolicy
from datetime import timedelta

RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,          # 1s → 2s → 4s → 8s …
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=5,               # total attempts including the first
)
```

**Default behavior (no explicit policy):** unlimited retries, exponential backoff (coefficient=2, cap=100× initial). Always set `maximum_attempts` for external service calls.

**Non-retryable errors:**
```python
from temporalio.exceptions import ApplicationError

raise ApplicationError("Invalid input: negative amount", non_retryable=True)
```
This stops retries immediately — the Activity and Workflow fail at once.

**Shared helper** (from `temporal-python-learning/utils/activity_helpers.py`):
```python
from utils.activity_helpers import default_retry_policy
policy = default_retry_policy(max_attempts=3, initial_interval_seconds=2)
```

---

## 6. Heartbeats

Long-running activities must call `activity.heartbeat()` periodically:
- Acts as a liveness signal to the Temporal Cluster
- Carries optional progress data (`activity.info().heartbeat_details`)
- On crash + retry, the next attempt can resume from the last heartbeat

```python
@activity.defn
async def process_file(file_id: int) -> str:
    for pct in range(10, 110, 10):
        await asyncio.sleep(0.5)
        activity.heartbeat(f"File {file_id}: {pct}%")
    return f"File {file_id} processed"
```

---

## 7. Timers

`await asyncio.sleep(seconds)` inside a Workflow creates a **durable timer** — tracked by the Temporal Cluster, not the Worker process. The Workflow survives Worker crashes during the wait.

```python
@workflow.run
async def run(self, input):
    result1 = await workflow.execute_activity(step_one, start_to_close_timeout=timedelta(seconds=5))
    await asyncio.sleep(10)   # durable — survives crash
    result2 = await workflow.execute_activity(step_two, start_to_close_timeout=timedelta(seconds=5))
```

---

## 8. Child Workflows

Spawn child workflows for independent execution context, separate retry scope, or parallel sub-processes.

```python
# Inside a parent workflow
child_handle = await workflow.start_child_workflow(
    FileProcessingChildWorkflow.run,
    id="child-file-123",
    task_queue=TASK_QUEUE,
)
result = await child_handle
```

Pattern in this repo: child workflows each wrap a single Activity for isolation:
```python
@workflow.defn
class FileProcessingChildWorkflow:
    @workflow.run
    async def run(self) -> str:
        return await workflow.execute_activity(
            process_file_media,
            start_to_close_timeout=timedelta(seconds=60),
            heartbeat_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
```

Parallel child workflows:
```python
file_handle = await workflow.start_child_workflow(FileProcessingChildWorkflow.run, ...)
video_handle = await workflow.start_child_workflow(VideoProcessingChildWorkflow.run, ...)
file_result, video_result = await asyncio.gather(file_handle, video_handle)
```

---

## 9. Parallel Activity Execution Inside a Workflow

Use `workflow.start_activity()` (non-blocking) instead of `workflow.execute_activity()` (blocking) to fire multiple activities concurrently. Signal handlers are the common trigger:

```python
@workflow.signal
def process_file_signal(self, file_id: int) -> None:
    handle = workflow.start_activity(
        process_file,
        file_id,
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=RetryPolicy(maximum_attempts=3),
    )
    self.tasks.append(handle)
```

---

## 10. Continue-As-New

For infinite loops approaching the ~50,000 event history limit:

```python
from temporalio.workflow import continue_as_new

@workflow.run
async def run(self, count: int) -> None:
    for _ in range(1000):
        count = await workflow.execute_activity(increment, count, ...)
    workflow.continue_as_new(count)  # fresh history, carries forward state
```

---

## 11. Workflow Sandbox — Import Pattern

Temporal runs Workflows in a determinism-enforcing sandbox. Import Activity modules using the pass-through context to avoid sandbox reload overhead:

```python
with workflow.unsafe.imports_passed_through():
    from activities import my_activity, MyActivityClass
    from child_workflows import MyChildWorkflow
```

Pure dataclass / shared-type modules (no I/O, no side effects) can be imported normally outside the `with` block.

---

## 12. Dataclass I/O Pattern

**Always use `@dataclass` for structured Workflow/Activity inputs and outputs.** Never use raw `dict`.

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class OrderInput:
    customer_name: str
    item: str
    quantity: int

@dataclass
class OrderResult:
    order_id: str
    status: str
    total: int
```

Temporal's default `DataConverter` serialises/deserialises dataclasses automatically. This provides type safety, IDE completion, and clean Web UI payload views.

---

## 13. Logging

| Location | Use |
|---|---|
| Inside Workflow | `workflow.logger.info(...)` — replay-safe, suppresses duplicate logs during replay |
| Inside Activity | `activity.logger.info(...)` |
| Worker bootstrap | `logging.basicConfig(level=logging.INFO)` in `main()` |

Never use `print()` or `logging.getLogger(...)` directly inside Workflow code — not replay-safe.

---

## 14. Activity Timeout Reference

| Timeout | Meaning |
|---|---|
| `start_to_close_timeout` | Max time from Activity start to completion — **always set this** |
| `schedule_to_close_timeout` | Max time from scheduling to completion (includes queue wait) |
| `schedule_to_start_timeout` | Max time waiting in the Task Queue |
| `heartbeat_timeout` | Max time between `activity.heartbeat()` calls — required for long activities |

---

## 15. execute_activity vs execute_activity_method

| Method | Use for |
|---|---|
| `workflow.execute_activity(fn, arg, ...)` | Standalone function-based activities |
| `workflow.execute_activity_method(Class.method, arg, ...)` | Class-based activity methods |
| `workflow.start_activity(fn, arg, ...)` | Non-blocking fire — returns handle, await later for parallel work |
| `workflow.start_activity_method(Class.method, arg, ...)` | Same but for class methods |

---

## 16. Testing

### Activity — isolated test
```python
import pytest
from temporalio.testing import ActivityEnvironment

@pytest.mark.asyncio
async def test_my_activity():
    env = ActivityEnvironment()
    result = await env.run(my_activity, "Alice")
    assert result == "Hello, Alice!"
```

### Workflow — end-to-end with time skipping
```python
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

@pytest.mark.asyncio
async def test_my_workflow():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue="test-q", workflows=[MyWorkflow], activities=[my_activity]):
            result = await env.client.execute_workflow(
                MyWorkflow.run, "Alice", id="test-wf", task_queue="test-q"
            )
    assert result == "Hello, Alice!"
```

`start_time_skipping()` fast-forwards all `asyncio.sleep()` timers instantly — tests that include 10-second timers still complete in milliseconds.

### Mocking Activities in Workflow tests
```python
@activity.defn(name="my_activity")   # must match the real activity name
async def my_activity_mock(name: str) -> str:
    return f"Mocked: {name}"

# Use my_activity_mock instead of my_activity when registering the Worker in tests
```

---

## 17. Durable Execution — How Replay Works

```
Event History (persisted in Temporal DB):
  WorkflowExecutionStarted
  ActivityTaskScheduled → step_one
  ActivityTaskCompleted → "result A"     ← on replay: injected from cache, NOT re-executed
  TimerStarted → 10s
  TimerFired                              ← on replay: skipped
  ActivityTaskScheduled → step_two       ← resumes here after Worker crash
  ActivityTaskCompleted → "result B"
  WorkflowExecutionCompleted
```

**Why Workflows must be deterministic:** Temporal replays Workflow code from history to reconstruct state. If the code produces a different sequence of commands on replay (e.g., different branch taken due to `random()`), Temporal raises a non-determinism error and the Workflow fails permanently.

---

## 18. Project Walkthroughs

### 18.1 Demo/ — Temporal Showcase POC

**The most complete example in the repo.** A single long-running `TemporalShowcaseWorkflow` that exercises every major Temporal feature in sequence.

**File layout:**
| File | Purpose |
|---|---|
| `workflows.py` | `TemporalShowcaseWorkflow` — 6 phases, all signals/queries/updates |
| `activities.py` | All activities consolidated from all Tutorial sub-projects |
| `child_workflows.py` | `FileProcessingChildWorkflow`, `VideoProcessingChildWorkflow` |
| `shared.py` | All dataclasses for inputs/outputs/progress/results |
| `worker.py` | Single worker registration for everything |
| `starter.py` | Starts the workflow, prints step-by-step driver commands |
| `clients.py` | CLI driver for every signal, query, and update |

**Task queue:** `"temporal-showcase-queue"`

**6 phases in order:**
1. **counter** — Increments until `stop_counter` signal
2. **password_cracker** — Brute-forces a 3-digit PIN; supports `override_pin` signal
3. **file_processor** — Processes files queued via `queue_file` signal in parallel
4. **calculator** — Runs random math ops until `advance_phase` signal
5. **media_processor** — Spawns `FileProcessingChildWorkflow` + `VideoProcessingChildWorkflow` in parallel
6. **resilience_test** — Randomly-failing activity demonstrating retry behavior

**Supported signals:** `start`, `pause`, `resume`, `stop`, `advance_phase`, `stop_counter`, `queue_file`, `override_pin`
**Supported queries:** `get_status`, `get_phase_progress`, `get_results`
**Supported updates:** `run_calculator`, `test_pin_match`

**How to run:**
```bash
# Terminal 1 — start worker
python Demo/worker.py

# Terminal 2 — start workflow
python Demo/starter.py --pin 742

# Terminal 3 — drive workflow step by step
python Demo/clients.py <workflow_id> start --pin 742
python Demo/clients.py <workflow_id> query_status
python Demo/clients.py <workflow_id> stop_counter
python Demo/clients.py <workflow_id> update_calc --a 9 --b 3 --op divide
```

---

### 18.2 Projects/temporal-banking-system/

**A production-style banking workflow.** A long-running `BankServerWorkflow` that acts as a stateful bank account server.

**File layout:**
```
workflows/banking_workflow.py       BankServerWorkflow
activities/deposit_money.py         credit_money activity
activities/withdraw_money.py        debit_money activity
workers/transaction_worker.py       Worker registration
starters/start_server.py            Starts the bank server workflow
external_clients/bank_admin.py      Interactive CLI (menu-driven)
external_clients/update_balance.py  Deposit/withdraw via updates
external_clients/freeze_account.py  Freeze signal
external_clients/query_balance.py   Balance query
external_clients/stop_server.py     Stop signal
```

**Task queue:** `"Banking-System"`
**Workflow ID:** `"banking-server-01"`

**Pattern:** The workflow loops forever (`while not self.stop_server`) sleeping 5s between cycles. All external interaction happens via:
- **Signals:** `freeze_account`, `unfreeze_account`, `stop_bank_server`
- **Queries:** `check_balance` (returns `float` or frozen error string)
- **Updates:** `add_money_to_account`, `remove_money_from_account` (both guard against frozen state)

**How to run:**
```bash
# Terminal 1
python Projects/temporal-banking-system/workers/transaction_worker.py

# Terminal 2 — start the bank server
python Projects/temporal-banking-system/starters/start_server.py

# Terminal 3 — interactive admin CLI
python Projects/temporal-banking-system/external_clients/bank_admin.py
```

---

### 18.3 Tutorial/ Sub-Projects

Each tutorial is a standalone Python package with `worker.py`, `workflow.py`/`workflows.py`, `activity.py`/`activities.py`, and a client/starter.

| Directory | Concept demonstrated | Key pattern |
|---|---|---|
| `activity-loop-until-output/` | Activity loop until condition met | `PasswordCrackingWorkflow` — loop of generate+validate; signal to stop; update to inject override |
| `child-workflows_and_continue_as_new/` | Child workflow pattern | `ParentWorkflow` spawning child workflows |
| `failing_activity_tutorial/` | Random activity failure + retries | `RandomFailWorkflow` — 70% failure rate, `RetryPolicy(maximum_attempts=5)` |
| `learn_temporal_tutorial/` | Core fundamentals | Clean structured tutorial split into activities/workers/workflows/starters |
| `long_running_workflow_calulator/` | Class-based activities | `LongRunningWorkflow` using `execute_activity_method` on `Calculator` class; cancel via signal |
| `mutiple_workflows_tutorial/` | Multiple workflows + FastAPI integration | `InfiniteRetryWorkflow` + `FiniteRetryWorkflow` calling a FastAPI service via `aiohttp` |
| `parallel-file-processing-signals/` | Parallel activity dispatch via signals | `FileProcessorWorkflow` — `workflow.start_activity()` in signal handler, keeps list of handles |
| `query_signals_and_hearbeats_example/` | Signals, queries, heartbeats together | `CounterWorkflow` with `get_current_count` query and `stop_counter_func` signal |
| `signals_and_heartbeats/` | Signal to break activity loop | `SignalWorkflow` — runs activity in a loop until `request_result` signal received |

---

### 18.4 temporal-python-learning/

**Structured learning path covering Temporal 101 and 102.**

**Docs** (`docs/`): 20 Markdown concept files numbered `01_` to `20_`:
- 01–12: Temporal 101 (overview, architecture, workflows, activities, workers, task queues, CLI, Web UI, retry policy, async vs sync, deployment, integration)
- 13–20: Temporal 102 (durable execution, logging, timers, testing, time-skipping, mocking, debugging, best practices)

**Exercises** (`exercises/`):
| File | Topic |
|---|---|
| `exercise_01_hello_workflow.py` | First workflow — `GreetSomeone` |
| `exercise_02_web_ui_observation.py` | Web UI exploration |
| `exercise_03_farewell_workflow.py` | Add an activity to a workflow |
| `exercise_04_finale_workflow.py` | Cross-language (Python workflow + Java activity) |
| `exercise_05_durable_execution.py` | Timer + crash recovery demo |
| `exercise_06_testing_workflow.py` | `ActivityEnvironment` + `WorkflowEnvironment` tests with `OrderWorkflow` |
| `exercise_07_debug_activity.py` | Debug a `PizzaOrderWorkflow` with a buggy `get_distance` Activity |

**Mini-projects** (`projects/`): `greeting_workflow_project/`, `translation_workflow_project/`, `pizza_order_debug_project/`

**Shared utils** (`utils/`):
- `temporal_client.py` → `get_client(host, namespace)` — reads `TEMPORAL_HOST` / `TEMPORAL_NAMESPACE` env vars
- `activity_helpers.py` → `default_retry_policy(...)`, `activity_options(...)`
- `workflow_helpers.py` — workflow convenience utilities

---

## 19. Coding Conventions in This Repo

| Convention | Detail |
|---|---|
| Task queue constant | `TASK_QUEUE = "queue-name"` at module level, imported by worker and starter |
| Workflow ID | Business-meaningful string; often includes `uuid.uuid4().hex[:8]` suffix for uniqueness |
| Dataclasses in shared.py | All I/O types in a dedicated `shared.py` (or `shared/`) module |
| Sandbox imports | Activity/child-workflow imports always inside `with workflow.unsafe.imports_passed_through():` |
| Class-based activities | Used when activities need injected dependencies (DB, HTTP session) |
| Function-based activities | Used for simple, stateless activities |
| External client scripts | Separate file(s) for external interaction (signals/queries/updates) — not mixed into worker |
| Starter separate from worker | `starter.py` / `client.py` / `starters/` always a separate file from `worker.py` |
| `asyncio.run(main())` | All entry points use `asyncio.run(main())` pattern |

---

## 20. Temporal CLI Cheatsheet

```bash
# Start local dev server (persists to file for crash-recovery demos)
temporal server start-dev
temporal server start-dev --ui-port 8080 --db-filename clusterdata.db

# Start a workflow
temporal workflow start \
  --type WorkflowClassName \
  --task-queue queue-name \
  --workflow-id my-workflow-01 \
  --input '"input_string"'

# Show event history
temporal workflow show --workflow-id my-workflow-01
temporal workflow show --workflow-id my-workflow-01 --detailed

# List workflows
temporal workflow list

# Cancel a running workflow
temporal workflow cancel --workflow-id my-workflow-01
```

---

## 21. Deployment Options

| Option | Description |
|---|---|
| `temporal server start-dev` | Local single-process (in-memory DB). No Docker. Default for dev. |
| `docker-compose-postgres.yml` | Full local cluster with Postgres. Use `TEMPORAL_VERSION` env var. |
| `docker-compose-mysql.yml` | Full local cluster with MySQL. |
| Kubernetes | Production self-hosted deployment. |
| **Temporal Cloud** | Fully managed SaaS. Workers still run on your infra. |

Docker compose: `temporal-ui` exposed on port `8080` (not `8233` as in dev server). The Temporal frontend is on `7233` in all cases.

---

## 22. Common Gotchas & Rules

1. **`await` on `execute_activity`** — forgetting `await` returns a coroutine, not the result. Causes `TypeError: coroutine is not JSON serializable`.
2. **Timeouts must be `timedelta`** — `start_to_close_timeout=10` raises a type error; must be `timedelta(seconds=10)`.
3. **Task queue name case-sensitive** — `"Banking-System"` ≠ `"banking-system"`.
4. **Non-determinism errors** — never use `random`, `datetime.now()`, `uuid.uuid4()`, or I/O directly in Workflow code. All non-deterministic calls go inside Activities.
5. **`workflow.logger` not `print()`** — standard logging and `print()` in Workflow code produce duplicate output on replay; use `workflow.logger`.
6. **Restart Worker after Workflow code changes** — Workflow code changes risk non-determinism for in-flight executions. Activity code changes are safe to hot-deploy.
7. **`non_retryable=True` for business errors** — always raise `ApplicationError(..., non_retryable=True)` for invalid input, constraint violations, and other deterministic failures.
8. **History limit ~50k events** — use `continue_as_new` for infinite loops in production.
9. **`with workflow.unsafe.imports_passed_through()`** — always use this block to import Activity modules inside Workflow files.
10. **Class-based activity registration** — pass an *instance* to `Worker(activities=[MyActivities(session)])`, not the class.

---

## 23. Key API Reference

```python
# Connect
client = await Client.connect("localhost:7233")
client = await Client.connect("localhost:7233", namespace="my-namespace")

# Start / execute workflow
handle = await client.start_workflow(Wf.run, arg, id="wf-id", task_queue="q")
result = await client.execute_workflow(Wf.run, arg, id="wf-id", task_queue="q")

# Get handle to existing workflow
handle = client.get_workflow_handle("wf-id")

# Interact
await handle.signal(Wf.my_signal, payload)
result = await handle.query(Wf.my_query)
result = await handle.execute_update(Wf.my_update, args=[payload])
result = await handle.result()

# Inside workflow — execute activity
result = await workflow.execute_activity(fn, arg, start_to_close_timeout=timedelta(seconds=10))
result = await workflow.execute_activity_method(Cls.method, arg, start_to_close_timeout=timedelta(seconds=10))

# Inside workflow — non-blocking activity
handle = workflow.start_activity(fn, arg, start_to_close_timeout=timedelta(seconds=10))
result = await handle  # await whenever needed

# Inside workflow — child workflow
child = await workflow.start_child_workflow(ChildWf.run, id="child-id", task_queue="q")
result = await child

# Inside workflow — safe timer
await asyncio.sleep(seconds)  # durable, cluster-tracked

# Inside workflow — continue-as-new
workflow.continue_as_new(new_arg)

# Inside activity — heartbeat
activity.heartbeat("progress message")
activity.info().attempt  # current attempt number
```

---

## 24. Environment Variables

```bash
TEMPORAL_HOST=localhost:7233          # used by utils/temporal_client.py
TEMPORAL_NAMESPACE=default            # used by utils/temporal_client.py
TEMPORAL_VERSION=1.x.x               # used by docker-compose files
TEMPORAL_ADMINTOOLS_VERSION=1.x.x    # used by docker-compose files
TEMPORAL_UI_VERSION=x.x.x            # used by docker-compose files
```

`.env.example` is in `temporal-python-learning/`.

---

## 25. How to Orient When Asked About This Repo

- **"Add a new workflow"** → Follow the pattern in `Demo/workflows.py` or `Projects/temporal-banking-system/workflows/banking_workflow.py`. Place in `workflows/` directory, export `TASK_QUEUE`, register in `worker.py`.
- **"Add a new activity"** → Follow `Demo/activities.py` or any `Tutorial/*/activities.py`. Use `@activity.defn`, add heartbeats for long tasks, raise `ApplicationError(..., non_retryable=True)` for business errors.
- **"Add a signal/query/update"** → See `Demo/workflows.py` for all three patterns in one class.
- **"Write a test"** → See `temporal-python-learning/exercises/exercise_06_testing_workflow.py` for `ActivityEnvironment` + `WorkflowEnvironment` patterns.
- **"Start everything locally"** → Run `./start-temporal-dev.sh`, then `python <project>/workers/<worker>.py`, then `python <project>/starters/<starter>.py`.
- **"Parallel activities"** → See `Tutorial/parallel-file-processing-signals/workflows.py` for the `workflow.start_activity()` + signal handler pattern.
- **"Child workflows"** → See `Demo/child_workflows.py` and the `media_processor` phase in `Demo/workflows.py`.
- **"Retry config"** → Use `RetryPolicy` from `temporalio.common`; see `temporal-python-learning/utils/activity_helpers.py` for the shared helper.
- **"Write a Zigflow workflow"** → See `Zigflow/Examples/` for runnable YAML patterns. Follow the `document` + `do` structure. See section 26–31 below and `.github/docs/zigflow.md` for the full reference.
- **"Add a signal to a Zigflow workflow"** → Use a `listen` task with `to.one.with.id: <signal-name>`. Send via `temporal workflow signal --name <signal-name>`.
- **"Handle errors in Zigflow"** → Wrap tasks in `try`/`catch` with a `retry` block. Use `raise` to fault deliberately.
- **"Run parallel tasks in Zigflow"** → Use `fork` task with `compete: false` (all results) or `compete: true` (first wins).
- **"Debug a Zigflow workflow"** → Run `zigflow validate workflow.yaml`, then `zigflow run -f workflow.yaml --log-level debug`, then inspect with `temporal workflow show --workflow-id <id>`.

---

## 26. Zigflow — What It Is

**Zigflow is a declarative workflow engine** that sits on top of Temporal. Instead of writing Python classes, you describe the workflow in a YAML file using the [CNCF Serverless Workflow DSL v1.0.0](https://github.com/serverlessworkflow/specification).

```
YAML → Validation → Compilation → Temporal Workflow → Execution
```

| Component | Role |
|---|---|
| YAML file | Single source of truth for workflow behavior |
| Zigflow Worker | Compiles YAML → Temporal workflow; polls the Task Queue |
| Temporal Server | Orchestrates scheduling, retries, history, timers |
| Temporal CLI | Triggers workflow execution and sends signals |

**Key rule:** Zigflow does NOT self-trigger workflows. After `zigflow run -f workflow.yaml` starts the worker, you trigger execution with `temporal workflow start`.

### Zigflow vs Python SDK — When to Use Which

| Use Zigflow YAML when… | Use Python SDK when… |
|---|---|
| Workflow is mostly orchestration (call → wait → call) | Workflow has complex business logic in Python |
| Team prefers declarative config | You need type-safe dataclasses and IDE completion |
| Rapid prototyping of integration flows | You need fine-grained control over retry/heartbeat |
| Non-Python teams need to read/write workflows | Activities use Python libraries heavily |

---

## 27. Zigflow DSL Structure

Every Zigflow workflow file has two required top-level keys:

```yaml
document:
  dsl: "1.0.0"           # always "1.0.0"
  taskQueue: my-queue    # must match the Zigflow worker's task queue (case-sensitive)
  workflowType: my-wf    # must match the Temporal workflow type (case-sensitive)
  version: "1.0.0"       # your workflow's semantic version
  metadata:              # optional: activityOptions, custom tags
    activityOptions:
      startToCloseTimeout:
        minutes: 5

do:                      # ordered list of named tasks
  - taskName:
      <task-definition>
```

### `document` field reference

| Field | Required | Notes |
|---|---|---|
| `dsl` | yes | Always `"1.0.0"` |
| `taskQueue` | yes | Temporal Task Queue — must match `zigflow run` configuration |
| `workflowType` | yes | Temporal Workflow Type registered by Zigflow worker |
| `version` | yes | Semantic version of the workflow definition |
| `metadata.activityOptions` | no | Default timeouts for all `call`/`run` tasks |

### Reusable components (`use`)

Define retry policies, authentication, and functions once:

```yaml
use:
  retries:
    standardRetry:
      delay:
        seconds: 2
      backoff:
        exponential: {}
      limit:
        attempt:
          count: 3
  authentications:
    myAuth:
      bearer:
        token: ${ $env.API_TOKEN }
```

---

## 28. Zigflow Task Types Quick Reference

| Task | What it does | Key property |
|---|---|---|
| `set` | Assign variables in workflow data | `set: {key: value}` |
| `call` | Invoke HTTP/OpenAPI/gRPC/AsyncAPI | `call: http`, `with: {method, endpoint}` |
| `do` | Run subtasks sequentially as a group | `do: [list of tasks]` |
| `fork` | Run branches in parallel | `fork: {compete: bool, branches: [...]}` |
| `for` | Loop over a collection | `for: {each, in, at}`, `do: [...]` |
| `listen` | Wait for an external event/signal | `listen: {to: {one/any/all: {with: {id, type}}}}` |
| `raise` | Throw an error to fault the workflow | `raise: {error: {type, status, title}}` |
| `run` | Execute container/shell/script/sub-workflow | `run: {container/shell/script/workflow}` |
| `switch` | Conditional branching | `switch: [{case: {when, then}}]` |
| `try` | Error handling with optional retry | `try: [tasks]`, `catch: {retry, do}` |
| `wait` | Pause for a duration (durable timer) | `wait: {seconds/minutes/hours}` |

### Task execution model

| Task type | Runs as | Deterministic? |
|---|---|---|
| `set`, `switch` | Temporal Workflow code | Must be deterministic |
| `call`, `run` | Temporal Activity | Can do I/O; retried on failure |
| `wait` | Temporal Timer | Durable — survives Worker crash |
| `listen` | Temporal Signal handler | Durable — survives Worker crash |
| `fork` | Workflow code + parallel Activities | Branches run concurrently |

---

## 29. Zigflow Examples in This Repo

All runnable examples are in `Zigflow/Examples/`:

| File | Task Queue | Workflow Type | Demonstrates |
|---|---|---|---|
| `hello_world.yaml` | `zigflow` | `hello-world` | Minimal `set` + `output` pattern |
| `http_call.yaml` | `zigflow-http` | `fetch-user` | `call: http` with `output.as` |
| `signal_driven_workflow.yaml` | `zigflow-signals` | `signal` | `listen` task + `wait` timer |
| `parallel_task.yaml` | `zigflow-parallel-tasks` | `competing-tasks` | `fork` with `compete: true` (race) |
| `error_handling.yaml` | `zigflow-error-handle` | `try-catch` | `try`/`catch` with fallback `set` |

### Running any example

```bash
# Terminal 1 — start Temporal dev server (if not already running)
temporal server start-dev

# Terminal 2 — start Zigflow worker for the example
cd Zigflow/Examples
zigflow run -f <example>.yaml

# Terminal 3 — trigger the workflow
temporal workflow start \
  --type <workflowType> \
  --task-queue <taskQueue> \
  --workflow-id my-run-01 \
  --input '{}'

# For signal_driven_workflow.yaml — send signal after starting
temporal workflow signal \
  --workflow-id my-run-01 \
  --name approve \
  --input '{"approved": true}'
```

---

## 30. Zigflow Runtime Expressions

Expressions use jq syntax wrapped in `${ }`:

```yaml
userId: ${ $input.userId }           # workflow input
userName: ${ $data.fetchUser.name }  # previous task output (by task name)
allIds: ${ $context.ids }            # accumulated context state
requestId: ${ uuid }                 # replay-safe UUID generation
createdAt: ${ timestamp }            # replay-safe timestamp
active: ${ .users | map(select(.active)) }  # jq filter
```

### Built-in variables

| Variable | Contains |
|---|---|
| `$input` | Raw input passed when the workflow was started |
| `$context` | Accumulated workflow state (from `export.as`) |
| `$data` | Output from the previous task |
| `$env` | Environment variables |

### `output` vs `export`

```yaml
- fetchUser:
    call: http
    with:
      method: get
      endpoint: https://api.example.com/users/1
    output:
      as:
        user: ${ . }                          # shapes what flows to next task
    export:
      as: "${ $context + {fetchedUser: .} }"  # persists into $context for later tasks
```

**Rule:** Always use `$context + {...}` merge syntax in `export.as` to avoid overwriting existing context.

---

## 31. Zigflow Common Mistakes & Rules

1. **Task Queue / Workflow Type are case-sensitive** — `zigflow-HTTP` ≠ `zigflow-http`. Must match exactly between YAML and Worker.
2. **`set` must be deterministic** — never use `$env.RANDOM`, Python's `random`, or current wall-clock time. Use `${ uuid }` and `${ timestamp }`.
3. **Every task needs a name** — the task name is the key under `do`. Missing it causes a YAML parse error.
4. **Zigflow doesn't self-trigger** — always trigger with `temporal workflow start` after the worker is running.
5. **Signal name must match `listen.to.one.with.id`** exactly — `temporal workflow signal --name approve` must match `id: approve` in YAML.
6. **`fork compete: false` returns an array** — both branch results are wrapped in an array. Don't expect a single value.
7. **`export.as` must merge, not replace** — use `${ $context + {key: .} }`, not `${ . }`, or you'll lose all previous context.
8. **Validate before running** — always run `zigflow validate workflow.yaml` first; it catches schema errors before Temporal sees them.
9. **`metadata.activityOptions` sets defaults for all tasks** — override per-task with a task-level `metadata.timeout`.
10. **`workflowType` in YAML is the Temporal Workflow Type** — it appears as `workflowType` in `temporal workflow list` output.

---

## 32. DSL Compiler — Initiative Overview

**Status:** POC (proof of concept) — active development.

The DSL Compiler initiative builds a **Visual Workflow → Zigflow DSL compiler**. It is a layer that sits between a UI workflow builder and the Zigflow runtime. Temporal is the orchestration runtime only; the compiler does not generate Temporal Python code.

```
UI Workflow Builder
        ↓
  JSON Workflow Definition
        ↓
      Compiler
        ↓
  Zigflow DSL (JSON / YAML)
        ↓
  Executed by Zigflow + Temporal
```

**What the compiler is NOT:**
- Not a Temporal workflow generator.
- Not a Zigflow worker.
- Not a runtime execution engine.

**Backend (planned):** Python + FastAPI.

**Key documents:**
| File | Purpose |
|---|---|
| `poc-dsl-compiler/docs/compiler_context.md` | Full architecture explanation |
| `poc-dsl-compiler/docs/compiler_pipeline.md` | Frozen pipeline stages with function signatures |
| `poc-dsl-compiler/docs/workflow_json_contract.md` | Frozen input JSON contract |
| `poc-dsl-compiler/docs/compiler_progress.md` | Completed / current / next steps |
| `poc-dsl-compiler/docs/testing_strategy.md` | Workflow generator and fuzz-testing approach |
| `Documents/workflow_builder_architecture.md` | Full three-tier system architecture (V2 vision) |

---

## 33. DSL Compiler — Architecture Pipeline

The compiler transforms a Workflow JSON into Zigflow DSL through a sequential pipeline of pure functions. No classes. No templates (yet). No registry (yet). The compiler is stateless.

```
Workflow JSON  ({nodes, edges})
        │
        ▼
  generate_node_map()          →  node_id → node dict
        │
        ▼
  generate_adjacency_list()    →  source_id → [target_id, ...]
        │
        ▼
  find_entrypoint()            →  ID of the START node
        │
        ▼
  generate_graph_structure()   →  Recursive DAG; shared nodes appear once
        │
        ▼
  print_graph()                →  Debug visualisation (DFS preorder)
        │
        ▼
  traverse_graph()             →  Ordered list of nodes (DFS preorder)
        │
        ▼
  DSL Builder                  →  Zigflow DSL dict / YAML string
```

**Implementation file:** `poc-dsl-compiler/examples/workflow_compiler.py`

**Critical rules:**
- Do NOT iterate the raw node array to determine execution order. Use graph traversal only.
- Shared nodes (nodes with multiple incoming edges in a DAG) must not be duplicated in traversal.
- Traversal order is DFS preorder.
- Builder functions are pure — no side effects, no global state.

---

## 34. DSL Compiler — Frozen V1 Node Types

These are the only node types implemented in V1. Do not add others without updating this file.

| Node Type | DSL Output | Notes |
|---|---|---|
| `START` | None | Graph traversal entry point; emits no DSL task |
| `END` | None | Graph traversal terminal; emits no DSL task |
| `INPUT` | `set` task | Captures external input fields into named workflow variables |
| `ACTION` | Activity call task | Transforms runtime variables; models a computation step |
| `OUTPUT` | `set` task (expose) | Exposes named workflow variables as workflow output |

**NOT implemented in V1** (deferred): `IF`, `WAIT`, `VARIABLE`, `WORKFLOW`, `PARALLEL`.

### Node Data Contracts

**INPUT node:**
```json
{
  "type": "INPUT",
  "data": {
    "inputs": [
      { "field": "name", "store_as": "user_name", "type": "string" }
    ]
  }
}
```

**ACTION node:**
```json
{
  "type": "ACTION",
  "data": {
    "operation": "greet",
    "inputs": { "name": "user_name" },
    "output": "message"
  }
}
```

**OUTPUT node:**
```json
{
  "type": "OUTPUT",
  "data": {
    "outputs": [
      { "field": "message", "type": "string" }
    ]
  }
}
```

---

## 35. DSL Compiler — Input JSON Contract (Frozen)

```json
{
  "nodes": [
    { "id": "N1", "type": "START" },
    { "id": "N2", "type": "INPUT", "data": { ... } },
    { "id": "N3", "type": "ACTION", "data": { ... } },
    { "id": "N4", "type": "OUTPUT", "data": { ... } },
    { "id": "N5", "type": "END" }
  ],
  "edges": [
    { "id": "E1", "source": "N1", "target": "N2" },
    { "id": "E2", "source": "N2", "target": "N3" },
    { "id": "E3", "source": "N3", "target": "N4" },
    { "id": "E4", "source": "N4", "target": "N5" }
  ]
}
```

**Invariants:**
- `nodes` and `edges` are the only top-level keys required.
- Every edge has exactly `{id, source, target}`. Edges carry no business data.
- Node IDs must be unique across the graph.
- Edge source and target must reference valid node IDs.
- The graph must have exactly one `START` node and one `END` node.

**Sample inputs:** `poc-dsl-compiler/examples/workflow_1_output.json`, `workflow_2_output.json`

---

## 36. DSL Compiler — Workflow Generator

**File:** `poc-dsl-compiler/examples/workflow_generator.py`

The workflow generator produces random Workflow JSON documents for fuzz-testing the compiler pipeline.

**How to run:**
```bash
cd poc-dsl-compiler/examples
python workflow_generator.py
# Prompts: Total Nodes, Branches
# Output: generated/workflow.json + generated/workflow.md (Mermaid diagram)
```

**What it generates:**
- A `START` node → one shared `INPUT` node → N branches of random `INPUT`/`ACTION`/`OUTPUT` nodes → an `END` node
- All `OUTPUT` nodes are wired directly to `END`
- A Mermaid diagram is saved alongside the JSON for visual inspection

**Supported node types in generator:** `INPUT`, `ACTION`, `OUTPUT` (the full V1 set, minus `START`/`END` which are always auto-generated).

---

## 37. DSL Compiler — How to Orient When Asked About the Compiler

- **"Add a new node type to the compiler"** → First update `poc-dsl-compiler/docs/workflow_json_contract.md` and `compiler_context.md` to document the contract. Then add a builder function in `workflow_compiler.py`. Do not add node types that are in the NOT IMPLEMENTING list.
- **"What nodes are supported?"** → V1 frozen set: `START`, `END`, `INPUT`, `ACTION`, `OUTPUT`. See section 34.
- **"What does an edge look like?"** → Always `{id, source, target}` only. No business logic in edges.
- **"How does traversal work?"** → DFS preorder from the `START` node. Do not iterate the raw node array. See `traverse_graph()` in `workflow_compiler.py`.
- **"Where is the compiler code?"** → `poc-dsl-compiler/examples/workflow_compiler.py`
- **"Where is the V0 prototype?"** → `poc-react-flow/` — agent-routing specific, not generic. Key reference: `poc-react-flow/node_conversion.py` for builder function patterns.
- **"Generate a test workflow"** → `python poc-dsl-compiler/examples/workflow_generator.py`
- **"What is the three-tier architecture?"** → See `Documents/workflow_builder_architecture.md`. Tier 1 = UI (V2), Tier 2 = Compiler + API (V1), Tier 3 = Zigflow + Temporal execution.

---

## 38. DSL Compiler — What NOT to Do

1. **Do not add Temporal Python Workflow code for the compiler output.** The compiler generates Zigflow DSL only.
2. **Do not put business logic in edges.** Edges are `{id, source, target}` only.
3. **Do not iterate the node array for execution order.** Always use graph traversal.
4. **Do not duplicate shared nodes** in the traversal output. The graph structure handles them with a `visited` set.
5. **Do not use classes** in the compiler functions. All functions are module-level and pure.
6. **Do not add templates or a registry** until the V1 pure-function approach is validated end-to-end.
7. **Do not implement** `IF`, `WAIT`, `VARIABLE`, `WORKFLOW`, or `PARALLEL` nodes in V1.
