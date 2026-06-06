# Temporal Python SDK — Complete Developer Handbook

> **Purpose:** Authoritative reference for building durable, fault-tolerant workflows using Temporal Python SDK.
> **Scope:** Temporal fundamentals, architecture, core API, patterns, testing, deployment, and repository-specific usage.
> **Audience:** Developers building workflows in Python using the `temporalio >= 1.24.0` SDK.

---

## Table of Contents

1. [What Is Temporal](#1-what-is-temporal)
2. [Core Concepts](#2-core-concepts)
3. [Workflows — Deterministic Orchestration](#3-workflows--deterministic-orchestration)
4. [Activities — Reliable Work Execution](#4-activities--reliable-work-execution)
5. [Workers — Execution Engine](#5-workers--execution-engine)
6. [Task Queues — Work Routing](#6-task-queues--work-routing)
7. [Signals, Queries, and Updates](#7-signals-queries-and-updates)
8. [Retry Policies and Failure Handling](#8-retry-policies-and-failure-handling)
9. [Heartbeats and Long-Running Activities](#9-heartbeats-and-long-running-activities)
10. [Durable Timers](#10-durable-timers)
11. [Child Workflows](#11-child-workflows)
12. [Parallel Activity Execution](#12-parallel-activity-execution)
13. [Continue-As-New for Infinite Loops](#13-continue-as-new-for-infinite-loops)
14. [Sandbox and Import Patterns](#14-sandbox-and-import-patterns)
15. [Dataclass I/O Pattern](#15-dataclass-io-pattern)
16. [Logging](#16-logging)
17. [Activity Timeouts](#17-activity-timeouts)
18. [Activity Execution Methods](#18-activity-execution-methods)
19. [Testing Workflows and Activities](#19-testing-workflows-and-activities)
20. [Durable Execution and Replay](#20-durable-execution-and-replay)
21. [Temporal CLI](#21-temporal-cli)
22. [Deployment Options](#22-deployment-options)
23. [Key API Reference](#23-key-api-reference)
24. [Environment Variables](#24-environment-variables)
25. [Common Pitfalls](#25-common-pitfalls)
26. [Best Practices](#26-best-practices)
27. [Repository Examples](#27-repository-examples)
28. [Coding Conventions](#28-coding-conventions)

---

## 1. What Is Temporal

**Temporal is a durable execution platform** that ensures code runs to completion, even in the presence of failures such as network outages, server crashes, or bugs.

Traditional applications lose state when a process crashes. Temporal solves this by persisting every step of execution as an **event history**. If a failure occurs, Temporal automatically replays the history to restore the exact state before the failure.

**Key value proposition:** You write plain Python functions that run reliably for days, weeks, or months without manual retry loops, state persistence code, or distributed transaction management.

### Core Insight

```
Without Temporal: Write code → Handle retries → Persist state → Manage recovery
With Temporal: Write code → Temporal handles everything else
```

---

## 2. Core Concepts

| Concept | Role | Persistence |
|---------|------|-------------|
| **Workflow** | Durable orchestration logic (state machine) | Event history in Temporal Cluster |
| **Activity** | Non-deterministic work (API calls, DB writes) | Results cached in history |
| **Worker** | Process that executes workflows and activities | Polls Temporal Cluster for work |
| **Task Queue** | Named channel routing work from Cluster → Workers | Cluster-side queue |
| **Namespace** | Multi-tenant isolation boundary | Cluster configuration |
| **Temporal Cluster** | Central server orchestrating execution | Persists history, manages schedules |

---

## 3. Workflows — Deterministic Orchestration

### Definition

A Workflow is a durable function that orchestrates one or more activities. It must be **deterministic** — all non-deterministic behavior delegated to activities.

### Syntax

```python
from temporalio import workflow
from datetime import timedelta

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            my_activity,
            name,
            start_to_close_timeout=timedelta(seconds=10)
        )
```

### Requirements

| Requirement | Why |
|---|---|
| `@workflow.defn` class decorator | Registers the workflow with Temporal |
| `@workflow.run` async method | Workflow entry point; must be `async` |
| Deterministic code only | Temporal replays from history; non-determinism breaks replay |
| Use `workflow.execute_activity()` for side effects | All I/O, external calls go through activities |
| Use `workflow.now()` for time | Not `datetime.now()`; must respect replay semantics |
| Long-running capable | Workflows can run for days, months, or years |

### What Workflows Can Do

✅ Orchestrate activities in sequence or parallel
✅ Branch on activity results (if/else logic)
✅ Loop over activity results
✅ Handle signals and queries from external clients
✅ Sleep durably (survives crashes)
✅ Spawn child workflows
✅ Execute multiple activities in parallel
✅ Continue-as-new to reset history

### What Workflows Cannot Do

❌ Make HTTP calls directly
❌ Write to databases directly
❌ Use `random`, `datetime.now()`, `uuid.uuid4()` directly
❌ Use threading or async libraries (except `asyncio.sleep`)
❌ Import modules with I/O side effects (except in `unsafe.imports_passed_through()`)
❌ Catch Temporal-internal exceptions (non-determinism, timeouts)

---

## 4. Activities — Reliable Work Execution

### Definition

An Activity is a function that performs real work. Activities are **automatically retried** on failure (configurable via `RetryPolicy`). All side effects go here.

### Function-Based Activity

```python
from temporalio import activity

@activity.defn
async def my_activity(name: str) -> str:
    activity.heartbeat("starting...")
    result = await call_external_api(name)
    return result
```

### Class-Based Activity (Dependency Injection)

```python
class MyActivities:
    def __init__(self, db_session, http_client):
        self.db = db_session
        self.http = http_client

    @activity.defn
    async def fetch_user(self, user_id: int) -> User:
        return await self.db.query_user(user_id)

# Register as instance, not class
worker = Worker(
    client,
    task_queue="my-queue",
    activities=[MyActivities(db_session, http_client)]
)
```

### Properties

| Property | Detail |
|---|---|
| Automatically retried | On failure, Temporal retries per `RetryPolicy` |
| Use `activity.logger` | For logging inside activities |
| Use `activity.heartbeat()` | To signal progress on long tasks |
| Can be async or sync | Both `async def` and `def` supported |
| Can access `activity.info()` | Current attempt number, retry state, heartbeat details |

---

## 5. Workers — Execution Engine

### Definition

A Worker connects to the Temporal Cluster, polls a Task Queue, and executes the workflows and activities registered with it.

### Syntax

```python
from temporalio.client import Client
from temporalio.worker import Worker

async def main():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue="my-queue",
        workflows=[MyWorkflow, AnotherWorkflow],
        activities=[my_activity, MyActivities(session)],
    )
    await worker.run()
```

### Responsibilities

- Polls Temporal Cluster on the assigned task queue
- Executes workflows and activities as tasks arrive
- Reports results back to the Cluster
- Handles retries, signals, and queries
- Maintains workflow state during replay

### Running Multiple Workers

One or more workers can poll the same task queue. Scale horizontally by running more worker instances.

---

## 6. Task Queues — Work Routing

### Definition

A Task Queue is a named channel that routes work from the Temporal Cluster to Workers. Must **exactly match** (case-sensitive) between Worker and Client.

### Convention in This Repository

```python
# tasks/my_workflow_tasks.py
TASK_QUEUE = "my-workflow-queue"

# worker.py
Worker(client, task_queue=TASK_QUEUE, workflows=[...], activities=[...])

# starter.py
await client.execute_workflow(
    MyWorkflow.run,
    "arg",
    id="wf-id",
    task_queue=TASK_QUEUE
)
```

### Semantics

- Worker registers itself as a consumer on the queue
- Client posts tasks (start workflow, signals, queries) to the queue
- Temporal Cluster stores tasks until a worker polls
- Multiple workers on the same queue provide load balancing
- Workers on different queues provide isolation

---

## 7. Signals, Queries, and Updates

All three are methods on the Workflow class. They allow external clients to interact with running workflows.

### Signals — Fire-and-Forget, No Return Value

```python
@workflow.signal
def pause(self) -> None:
    self._paused = True

@workflow.signal
def queue_file(self, file_id: int) -> None:
    self._file_queue.append(file_id)
```

**Send from external client:**

```python
await handle.signal(MyWorkflow.pause)
await handle.signal(MyWorkflow.queue_file, 101)
```

**Use case:** Trigger actions without waiting for a response.

### Queries — Synchronous Read, No Side Effects

```python
@workflow.query
def get_status(self) -> WorkflowStatus:
    return WorkflowStatus(
        phase=self._phase,
        started=self._started,
        total_processed=self._count
    )
```

**Read from external client:**

```python
status = await handle.query(MyWorkflow.get_status)
print(f"Phase: {status.phase}, Count: {status.total_processed}")
```

**Use case:** Inspect workflow state without modifying it.

### Updates — Synchronous Modify and Return

```python
@workflow.update
async def run_calculator(self, input: CalculatorInput) -> str:
    result = await workflow.execute_activity(
        calculate,
        args=[input.a, input.b, input.op],
        start_to_close_timeout=timedelta(seconds=10)
    )
    return result

@workflow.update_validator(run_calculator)
def validate_calculator(self, input: CalculatorInput) -> None:
    if input.op not in ("add", "subtract", "multiply", "divide"):
        raise ValueError(f"Unknown op: {input.op}")
```

**Send from external client (blocks until update completes):**

```python
result = await handle.execute_update(
    MyWorkflow.run_calculator,
    args=[CalculatorInput(a=9, b=3, op="divide")]
)
```

**Use case:** Modify workflow state and get a response.

### Comparison

| Aspect | Signal | Query | Update |
|---|---|---|---|
| Modifier | No | No | Yes |
| Blocks caller | No | Yes | Yes |
| Return value | No | Yes | Yes |
| Validator | No | No | Yes |

---

## 8. Retry Policies and Failure Handling

### Automatic Retries

Every activity call is automatically retried on failure (configurable via `RetryPolicy`). The Temporal Cluster handles scheduling retries, backoff, and state recovery.

### Retry Policy Configuration

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

**Default behavior (no explicit policy):** Unlimited retries, exponential backoff (coefficient=2, cap at 100× initial interval).

### Best Practice

**Always set `maximum_attempts` for external service calls.** Otherwise, activities retry forever.

### Non-Retryable Errors

```python
from temporalio.exceptions import ApplicationError

raise ApplicationError(
    "Invalid input: negative amount",
    non_retryable=True
)
```

This stops retries immediately. Use for:
- Invalid input (validation errors)
- Business rule violations
- Permanent failures that retry won't fix

### Shared Helper in Repository

```python
from temporal_python_learning.utils.activity_helpers import default_retry_policy

policy = default_retry_policy(max_attempts=3, initial_interval_seconds=2)
```

---

## 9. Heartbeats and Long-Running Activities

Long-running activities must call `activity.heartbeat()` periodically to:
- Signal liveness to the Temporal Cluster
- Carry progress data for crash recovery
- Allow resumption from the last heartbeat on retry

### Example: File Processing

```python
@activity.defn
async def process_file(file_id: int) -> str:
    for percent in range(10, 110, 10):
        await asyncio.sleep(1)
        activity.heartbeat(f"File {file_id}: {percent}%")
    return f"File {file_id} processed"
```

### Heartbeat Timeout

```python
await workflow.execute_activity(
    process_file,
    file_id=123,
    start_to_close_timeout=timedelta(seconds=120),
    heartbeat_timeout=timedelta(seconds=10),  # Must heartbeat every 10s
)
```

If activity doesn't heartbeat within `heartbeat_timeout`, Temporal marks it failed and schedules a retry.

### On Crash and Retry

```python
# Next attempt can read the last heartbeat's progress data
last_progress = activity.info().heartbeat_details
if last_progress:
    # Resume from last progress
    start_from = last_progress.percent
```

---

## 10. Durable Timers

`await asyncio.sleep(seconds)` inside a Workflow creates a **durable timer** — tracked by the Temporal Cluster, not the Worker process. The Workflow survives Worker crashes during the wait.

### Example

```python
@workflow.run
async def run(self):
    result1 = await workflow.execute_activity(
        step_one,
        start_to_close_timeout=timedelta(seconds=5)
    )

    await asyncio.sleep(10)  # durable — survives worker crash

    result2 = await workflow.execute_activity(
        step_two,
        start_to_close_timeout=timedelta(seconds=5)
    )
```

If the Worker crashes during the sleep, the Workflow automatically resumes and continues waiting for the remaining time when the Worker restarts.

---

## 11. Child Workflows

Spawn child workflows for:
- Independent execution context
- Separate retry scope
- Parallel sub-processes
- Logical isolation

### Basic Pattern

```python
child_handle = await workflow.start_child_workflow(
    FileProcessingChildWorkflow.run,
    id="child-file-123",
    task_queue=TASK_QUEUE,
)
result = await child_handle
```

### Pattern in This Repository

Each child workflow wraps a single activity for isolation:

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

### Parallel Child Workflows

```python
file_handle = await workflow.start_child_workflow(
    FileProcessingChildWorkflow.run,
    id="child-file-1"
)
video_handle = await workflow.start_child_workflow(
    VideoProcessingChildWorkflow.run,
    id="child-video-1"
)

file_result, video_result = await asyncio.gather(file_handle, video_handle)
```

---

## 12. Parallel Activity Execution

Fire multiple activities concurrently without waiting for sequential completion.

### Pattern: Start and Await Later

```python
# Non-blocking — returns handle immediately
handle1 = workflow.start_activity(
    activity1,
    arg1,
    start_to_close_timeout=timedelta(seconds=30)
)
handle2 = workflow.start_activity(
    activity2,
    arg2,
    start_to_close_timeout=timedelta(seconds=30)
)

# Both run in parallel; await later
result1 = await handle1
result2 = await handle2
```

### Pattern: Signal-Triggered Parallel Work

A common pattern: signal handler queues activities that run in parallel:

```python
@workflow.signal
def process_file_signal(self, file_id: int) -> None:
    handle = workflow.start_activity(
        process_file,
        file_id,
        start_to_close_timeout=timedelta(seconds=30),
        retry_policy=RetryPolicy(maximum_attempts=3),
    )
    self.pending_tasks.append(handle)

@workflow.run
async def run(self) -> None:
    while True:
        # Periodically check and await all pending tasks
        if self.pending_tasks:
            results = await asyncio.gather(*self.pending_tasks)
            self.results.extend(results)
            self.pending_tasks.clear()
        await asyncio.sleep(1)
```

---

## 13. Continue-As-New for Infinite Loops

For infinite loops that would exceed the ~50,000 event history limit, use `continue_as_new()` to start a fresh execution with the current state:

```python
from temporalio.workflow import continue_as_new

@workflow.run
async def run(self, count: int) -> None:
    for _ in range(1000):
        count = await workflow.execute_activity(
            increment,
            count,
            start_to_close_timeout=timedelta(seconds=10)
        )

    # Start fresh execution with new state
    workflow.continue_as_new(count)
```

**Use case:** Long-running service workflows that must never terminate.

---

## 14. Sandbox and Import Patterns

Temporal runs Workflows in a **determinism-enforcing sandbox**. Import Activity modules using the pass-through context to avoid sandbox reload overhead:

```python
with workflow.unsafe.imports_passed_through():
    from activities import my_activity, MyActivityClass
    from child_workflows import MyChildWorkflow
```

Pure dataclass / shared-type modules (no I/O, no side effects) can be imported normally:

```python
from dataclasses import dataclass

@dataclass
class OrderInput:
    customer_id: int
    items: List[str]
```

**Rule:** Activities must be imported inside the `unsafe.imports_passed_through()` block.

---

## 15. Dataclass I/O Pattern

**Always use `@dataclass` for structured Workflow/Activity inputs and outputs.** Never use raw `dict`.

```python
from dataclasses import dataclass
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

**Benefits:**
- Temporal's default `DataConverter` serializes/deserializes dataclasses automatically
- Type safety — IDE completion
- Clean Web UI payload views
- Enforces schema consistency

---

## 16. Logging

| Location | Use |
|---|---|
| Inside Workflow | `workflow.logger.info(...)` — replay-safe, suppresses duplicate logs during replay |
| Inside Activity | `activity.logger.info(...)` |
| Worker bootstrap | `logging.basicConfig(level=logging.INFO)` in `main()` |

**Never use `print()` or `logging.getLogger(...)` directly inside Workflow code** — not replay-safe. On replay, logs will be duplicated.

---

## 17. Activity Timeouts

| Timeout | Meaning | Scope |
|---|---|---|
| `start_to_close_timeout` | Max time from Activity start to completion | **Always set this** |
| `schedule_to_close_timeout` | Max time from scheduling to completion (includes queue wait) | Optional; defaults to infinite |
| `schedule_to_start_timeout` | Max time waiting in the Task Queue | Optional; defaults to infinite |
| `heartbeat_timeout` | Max time between `activity.heartbeat()` calls | **Required for long activities** |

**Best practice:** Always set `start_to_close_timeout`; set `heartbeat_timeout` for long-running activities.

---

## 18. Activity Execution Methods

| Method | Use for | Example |
|---|---|---|
| `workflow.execute_activity(fn, arg, ...)` | Standalone function-based activities | `await workflow.execute_activity(my_activity, "input")` |
| `workflow.execute_activity_method(Cls.method, arg, ...)` | Class-based activity methods | `await workflow.execute_activity_method(MyActivities.fetch_user, 123)` |
| `workflow.start_activity(fn, arg, ...)` | Non-blocking fire; returns handle for parallel work | `handle = workflow.start_activity(my_activity, "input"); result = await handle` |
| `workflow.start_activity_method(Cls.method, arg, ...)` | Same as above but for class methods | `handle = workflow.start_activity_method(MyActivities.fetch_user, 123)` |

---

## 19. Testing Workflows and Activities

### Activity — Isolated Test

```python
import pytest
from temporalio.testing import ActivityEnvironment

@pytest.mark.asyncio
async def test_my_activity():
    env = ActivityEnvironment()
    result = await env.run(my_activity, "Alice")
    assert result == "Hello, Alice!"
```

### Workflow — End-to-End with Time Skipping

```python
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

@pytest.mark.asyncio
async def test_my_workflow():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-q",
            workflows=[MyWorkflow],
            activities=[my_activity]
        ):
            result = await env.client.execute_workflow(
                MyWorkflow.run,
                "Alice",
                id="test-wf",
                task_queue="test-q"
            )
    assert result == "Hello, Alice!"
```

**Key feature:** `start_time_skipping()` fast-forwards all `asyncio.sleep()` timers instantly. Workflows that include 10-second timers still complete in milliseconds.

### Mocking Activities in Workflow Tests

```python
@activity.defn(name="my_activity")   # must match real activity name
async def my_activity_mock(name: str) -> str:
    return f"Mocked: {name}"

# Use mock instead of real activity when registering Worker in tests
async with Worker(
    env.client,
    task_queue="test-q",
    workflows=[MyWorkflow],
    activities=[my_activity_mock]  # pass the mock
):
    ...
```

---

## 20. Durable Execution and Replay

### How Replay Works

```
Event History (persisted in Temporal Cluster):
  WorkflowExecutionStarted
  ActivityTaskScheduled → step_one
  ActivityTaskCompleted → "result A"     ← on replay: injected from cache, NOT re-executed
  TimerStarted → 10s
  TimerFired                              ← on replay: skipped
  ActivityTaskScheduled → step_two       ← resumes here after Worker crash
  ActivityTaskCompleted → "result B"
  WorkflowExecutionCompleted
```

### Why Determinism Matters

Temporal replays Workflow code from history to reconstruct state. If the code produces a different sequence of commands on replay (e.g., different branch taken due to `random()`), Temporal raises a non-determinism error and the Workflow fails permanently.

**Example of non-determinism error:**

```python
# ❌ BAD — will fail on replay
@workflow.run
async def run(self):
    if random.random() > 0.5:  # Different on replay!
        await workflow.execute_activity(activity_a)
    else:
        await workflow.execute_activity(activity_b)

# ✅ GOOD — deterministic
@workflow.run
async def run(self, random_input: bool):
    if random_input:
        await workflow.execute_activity(activity_a)
    else:
        await workflow.execute_activity(activity_b)
```

### Consequence for Workflow Code Changes

- **Activity code changes:** Safe to hot-deploy. Only new activity calls use new code.
- **Workflow code changes:** Risky for in-flight executions. Restart workers after changes to avoid non-determinism errors.

---

## 21. Temporal CLI

```bash
# Start local dev server (in-memory DB)
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

# Send a signal
temporal workflow signal \
  --workflow-id my-workflow-01 \
  --name signal-name \
  --input '{"field": "value"}'

# Query workflow state
temporal workflow query \
  --workflow-id my-workflow-01 \
  --query-type query-name
```

---

## 22. Deployment Options

| Option | Use Case | DB | UI Port |
|---|---|---|---|
| `temporal server start-dev` | Local single-process development | In-memory | 8233 |
| `docker-compose-postgres.yml` | Full local cluster with Postgres | Postgres | 8080 |
| `docker-compose-mysql.yml` | Full local cluster with MySQL | MySQL | 8080 |
| Kubernetes | Production self-hosted | External | 8080 |
| **Temporal Cloud** | Fully managed SaaS | Managed | N/A |

**Key difference:** In dev server, UI is at port `8233`. In Docker Compose / Production, UI is at port `8080`.

---

## 23. Key API Reference

```python
# ===== Client Setup =====
from temporalio.client import Client

client = await Client.connect("localhost:7233")
client = await Client.connect("localhost:7233", namespace="my-namespace")

# ===== Start / Execute Workflow =====
# Start and get handle (non-blocking)
handle = await client.start_workflow(
    Wf.run,
    arg,
    id="wf-id",
    task_queue="q"
)

# Start and wait for result (blocking)
result = await client.execute_workflow(
    Wf.run,
    arg,
    id="wf-id",
    task_queue="q"
)

# Get handle to existing workflow
handle = client.get_workflow_handle("wf-id")

# ===== Interact with Running Workflow =====
# Send signal (fire-and-forget)
await handle.signal(Wf.my_signal, payload)

# Query state (synchronous read)
result = await handle.query(Wf.my_query)

# Execute update (synchronous modify)
result = await handle.execute_update(Wf.my_update, args=[payload])

# Get workflow result
result = await handle.result()

# ===== Inside Workflow: Execute Activity =====
result = await workflow.execute_activity(
    fn,
    arg,
    start_to_close_timeout=timedelta(seconds=10)
)

result = await workflow.execute_activity_method(
    Cls.method,
    arg,
    start_to_close_timeout=timedelta(seconds=10)
)

# ===== Inside Workflow: Non-Blocking Activity =====
handle = workflow.start_activity(
    fn,
    arg,
    start_to_close_timeout=timedelta(seconds=10)
)
result = await handle  # await whenever needed

# ===== Inside Workflow: Child Workflow =====
child = await workflow.start_child_workflow(
    ChildWf.run,
    id="child-id",
    task_queue="q"
)
result = await child

# ===== Inside Workflow: Durable Timer =====
await asyncio.sleep(seconds)  # durable, cluster-tracked

# ===== Inside Workflow: Continue-As-New =====
from temporalio.workflow import continue_as_new
workflow.continue_as_new(new_arg)

# ===== Inside Activity: Heartbeat =====
activity.heartbeat("progress message")
attempt_number = activity.info().attempt
```

---

## 24. Environment Variables

```bash
TEMPORAL_HOST=localhost:7233          # Client connection
TEMPORAL_NAMESPACE=default            # Namespace
TEMPORAL_VERSION=1.x.x               # Docker Compose version
TEMPORAL_ADMINTOOLS_VERSION=1.x.x    # AdminTools version
TEMPORAL_UI_VERSION=x.x.x            # UI version
```

See `temporal-python-learning/.env.example` for a complete example.

---

## 25. Common Pitfalls

1. **Forgetting `await` on `execute_activity`** — Returns a coroutine. Causes `TypeError: coroutine is not JSON serializable`.
2. **Timeouts as int instead of `timedelta`** — `start_to_close_timeout=10` raises type error; must be `timedelta(seconds=10)`.
3. **Task queue name case-sensitive** — `"Banking-System"` ≠ `"banking-system"`. Must match exactly.
4. **Non-determinism in Workflow code** — Never use `random`, `datetime.now()`, `uuid.uuid4()`, or I/O directly in workflow code.
5. **Using `print()` or bare `logging.getLogger()` in Workflow** — Not replay-safe. Causes duplicate logs. Use `workflow.logger`.
6. **Restarting Worker without considering in-flight Workflows** — Workflow code changes risk non-determinism. Activity changes are safe to hot-deploy.
7. **Not setting `maximum_attempts` on RetryPolicy** — Activities retry forever. Always set this for external services.
8. **Ignoring history limit (~50k events)** — Infinite loops hit the limit in production. Use `continue_as_new`.
9. **Forgetting `with workflow.unsafe.imports_passed_through()`** — Activity imports must be inside this block in Workflow files.
10. **Passing class instead of instance to `Worker(activities=...)`** — Must pass an instance: `MyActivities(session)`, not `MyActivities`.

---

## 26. Best Practices

| Practice | Rationale |
|---|---|
| Always set `start_to_close_timeout` on activities | Defines a clear timeout; prevents unbounded waiting |
| Set `heartbeat_timeout` for long-running activities | Allows resumption from last checkpoint on retry |
| Use `@dataclass` for all I/O | Type safety, IDE completion, clean Web UI views |
| Separate workers from starters | Keeps concerns separate; easier to run multiple workers |
| Use `asyncio.gather()` for parallel activities | Cleaner syntax than manual handle management |
| Log with `workflow.logger` and `activity.logger` | Replay-safe; avoids duplicate logs |
| Raise `ApplicationError(..., non_retryable=True)` for business errors | Stops retries immediately for deterministic failures |
| Define `TASK_QUEUE` as module constant | Single source of truth for task queue name |
| Use child workflows for isolation | Separate retry scope, independent execution context |
| Test with `WorkflowEnvironment.start_time_skipping()` | Fast tests; timers complete instantly |

---

## 27. Repository Examples

### demo/temporal-poc-demo/ — Temporal Showcase POC

**The most complete example in the repo.** Single `TemporalShowcaseWorkflow` that exercises every major Temporal feature in sequence.

**File layout:**
- `workflows.py` — `TemporalShowcaseWorkflow` (6 phases)
- `activities.py` — All activities from tutorial sub-projects
- `child_workflows.py` — `FileProcessingChildWorkflow`, `VideoProcessingChildWorkflow`
- `shared.py` — All dataclasses
- `worker.py` — Worker registration
- `starter.py` — Workflow startup with step-by-step driver commands
- `clients.py` — CLI driver for signals, queries, updates

**Task queue:** `"temporal-showcase-queue"`

**How to run:**

```bash
# Terminal 1
python demo/temporal-poc-demo/worker.py

# Terminal 2
python demo/temporal-poc-demo/starter.py --pin 742

# Terminal 3
python demo/temporal-poc-demo/clients.py <workflow_id> query_status
python demo/temporal-poc-demo/clients.py <workflow_id> stop_counter
```

### Banking System — Pattern Reference

> **Note:** The banking system project files are not present in this repository. The following describes the patterns it demonstrated, which remain valid Temporal SDK reference material.

**Production-style banking workflow** — long-running `BankServerWorkflow` acting as a stateful account server. Demonstrates how to build an always-on service workflow that handles external interactions via signals, queries, and updates.

**Key patterns demonstrated:**
- Signals: `freeze_account`, `unfreeze_account`, `stop_bank_server`
- Queries: `check_balance` (guards against frozen state; returns error string if frozen)
- Updates: `add_money_to_account`, `remove_money_from_account` (both validate frozen state)
- Infinite loop workflow (`while not self.stop_server`) — typical for service-style workflows
- Separate external client scripts for each operation

**Task queue pattern:** `"Banking-System"` — always a named constant shared between worker and starters.

### temporal-python-tutorial/ Sub-Projects

Each tutorial is a standalone package demonstrating a specific concept:

| Directory | Concept |
|---|---|
| `activity-loop-until-output/` | Activity loop until condition; signal to stop; update to inject override |
| `child-workflows_and_continue_as_new/` | Child workflow spawning |
| `failing_activity_tutorial/` | Retry behavior on random failures |
| `learn_temporal_tutorial/` | Core fundamentals, structured |
| `parallel-file-processing-signals/` | Signal-triggered parallel activities |
| `signals_and_heartbeats/` | Combined signal, heartbeat, logging |

### temporal-python-learning/

**Structured 101/102 learning path:**

- **Docs** (`docs/`): 20 concept files covering Temporal 101 (overview, architecture, workers, activities, CLI, Web UI, retry, deployment) and 102 (durable execution, testing, debugging, best practices)
- **Exercises** (`exercises/`): 7 standalone scripts (hello workflow, Web UI, durable execution, testing, debugging)
- **Projects** (`projects/`): 3 mini-projects (greeting, translation, pizza order debug)
- **Utils** (`utils/`): Shared helpers (client, retry policy, activity options)

---

## 28. Coding Conventions

| Convention | Detail |
|---|---|
| Task queue constant | `TASK_QUEUE = "queue-name"` at module level, imported by worker and starter |
| Workflow ID | Business-meaningful string; often includes `uuid.uuid4().hex[:8]` suffix for uniqueness |
| Dataclasses in shared.py | All I/O types in a dedicated `shared.py` (or `shared/`) module |
| Sandbox imports | Activity/child-workflow imports inside `with workflow.unsafe.imports_passed_through():` |
| Class-based activities | Used when activities need injected dependencies (DB, HTTP session) |
| Function-based activities | Used for simple, stateless activities |
| External client scripts | Separate file(s) for interaction — not mixed into worker |
| Starter separate from worker | `starter.py` / `client.py` / `starters/` always a separate file from `worker.py` |
| `asyncio.run(main())` | All entry points use this pattern |

---

## Summary

This handbook covers all essential Temporal patterns needed to build durable, fault-tolerant workflows in Python. Start with the [demo/temporal-poc-demo/](../../../demo/temporal-poc-demo/) showcase and [temporal-python-tutorial/](../../../temporal-python-tutorial/) for focused examples, then refer to this handbook as you build your own workflows.

For learning-oriented deeper dives, see [temporal-python-learning/docs/](../../../temporal-python-learning/docs/).

---

**Last Updated:** 2026-06-06
**Version:** 1.0
**Scope:** Temporal SDK for Python >= 1.24.0
