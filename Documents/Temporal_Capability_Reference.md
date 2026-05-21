# Temporal Capability & Design Reference Guide

> **One-line definition:**  
> Temporal is a durable execution platform that turns ordinary Python functions into fault-tolerant, stateful, long-running processes — without you writing retry loops, state stores, or recovery logic.

---

## Quick Support Legend

| Symbol | Meaning |
|--------|---------|
|  Native | Built into Temporal — zero extra infrastructure |
|  Partial | Supported via a design pattern — requires intentional code structure |
|  External | Needs an external system; Temporal orchestrates but doesn't provide it |

---

## Table of Contents

1. [Loops Inside Temporal](#1-loops-inside-temporal)
2. [Retries](#2-retries)
3. [Audit Functionality / Monitoring](#3-audit-functionality--monitoring)
4. [Trigger Mechanisms](#4-trigger-mechanisms)
5. [Data Capture](#5-data-capture)
6. [Validation and Correctness](#6-validation-and-correctness)
7. [Decision and Routing](#7-decision-and-routing)
8. [Human Interaction](#8-human-interaction)
9. [Execution (External Systems)](#9-execution-external-systems)
10. [Sequential vs Parallel Execution](#10-sequential-vs-parallel-execution)
11. [Stateful Workflow](#11-stateful-workflow)
12. [Deterministic Execution (Idempotency)](#12-deterministic-execution-idempotency)
13. [Exception Handling](#13-exception-handling)
14. [Versioning](#14-versioning)
15. [Resilience, Traceability, Reconstruction, Controllability](#15-resilience-traceability-reconstruction-controllability)
16. [Batch Execution](#16-batch-execution)
17. [Real-time Execution](#17-real-time-execution)

---

---

## 1. Loops Inside Temporal

### →  Native

---

### 1. Explanation (ELI5)

Think of a Temporal Workflow like a while-loop that never forgets where it was — even if your server crashes mid-iteration. You write a normal Python `while` or `for` loop and Temporal makes it durable, automatically replaying to the correct iteration on recovery.

---

### 2. How Temporal Handles It

- Workflows are **replayed** from their event history when a Worker restarts.
- Every completed Activity inside the loop is recorded as an event; on replay its result is read from history — the Activity is not re-executed.
- Loop control (stop flags, max counts) lives in **Workflow state** — signals flip these flags from outside.
- For history-size safety on very long loops, use **`continue_as_new`** to carry forward only essential state and start fresh history.

---

### 3. Code Example

```python
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import increment_counter

@workflow.defn
class CounterWorkflow:
    def __init__(self) -> None:
        self._stop = False
        self._count = 0

    @workflow.signal
    def stop(self) -> None:
        self._stop = True

    @workflow.query
    def get_count(self) -> int:
        return self._count

    @workflow.run
    async def run(self) -> int:
        while not self._stop:
            await workflow.sleep(timedelta(seconds=2))
            self._count = await workflow.execute_activity(
                increment_counter,
                self._count,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
        return self._count
```

For infinite loops with growing history, reset with `continue_as_new`:

```python
from temporalio.workflow import continue_as_new

@workflow.run
async def run(self, count: int) -> None:
    for _ in range(1000):
        count = await workflow.execute_activity(...)
    # Hand off state to a fresh execution
    workflow.continue_as_new(count)
```

---

### 4. Key Insight

- **Activity results inside loops are cached in event history** — Temporal never re-calls `increment_counter` during replay; it reads the recorded result. This is what makes the loop durable, not magic.
- **History size limit (~50k events) matters for long loops.** Use `continue_as_new` to avoid hitting the limit in production infinite-loop workflows.

---

---

## 2. Retries

### →  Native

---

### 1. Explanation (ELI5)

When an Activity fails (network timeout, API error, anything), Temporal automatically retries it without you writing a single line of retry code. You declare the policy once when you call the Activity and Temporal handles the rest — including waiting, back-off, and deciding when to give up.

---

### 2. How Temporal Handles It

- The Temporal Cluster records `ActivityTaskFailed` in the event history.
- It schedules a new `ActivityTaskScheduled` after the back-off interval.
- Each retry attempt increments `activity.info().attempt`.
- The Workflow code **sees only the final success** — intermediate failures are invisible to Workflow logic unless you explicitly inspect the attempt count.
- `non_retryable=True` on an `ApplicationError` stops retries immediately — useful for business validation errors.

---

### 3. Code Example

```python
from datetime import timedelta
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from temporalio import activity, workflow

@activity.defn
async def call_payment_api(amount: float) -> str:
    if amount < 0:
        raise ApplicationError("Negative amount", non_retryable=True)  # never retry
    # ... real API call that may transiently fail
    return "charged"

@workflow.defn
class PaymentWorkflow:
    @workflow.run
    async def run(self, amount: float) -> str:
        return await workflow.execute_activity(
            call_payment_api,
            amount,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=1),
                backoff_coefficient=2.0,         # 1s → 2s → 4s → 8s …
                maximum_interval=timedelta(seconds=30),
                maximum_attempts=5,
            ),
        )
```

---

### 4. Key Insight

- **Default behaviour is unlimited retries with exponential back-off** (`backoff_coefficient=2.0`, cap at 100× initial). Always set `maximum_attempts` for Activities that call external services.
- **Retries do not re-enter the Workflow** — only the Activity is retried. The Workflow thread stays parked waiting for the Activity result.

---

---

## 3. Audit Functionality / Monitoring

### →  Native (Event History) +  External (Metrics/Alerting)

---

### 1. Explanation (ELI5)

Every step your Workflow takes is written to an immutable log called the **event history**. You can inspect this log at any time — while the Workflow is running, after it completes, or years later — and see exactly what happened, when, and with what data.

---

### 2. How Temporal Handles It

- **Event history** is the built-in audit trail. Every `ActivityTaskScheduled`, `ActivityTaskCompleted`, `TimerFired`, `SignalReceived`, etc. is recorded with timestamps and payloads.
- The **Temporal Web UI** (`:8233`) visualises the event history graphically.
- The **CLI** lets you inspect it programmatically:  
  `temporal workflow show --workflow-id <id>`
- `workflow.logger` and `activity.logger` emit structured logs that are suppressed during replay (preventing duplicate log entries).
- For external observability (Prometheus metrics, Datadog, PagerDuty), Temporal exports SDK and server metrics that you connect to your existing monitoring stack.

---

### 3. Code Example

```python
# Inside a workflow
workflow.logger.info(f"Processing order {order_id} — phase: billing")

# Inside an activity
activity.logger.info(f"Calling payment API for order {order_id}")
activity.heartbeat(f"Payment attempt {activity.info().attempt}")
```

CLI audit query:
```bash
temporal workflow show --workflow-id order-workflow-XD001
# Lists every event: scheduled, started, completed, failed, retried
```

---

### 4. Key Insight

- **`workflow.logger` is replay-safe** — it suppresses duplicate log lines during replay. Never use `print()` or standard `logging` directly inside a Workflow.
- **Heartbeats serve as a sub-activity audit trail.** They record progress within a long-running Activity — if the Worker crashes, the next attempt can pick up from the last heartbeat checkpoint.

---

---

## 4. Trigger Mechanisms

### →  Native (Signals, Schedules, Child Workflows) +  External (HTTP, Events)

---

### 1. Explanation (ELI5)

Temporal Workflows can be started (triggered) in multiple ways: from code, on a schedule, by an HTTP call to your application, in response to another Workflow completing, or via a message from an external system.

---

### 2. How Temporal Handles It

| Trigger Type | Mechanism |
|---|---|
| Code / API call | `client.start_workflow()` or `client.execute_workflow()` |
| Scheduled (cron) | `CronSchedule` or Temporal Schedules API |
| Signal from outside | `handle.signal(workflow.some_signal, payload)` |
| Child workflow | `workflow.start_child_workflow()` from a parent |
| External event | Your code receives the event and calls `client.start_workflow()` |

---

### 3. Code Example

```python
# Trigger from application code
handle = await client.start_workflow(
    OrderWorkflow.run,
    OrderInput(order_id="XD001", amount=49.99),
    id="order-workflow-XD001",
    task_queue="order-tasks",
)

# Trigger on a schedule (cron)
handle = await client.start_workflow(
    DailyReportWorkflow.run,
    id="daily-report",
    task_queue="report-tasks",
    cron_schedule="0 9 * * *",  # Every day at 09:00
)

# Trigger a child workflow from inside a parent
child_handle = await workflow.start_child_workflow(
    FileProcessingChildWorkflow.run,
    id=f"{workflow.info().workflow_id}-child-file",
    task_queue="processing-tasks",
)
```

---

### 4. Key Insight

- **Signals are not triggers for new workflows — they are messages to a running workflow.** To trigger from an external event (Kafka, webhook), your consumer code calls `client.start_workflow()` or `handle.signal()`.
- **Temporal Schedules** (the newer API replacing `cron_schedule`) offer pause/unpause, backfill, and jitter — more control than a plain cron.

---

---

## 5. Data Capture

### →  Native (Event History Payloads) +  Partial (Custom Storage via Activities)

---

### 1. Explanation (ELI5)

Every input and output that flows through your Workflow — Activity arguments, return values, signal payloads, query results — is automatically serialised and stored in the event history. You can inspect, query, and export this data at any time.

---

### 2. How Temporal Handles It

- **DataConverter** serialises inputs/outputs (JSON by default) into the event history.
- `dataclass` objects are natively serialised — use typed dataclasses instead of raw dicts for structured capture.
- **Search Attributes** let you tag Workflow executions with indexed custom metadata (e.g., customer ID, order status) that you can query across all executions.
- For long-term persistence outside Temporal (data warehouse, DB), use an Activity that writes to your storage system.

---

### 3. Code Example

```python
from dataclasses import dataclass
from temporalio import workflow

@dataclass
class OrderInput:
    order_id: str
    amount: float
    customer_id: int

@dataclass
class OrderResult:
    status: str
    confirmation_number: str

@workflow.defn
class OrderWorkflow:
    @workflow.run
    async def run(self, input: OrderInput) -> OrderResult:
        # input is captured in event history as JSON
        result = await workflow.execute_activity(
            process_order, input,
            start_to_close_timeout=timedelta(seconds=30),
        )
        # result is captured in event history
        return result
```

---

### 4. Key Insight

- **The event history is not a database.** It holds execution data, not domain data. For analytical queries or long-term reporting, write to an external store via an Activity.
- **Custom DataConverters** let you encrypt payloads at rest — critical for PII. This keeps sensitive data from appearing in plain text in the Web UI.

---

---

## 6. Validation and Correctness

### →  Partial (Design Pattern Required)

---

### 1. Explanation (ELI5)

Temporal doesn't have a built-in "validate this input before running" step, but you design for correctness by raising `ApplicationError(non_retryable=True)` in Activities and by using typed dataclasses with Python's type system. Invalid input stops the workflow immediately without burning retries.

---

### 2. How Temporal Handles It

- **Input validation** is done at the Activity level using `ApplicationError` with `non_retryable=True` — tells Temporal "this is a business logic error, not a transient failure; don't retry."
- **Typed dataclasses** enforce structure at serialisation time through Python's type system.
- **Update validators** (`@workflow.update_validator`) let you reject an update before it modifies Workflow state.
- **Workflow-level guards** check state in the `@workflow.run` method before dispatching Activities.

---

### 3. Code Example

```python
from temporalio.exceptions import ApplicationError
from temporalio import activity, workflow

# Activity-level validation
@activity.defn
async def process_order(order: OrderInput) -> OrderResult:
    if order.amount < 0:
        raise ApplicationError(
            f"Invalid order amount: {order.amount}",
            non_retryable=True,   # Do NOT retry — the input is wrong
        )
    # ... process

# Update validator (rejects before state changes)
@workflow.defn
class OrderWorkflow:
    @workflow.update_validator(apply_discount)
    def validate_discount(self, pct: int) -> None:
        if pct < 0 or pct > 100:
            raise ValueError(f"Discount {pct}% is out of range")

    @workflow.update
    async def apply_discount(self, pct: int) -> str:
        # Only reached if validator passes
        ...
```

---

### 4. Key Insight

- **`non_retryable=True` is the key distinction between a transient failure (retry) and a business error (fail fast).** Omitting it on validation errors wastes retries and confuses debugging.
- Temporal cannot validate data before a Workflow starts — that is the responsibility of the client code or an initial validation Activity.

---

---

## 7. Decision and Routing

### →  Native

---

### 1. Explanation (ELI5)

Ordinary Python `if/elif/else` in a Workflow *is* the routing logic. Because Workflow code is deterministic and replayed from history, the routing decisions are durable — they are the same every time the Workflow replays.

---

### 2. How Temporal Handles It

- Conditional logic in Workflow code determines which Activities to execute, in what order, and with what parameters.
- Routing based on **runtime data** (e.g., distance > 25 km → reject order) is handled by reading Activity results and branching.
- **Signals** let external systems inject routing decisions into a running Workflow.
- **Child Workflows** route entire sub-processes to different Task Queues or Workers.

---

### 3. Code Example

```python
@workflow.defn
class PizzaOrderWorkflow:
    @workflow.run
    async def run(self, order: PizzaOrder) -> OrderConfirmation:
        distance = await workflow.execute_activity(
            get_distance, order.address,
            start_to_close_timeout=timedelta(seconds=10),
        )

        # Routing decision based on activity result
        if order.is_delivery and distance.kilometers > 25:
            raise ApplicationError("Customer outside delivery area", non_retryable=True)

        # Route to different activity based on order type
        if order.is_delivery:
            confirmation = await workflow.execute_activity(
                dispatch_delivery_driver, order,
                start_to_close_timeout=timedelta(seconds=30),
            )
        else:
            confirmation = await workflow.execute_activity(
                prepare_pickup, order,
                start_to_close_timeout=timedelta(seconds=30),
            )

        return confirmation
```

---

### 4. Key Insight

- **All routing logic must be deterministic** — the same inputs must always produce the same branch. Never route based on `random.random()`, `datetime.now()`, or external API calls directly inside the Workflow. Drive conditional logic from Activity results.

---

---

## 8. Human Interaction

### →  Partial (Design Pattern via Signals + External Wait)

---

### 1. Explanation (ELI5)

Temporal can pause a Workflow for days, waiting for a human to approve an action. When the human acts (clicks "Approve" in a UI), your backend sends a Signal to the Workflow, which wakes up and continues. The Workflow doesn't poll — it just waits efficiently.

---

### 2. How Temporal Handles It

- Workflow calls `await workflow.wait_condition(lambda: self._approved)`.
- This is a **durable wait** — the Worker can restart, the cluster can restart, and the wait survives.
- A frontend/backend hits your API, which sends `handle.signal(workflow.approve, reviewer_id)`.
- The Workflow state flag flips, `wait_condition` resolves, and execution continues.
- **Queries** let the UI poll current status ("Is this still waiting for approval?") without modifying state.

---

### 3. Code Example

```python
from temporalio import workflow
from dataclasses import dataclass

@dataclass
class ApprovalInput:
    order_id: str
    amount: float

@workflow.defn
class OrderApprovalWorkflow:
    def __init__(self) -> None:
        self._approved: bool = False
        self._reviewer_id: str = ""

    @workflow.signal
    def approve(self, reviewer_id: str) -> None:
        self._approved = True
        self._reviewer_id = reviewer_id
        workflow.logger.info(f"Order approved by {reviewer_id}")

    @workflow.signal
    def reject(self, reason: str) -> None:
        self._approved = False
        workflow.logger.info(f"Order rejected: {reason}")

    @workflow.query
    def is_pending(self) -> bool:
        return not self._approved

    @workflow.run
    async def run(self, input: ApprovalInput) -> str:
        workflow.logger.info(f"Waiting for approval on order {input.order_id}")

        # Durable wait — survives crashes, no polling
        await workflow.wait_condition(
            lambda: self._approved,
            timeout=timedelta(days=7),   # auto-expire after 7 days
        )

        return f"Order {input.order_id} approved by {self._reviewer_id}"
```

From the external system (e.g., FastAPI endpoint):
```python
handle = client.get_workflow_handle("order-approval-XD001")
await handle.signal(OrderApprovalWorkflow.approve, "reviewer@company.com")
```

---

### 4. Key Insight

- **There is no built-in UI** for human interaction — you build it. Temporal provides the reliable waiting and waking mechanism; your frontend and API provide the human interface.
- Set a **timeout on `wait_condition`** so workflows don't wait forever if a human never acts.

---

---

## 9. Execution (External Systems)

### →  Native (via Activities) +  External (The Systems Themselves)

---

### 1. Explanation (ELI5)

Whenever your Workflow needs to talk to the outside world — call an API, write to a database, send an email — it does so through Activities. Activities are the bridge between Temporal's durable orchestration and real-world systems.

---

### 2. How Temporal Handles It

- The Workflow calls `workflow.execute_activity(call_payment_api, ...)`.
- The Activity runs on a Worker — it has full access to the network, DB drivers, HTTP clients, etc.
- Temporal records the result in the event history on success.
- If the external call fails, Temporal retries the Activity per the `RetryPolicy`.
- **Class-based Activities** support dependency injection (shared HTTP session, DB connection pool) — the right pattern for external system clients.

---

### 3. Code Example

```python
import aiohttp
from temporalio import activity

class ExternalSystemActivities:
    def __init__(self, http_session: aiohttp.ClientSession):
        self.session = http_session

    @activity.defn
    async def call_payment_gateway(self, amount: float) -> str:
        activity.logger.info(f"Charging {amount} via payment gateway")
        async with self.session.post(
            "https://payment-api.internal/charge",
            json={"amount": amount},
        ) as resp:
            resp.raise_for_status()
            return (await resp.json())["transaction_id"]

    @activity.defn
    async def send_confirmation_email(self, email: str, order_id: str) -> None:
        activity.logger.info(f"Sending confirmation to {email}")
        async with self.session.post(
            "https://mail-api.internal/send",
            json={"to": email, "order_id": order_id},
        ) as resp:
            resp.raise_for_status()

# Worker registration with shared session
async with aiohttp.ClientSession() as session:
    activities = ExternalSystemActivities(session)
    worker = Worker(client, task_queue="order-tasks",
                    activities=[activities.call_payment_gateway,
                                 activities.send_confirmation_email], ...)
```

---

### 4. Key Insight

- **Activities must be idempotent when calling external systems.** Temporal may retry an Activity even after it partially succeeded (e.g., if the Worker crashed before recording the result). Design your external calls to be safe to call twice — use idempotency keys.
- Use `heartbeat_timeout` on long-running Activity calls so Temporal detects a stuck Worker quickly and retries on another.

---

---

## 10. Sequential vs Parallel Execution

### →  Native

---

### 1. Explanation (ELI5)

By default, `await`-ing Activities one after another is sequential — each waits for the previous to complete. To run things at the same time, use `asyncio.gather()` for Activities or `workflow.start_activity()` for non-blocking parallel launches. Both patterns work durably across crashes.

---

### 2. How Temporal Handles It

- **Sequential**: `await workflow.execute_activity(A)` then `await workflow.execute_activity(B)` — B starts only after A completes.
- **Parallel via `asyncio.gather`**: Both activities are scheduled simultaneously; the Workflow resumes when both are done.
- **Parallel via `start_activity`**: Returns a handle immediately; you can launch many activities and await handles later, or never (fire-and-forget within workflow).
- **Child Workflows in parallel**: Start multiple child workflows and `asyncio.gather` their handles.
- All of the above are **fully durable** — Temporal tracks every scheduled/completed event.

---

### 3. Code Example

```python
import asyncio
from temporalio import workflow

@workflow.defn
class ProcessingWorkflow:
    @workflow.run
    async def run(self) -> dict:

        # ── Sequential ───────────────────────────────────────────
        step1 = await workflow.execute_activity(
            validate_order, start_to_close_timeout=timedelta(seconds=10))
        step2 = await workflow.execute_activity(
            charge_customer, start_to_close_timeout=timedelta(seconds=30))

        # ── Parallel via gather ───────────────────────────────────
        file_result, video_result = await asyncio.gather(
            workflow.execute_activity(process_file,
                                      start_to_close_timeout=timedelta(seconds=60)),
            workflow.execute_activity(process_video,
                                      start_to_close_timeout=timedelta(seconds=60)),
        )

        # ── Dynamic parallel (signal-fed) ─────────────────────────
        handles = []
        for file_id in self._file_queue:
            handle = workflow.start_activity(
                process_file, file_id,
                start_to_close_timeout=timedelta(seconds=60),
                heartbeat_timeout=timedelta(seconds=10),
            )
            handles.append(handle)
        results = await asyncio.gather(*handles)

        return {"step1": step1, "step2": step2, "files": list(results)}
```

---

### 4. Key Insight

- **`asyncio.gather` inside a Workflow is deterministic** because Temporal controls the event loop. Do not use `asyncio.create_task()` or raw threads inside a Workflow — both break determinism.
- **Sync Activities run on a thread pool**, not the event loop. They can be truly parallel in CPU time, but from the Workflow's perspective they're just Activities that return results.

---

---

## 11. Stateful Workflow

### →  Native

---

### 1. Explanation (ELI5)

A Temporal Workflow is a class with instance variables. Whatever you store in `self._something` is your workflow's state. If the Worker crashes, Temporal replays the event history to reconstruct every instance variable back to exactly where it was. Your state is permanent.

---

### 2. How Temporal Handles It

- Workflow state lives in Python instance variables (`self.*`).
- On Worker restart, Temporal sends the full event history to a new Worker.
- The Worker replays the Workflow code from scratch — `__init__` runs, then every event is applied in order — restoring all `self.*` fields to their exact pre-crash values.
- **Signals** are the primary way to mutate state from outside.
- **Queries** read state without mutating it (safe to call from anywhere, anytime).

---

### 3. Code Example

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class WorkflowState:
    phase: str
    items_processed: int
    last_error: Optional[str]

@workflow.defn
class StatefulProcessorWorkflow:
    def __init__(self) -> None:
        self._phase: str = "idle"
        self._count: int = 0
        self._paused: bool = False

    @workflow.signal
    def pause(self) -> None:
        self._paused = True

    @workflow.signal
    def resume(self) -> None:
        self._paused = False

    @workflow.query
    def get_state(self) -> WorkflowState:
        return WorkflowState(
            phase=self._phase,
            items_processed=self._count,
            last_error=None,
        )

    @workflow.run
    async def run(self) -> int:
        self._phase = "processing"
        while self._count < 100:
            await workflow.wait_condition(lambda: not self._paused)
            result = await workflow.execute_activity(
                process_item, self._count,
                start_to_close_timeout=timedelta(seconds=10),
            )
            self._count += 1
        self._phase = "done"
        return self._count
```

---

### 4. Key Insight

- **Do not persist state in a database from within the Workflow function itself.** Workflow code runs during replay — writing to a DB inside `@workflow.run` would double-write on every replay. All side effects must go through Activities.
- **Workflow history is the state store.** You don't need Redis or a DB to remember where you are — Temporal already does that.

---

---

## 12. Deterministic Execution (Idempotency)

### →  Native (Enforced by Design)

---

### 1. Explanation (ELI5)

When a Worker crashes mid-workflow, the next Worker replays everything from scratch. For this to work correctly, the same Workflow code must produce the same decisions every single time it runs — no randomness, no reading the clock directly, no calling external APIs. Temporal's sandbox enforces this.

---

### 2. How Temporal Handles It

- Temporal runs Workflow code in a **sandboxed event loop** that intercepts non-deterministic operations.
- During replay, Activity calls are **not re-executed** — their recorded results are injected back in. 
- `asyncio.sleep()` becomes a durable timer, not a real sleep — it's skipped instantly during replay.
- `workflow.now()` returns the Workflow-safe current time (from event history), not the system clock.
- **Non-determinism errors** (`WorkflowTaskFailed`) occur when a code change between deployments alters the execution path — a critical failure mode to understand.

---

### 3. Code Example

```python
from temporalio import workflow
import asyncio

@workflow.defn
class DeterministicWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:

        #  Correct — use workflow.now() for current time
        now = workflow.now()

        #  Correct — delegate randomness to activities
        random_value = await workflow.execute_activity(
            get_random_number,
            start_to_close_timeout=timedelta(seconds=5),
        )

        #  Correct — durable timer
        await asyncio.sleep(10)

        return f"Hello {name} at {now}"

        # ❌ WRONG — never do these:
        # import random; x = random.random()
        # import datetime; t = datetime.datetime.now()
        # response = await aiohttp.get("https://api.example.com")
```

---

### 4. Key Insight

- **Determinism is not optional — it is required for correctness.** A non-deterministic Workflow will produce a `WorkflowTaskFailed` error during replay due to an event history mismatch.
- When you need to change Workflow logic that is currently running in production, use the **Workflow Versioning API** (`workflow.patched()`) to branch behaviour based on whether the execution predates the change.

---

---

## 13. Exception Handling

### →  Native

---

### 1. Explanation (ELI5)

Errors in Temporal are first-class citizens. Activities can fail (transient errors get retried automatically; business errors stop immediately). Workflows can fail or be cancelled. You use Python `try/except` and Temporal's `ApplicationError` to express intent about what should happen on failure.

---

### 2. How Temporal Handles It

| Error Type | Class | Behaviour |
|---|---|---|
| Transient (network, timeout) | Any `Exception` | Retried per `RetryPolicy` |
| Business logic error | `ApplicationError(non_retryable=True)` | Fails immediately, no retry |
| Workflow failure | `ApplicationError` (from Activity exhausted) | Workflow transitions to `Failed` |
| Workflow cancellation | `CancelledError` | Workflow transitions to `Cancelled` |
| Workflow termination | External `terminate()` call | Immediate stop, no cleanup |

---

### 3. Code Example

```python
from temporalio.exceptions import ApplicationError, ActivityError
from temporalio import activity, workflow

# Activity raising a business error
@activity.defn
async def validate_order(order: OrderInput) -> None:
    if order.amount <= 0:
        raise ApplicationError("Order amount must be positive", non_retryable=True)

# Workflow catching activity failure
@workflow.defn
class OrderWorkflow:
    @workflow.run
    async def run(self, order: OrderInput) -> str:
        try:
            await workflow.execute_activity(
                validate_order, order,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
        except ActivityError as e:
            workflow.logger.error(f"Validation failed: {e.cause}")
            raise ApplicationError("Order rejected due to validation", non_retryable=True)

        return await workflow.execute_activity(
            process_order, order,
            start_to_close_timeout=timedelta(seconds=30),
        )
```

---

### 4. Key Insight

- **An `ActivityError` wraps the root cause** — inspect `.cause` to get the original exception.
- **Raising inside Workflow code (not an Activity) immediately fails the Workflow** — no retry. Only Activities are automatically retried. Use this intentionally when a workflow-level condition is unrecoverable.

---

---

## 14. Versioning

### →  Native (Patching API) +  Partial (Requires Code Discipline)

---

### 1. Explanation (ELI5)

When you want to change a Workflow that is currently running in production, you have a problem: if you change the code, old executions will replay using the new code and get confused. Temporal's patching (`workflow.patched()`) lets you say "if this workflow started before my change, take path A; if after, take path B" — both in the same codebase.

---

### 2. How Temporal Handles It

- `workflow.patched("patch-id")` returns `True` for new executions that know about the patch and `False` for old ones being replayed.
- `workflow.deprecate_patch("patch-id")` removes the old path once all pre-patch executions have completed.
- **Safe deployment order**: Deploy new code with `patched()` → wait for old executions to drain → deploy code with `deprecate_patch()` → wait → remove patching code.

---

### 3. Code Example

```python
from temporalio import workflow

@workflow.defn
class OrderWorkflow:
    @workflow.run
    async def run(self, order: OrderInput) -> str:

        # Old executions use the old path; new executions use the new path
        if workflow.patched("add-discount-step"):
            # NEW behaviour: apply discount first
            await workflow.execute_activity(
                apply_discount, order,
                start_to_close_timeout=timedelta(seconds=10),
            )

        result = await workflow.execute_activity(
            process_order, order,
            start_to_close_timeout=timedelta(seconds=30),
        )
        return result
```

---

### 4. Key Insight

- **Never change Workflow logic that old running executions will replay without using `patched()`.** This is the most common production mistake with Temporal — it causes `WorkflowTaskFailed` non-determinism errors.
- Patching is only needed when changing the **sequence of events** (adding/removing/reordering Activities, timers, signals). Changing Activity implementation code (inside the Activity function itself) requires no patching.

---

---

## 15. Resilience, Traceability, Reconstruction, Controllability

### →  Native (All Four)

---

### 1. Explanation (ELI5)

- **Resilience**: Workflows survive crashes, network failures, and server restarts automatically.
- **Traceability**: Every step is in the event history — you can see what ran, when, with what data, and what failed.
- **Reconstruction**: A crashed workflow resumes exactly where it left off by replaying its history.
- **Controllability**: You can pause, resume, cancel, send data into, or query any running workflow from outside at any time.

---

### 2. How Temporal Handles It

| Property | Mechanism |
|---|---|
| **Resilience** | Event history + automatic replay on Worker restart |
| **Traceability** | Immutable event log with full payload visibility |
| **Reconstruction** | Deterministic replay reconstructs exact state |
| **Controllability** | Signals (mutate state), Queries (read state), Updates (sync call+response), `cancel()`, `terminate()` |

---

### 3. Code Example

```python
# From any external process — full controllability
handle = client.get_workflow_handle("order-workflow-XD001")

# Read state without stopping the workflow
status = await handle.query(OrderWorkflow.get_status)

# Inject data / change direction
await handle.signal(OrderWorkflow.add_item, new_item)

# Synchronously call an activity and get result back
result = await handle.execute_update(OrderWorkflow.apply_discount,
                                      args=[DiscountInput(pct=10)])

# Graceful cancel (workflow can clean up)
await handle.cancel()

# Hard stop (immediate, no cleanup)
await handle.terminate(reason="Fraud detected")
```

---

### 4. Key Insight

- **Queries are read-only and synchronous** — they return immediately and never change workflow state. Use them freely for monitoring dashboards.
- **Cancellation is cooperative** — the Workflow receives a `CancelledError` and can run compensating Activities before finishing. Termination is hard-kill with no cleanup window.

---

---

## 16. Batch Execution

### →  Partial (Design Pattern Required)

---

### 1. Explanation (ELI5)

Temporal doesn't have a "run this over 10,000 records" button, but you build batch processing as Workflows that iterate over a list, spawn parallel child workflows per item, and collate results. You get durability and progress tracking for free.

---

### 2. How Temporal Handles It

- **Fan-out**: A parent Workflow starts one child Workflow (or Activity) per batch item using `asyncio.gather` or `start_child_workflow`.
- **Signal-fed batches**: A long-running Workflow receives item IDs via signals, launches an Activity per item in parallel with `start_activity`, and tracks handles.
- **`continue_as_new`**: For very large batches (>thousands of items), break the batch into chunks and restart with `continue_as_new` to keep history size manageable.
- Temporal Schedules drive periodic batch jobs (nightly, hourly).

---

### 3. Code Example

```python
@workflow.defn
class BatchProcessorWorkflow:
    def __init__(self) -> None:
        self._item_queue: list[int] = []
        self._done = False
        self._handles: list = []

    @workflow.signal
    def add_item(self, item_id: int) -> None:
        self._item_queue.append(item_id)

    @workflow.signal
    def finish(self) -> None:
        self._done = True

    @workflow.run
    async def run(self) -> list[str]:
        while not self._done:
            while self._item_queue:
                item_id = self._item_queue.pop(0)
                handle = workflow.start_activity(
                    process_item, item_id,
                    start_to_close_timeout=timedelta(minutes=5),
                    heartbeat_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=2),
                        backoff_coefficient=2.0,
                        maximum_attempts=5,
                    ),
                )
                self._handles.append(handle)
            await workflow.sleep(timedelta(seconds=1))

        results = await asyncio.gather(*self._handles, return_exceptions=True)
        return [str(r) for r in results]
```

---

### 4. Key Insight

- **Temporal is not a batch framework like Spark or Flink.** It excels at durable orchestration of heterogeneous steps where individual items may need retries, human intervention, or downstream API calls — not raw number-crunching over millions of rows.
- Use `continue_as_new` for truly massive batches to avoid the ~50k event history ceiling.

---

---

## 17. Real-time Execution

### →  Partial (Sub-second Latency Requires Design Attention)

---

### 1. Explanation (ELI5)

Temporal can handle near-real-time use cases (response in 1–2 seconds), but there is inherent latency from the task queue dispatch round-trip. It is not designed for sub-millisecond, high-frequency trading, or streaming scenarios — but for business workflows that need "fast and reliable," it works well.

---

### 2. How Temporal Handles It

- **Latency sources**: Client → Cluster (gRPC) → Task Queue → Worker → Activity → back. Typical round-trip in a well-tuned setup is 50–200ms for a simple Activity.
- **Updates** provide a tighter synchronous loop: caller gets a result back without polling once the Activity completes.
- **Local Activities** (`workflow.execute_local_activity`) run directly on the Worker without a round-trip to the cluster — useful for very fast, low-latency in-process operations.
- Workers on the same machine as the cluster, or Temporal Cloud with low-latency regions, reduce dispatch overhead.

---

### 3. Code Example

```python
from temporalio import workflow

@workflow.defn
class RealTimeCheckWorkflow:
    @workflow.update
    async def check_inventory(self, sku: str) -> bool:
        """Caller gets a synchronous response — no polling needed."""
        in_stock = await workflow.execute_local_activity(
            check_stock_cache,  # Fast in-process cache check
            sku,
            schedule_to_close_timeout=timedelta(seconds=2),
        )
        return in_stock

    @workflow.run
    async def run(self) -> None:
        # Keep workflow alive to serve update requests
        await workflow.wait_condition(lambda: False,
                                      timeout=timedelta(hours=1))
```

---

### 4. Key Insight

- **Temporal is optimised for reliability and correctness over raw speed.** For sub-100ms SLAs with millions of requests per second, use a cache or a dedicated low-latency service and have Temporal orchestrate the durable parts of the flow.
- **Local Activities bypass task queue dispatch** but lose independent retry scope — they're good for read-only cache checks or CPU-bound transforms, not for calls to external services.

---

---

## 🔹 Final Summary

### What Temporal Does Best

| Capability | Quality |
|---|---|
| Long-running, multi-step business processes | ⭐⭐⭐⭐⭐ |
| Automatic retry without code | ⭐⭐⭐⭐⭐ |
| State management without a separate DB | ⭐⭐⭐⭐⭐ |
| Distributed saga / compensation | ⭐⭐⭐⭐⭐ |
| Human-in-the-loop workflows | ⭐⭐⭐⭐⭐ |
| Event history audit trail | ⭐⭐⭐⭐⭐ |
| Parallel + sequential orchestration | ⭐⭐⭐⭐⭐ |
| Testing (time skipping, mocking) | ⭐⭐⭐⭐⭐ |

### What Temporal Does NOT Replace

| System | Why |
|---|---|
| **Message queues** (Kafka, RabbitMQ) | High-throughput, fire-and-forget event streaming |
| **Databases** | Long-term domain data storage and complex ad-hoc queries |
| **Stream processors** (Flink, Spark) | Sub-millisecond, stateless, per-record transformations at scale |
| **API gateways** | Request routing, auth, rate limiting |
| **Schedulers** (cron) | Simple time-based triggers without stateful orchestration |
| **Monitoring systems** (Datadog, Prometheus) | Metrics aggregation, alerting, dashboards |

---

## 🔹 One-line Explanation

> **Temporal makes your code durable** — if a server crashes in the middle of your business process, Temporal picks up from exactly where it left off, without you writing a single line of retry, state recovery, or distributed transaction logic.
