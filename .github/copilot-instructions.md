# Temporal Python SDK — Copilot Instructions

> **Purpose:** This file is the authoritative AI-agent context document for this repository. It describes every project, pattern, convention, and concept present in the codebase so any AI assistant can orient instantly and generate accurate, idiomatic Temporal Python code.

---

## 1. Repository Identity

| Field | Value |
|---|---|
| **Name** | Temporal Python SDK — Learning Repository |
| **Python** | ≥ 3.12 (managed via `uv` / `pyproject.toml`) |
| **Primary SDK** | `temporalio >= 1.24.0` |
| **Dev server** | `temporal server start-dev` — Web UI at `http://localhost:8233`, gRPC at `localhost:7233` |
| **Package manager** | `uv` (lockfile: `uv.lock`); `pip install -r requirements.txt` also works |
| **Virtual env** | `.venv/` — activate with `source .venv/bin/activate` |
| **Test runner** | `pytest` + `pytest-asyncio` |

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
├── Resources/
│   ├── temporal_101/              # Official Temporal 101 course material (demos, exercises, samples)
│   └── temporal_102/              # Official Temporal 102 course material
├── TEMPORAL_CAPABILITY_REFERENCE.md  # Deep-dive: 17 capability categories with code examples
├── Temporal_Checkpoints_Explanations.md  # Same 17 categories — ELI5 + key notes format
├── README.md                      # Master README covering 101 + 102 (very detailed)
├── docker-compose-postgres.yml    # Full local cluster with Postgres
├── docker-compose-mysql.yml       # Full local cluster with MySQL
└── start-temporal-dev.sh          # Helper: installs Temporal CLI if missing, then starts dev server
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
