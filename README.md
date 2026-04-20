# Temporal Python SDK — Learning Repository

> Personal learning repo covering **Temporal 101** and **Temporal 102** courses (Python). Covers core concepts, architecture, durable execution, testing, debugging, and hands-on exercises using the Temporal Python SDK.

---

## Index

### Temporal 101
- [What is Temporal?](#what-is-temporal)
- [Core Concepts](#core-concepts) — Workflow, Activity, Worker, Task Queue
- [Architecture](#architecture-simple)
- [Local Setup](#local-setup)
- [Running a Workflow](#running-a-workflow)
- [Temporal CLI Cheatsheet](#temporal-cli-cheatsheet)
- [Web UI](#web-ui)
- [Input/Output Rules](#inputoutput-rules)
- [Activity Retry Policy](#activity-retry-policy)
- [Async vs Sync Activities](#async-vs-sync-activities)
- [Executing Activities — Function vs Method](#executing-activities--function-vs-method)
- [Sandbox Import Pattern](#sandbox-import-pattern-python-specific)
- [Custom Retry Policy](#custom-retry-policy)
- [Deployment Options](#deployment-options)
- [Integrating with a Web/Mobile App](#integrating-temporal-with-a-webmobile-app)
- [Key Development Rules](#key-development-rules)
- [Versioning](#versioning-brief)
- [Repo Structure](#repo-structure)
- [Course Coverage (101)](#course-coverage-temporal-101)
- [Hands-On Exercises (101)](#hands-on-exercises-temporal-101)
  - [Exercise 1 — Hello Workflow](#exercise-1--hello-workflow-exerciseshello-workflow)
  - [Exercise 2 — Hello Web UI](#exercise-2--hello-web-ui-exerciseshello-web-ui)
  - [Exercise 3 — Farewell Workflow](#exercise-3--farewell-workflow-exercisesfarewell-workflow)
  - [Exercise 4 — Finale Workflow](#exercise-4--finale-workflow-exercisesfinale-workflow)
  - [Custom Task — Greet User](#custom-task--greet-user-tasksgreet-user)

### Temporal 102
- [What's New in 102](#whats-new-in-102)
- [Local Dev Server — 102 Specific Command](#local-dev-server--102-specific-command)
- [Durable Execution — How It Actually Works](#durable-execution--how-it-actually-works)
- [Logging in Workflows and Activities](#logging-in-workflows-and-activities)
- [Timers in Workflows](#timers-in-workflows)
- [Testing](#testing)
  - [Testing an Activity](#testing-an-activity)
  - [Testing a Workflow](#testing-a-workflow)
  - [Time-Skipping](#time-skipping)
  - [Mocking Activities](#mocking-activities-in-workflow-tests)
- [Debugging with Web UI](#debugging-with-web-ui)
- [Hands-On Exercises (102)](#hands-on-exercises-temporal-102)
  - [Exercise 1 — Durable Execution](#exercise-1--observing-durable-execution-exercisesdurable-execution)
  - [Exercise 2 — Testing](#exercise-2--testing-the-translation-workflow-exercisestesting-code)
  - [Exercise 3 — Debug Activity](#exercise-3--debugging-an-activity-failure-exercisesdebug-activity)
- [Course Coverage (102)](#102-course-coverage)

### Zigflow (Declarative YAML Workflows on Temporal)
- [What is Zigflow?](#what-is-zigflow)
- [Zigflow vs Python SDK](#zigflow-vs-python-sdk)
- [Zigflow DSL Structure](#zigflow-dsl-structure)
- [Task Types](#task-types)
- [Running a Zigflow Workflow](#running-a-zigflow-workflow)
- [Repo Examples](#repo-examples)
- [Cheatsheet Files](#cheatsheet-files)

---

## What is Temporal?

**Temporal is a platform that guarantees your code runs to completion — even if servers crash, networks fail, or your app restarts.**

Think of it like this: you write your business logic as normal Python code, and Temporal makes sure it executes reliably from start to finish, no matter what goes wrong in between. You don't write retry logic, failure recovery, or state management — Temporal handles all of that.

**Real-world examples of workflows Temporal is built for:**
- Processing an expense report (multi-step, multi-person, long-running)
- Transferring money between bank accounts (must complete both steps, exactly once)
- E-commerce order fulfillment, subscription management, booking systems

---

## Core Concepts

### Workflow
A **Workflow** is a durable sequence of steps written as Python code. It defines your business process. Key rules:
- Must be **deterministic** — same input always produces same output
- Cannot interact directly with the outside world (no HTTP calls, DB queries, file I/O) — use Activities for that
- Can run for **years** and survive crashes/restarts automatically

```python
from temporalio import workflow
from datetime import timedelta

@workflow.defn
class GreetSomeone:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            say_hello, name, start_to_close_timeout=timedelta(seconds=5)
        )
```

### Activity
An **Activity** is a single step that does the real work — things that can fail (HTTP requests, DB calls, file I/O). Activities are:
- **Automatically retried** on failure (configurable)
- Not required to be deterministic
- Kept separate from Workflow code

```python
from temporalio import activity

@activity.defn
async def say_hello(name: str) -> str:
    return f"Hello, {name}!"
```

### Worker
A **Worker** is your application process that polls Temporal for tasks and executes your Workflow and Activity code. You configure and run it yourself.

```python
worker = Worker(client, task_queue="greeting-tasks", workflows=[GreetSomeone], activities=[say_hello])
await worker.run()
```

### Task Queue
A named channel that the Temporal Cluster uses to route work to Workers. Worker and Workflow start must use the **same task queue name** (case-sensitive).

### Workflow Execution
A single run of a Workflow Definition. Has a unique **Workflow ID** (user-defined, business-meaningful) and a **Run ID** (auto-assigned UUID).

---

## Architecture (Simple)

```
Your App (Worker)  <-->  Temporal Cluster (Server + DB)  <-->  Temporal Client / CLI / Web UI
```

- **Temporal Cluster** = Frontend Service + Backend Services + Database (Postgres/Cassandra/MySQL). Tracks state and event history of every execution. Does NOT run your code.
- **Worker** = Your process. Runs your code. Polls the cluster for tasks.
- **Client** = Used to start workflows, query status, send signals. Embedded in your app or used via CLI/Web UI.
- Communication uses **gRPC + Protocol Buffers**, optionally secured with TLS.
- Port: `7233` (default frontend)

---

## Local Setup

### Prerequisites
- Python 3.8+
- [Temporal CLI](https://docs.temporal.io/cli)

### Install

```bash
# Clone the repo
git clone https://github.com/your-username/Temporal-Python-SDK.git
cd Temporal-Python-SDK

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Start Local Temporal Server

```bash
temporal server start-dev
```

This starts a lightweight dev server (no Docker needed). Web UI available at: `http://localhost:8233`

---

## Running a Workflow

### Step 1 — Start the Worker
```bash
python3 worker.py
# Output: Worker Started...
```

### Step 2 — Start a Workflow (from code)
```bash
python3 starter_or_client.py
```

### Step 2 (alternative) — Start via CLI
```bash
temporal workflow start \
  --type GreetSomeone \
  --task-queue greeting-tasks \
  --workflow-id my-first-workflow \
  --input '"Mason"'
```

### Check Result via CLI
```bash
temporal workflow show --workflow-id my-first-workflow
```

---

## Temporal CLI Cheatsheet

| Command | Description |
|---|---|
| `temporal server start-dev` | Start local dev server |
| `temporal workflow start --type ... --task-queue ... --workflow-id ... --input ...` | Start a workflow |
| `temporal workflow show --workflow-id ...` | Show result and event history |
| `temporal workflow show --workflow-id ... --detailed` | Full event history with details |
| `temporal workflow list` | List recent workflow executions |
| `temporal workflow cancel --workflow-id ...` | Cancel a running workflow |

---

## Web UI

Access at `http://localhost:8233` when the dev server is running.

- Browse all Workflow Executions (running, completed, failed)
- View full Event History for any execution
- See input, output, status, timing
- Advanced search/filter with Elasticsearch (optional, not needed for dev)

---

## Input/Output Rules

- All input parameters and return values must be **JSON-serializable**
- Allowed: `str`, `int`, `float`, `bool`, `list`, `dict`, `dataclass`
- Not allowed: `datetime`, functions, coroutines, non-serializable objects
- Temporal recommends using a **single dataclass** as input (easier to evolve without breaking running workflows)
- Avoid passing large data (files, images) — pass paths/URLs instead

---

## Activity Retry Policy

Temporal automatically retries failed activities. Default behavior:

| Property | Default |
|---|---|
| `initial_interval` | 1 second |
| `backoff_coefficient` | 2.0 (doubles each retry) |
| `maximum_interval` | 100× initial |
| `maximum_attempts` | Unlimited |

Customize via `RetryPolicy` when calling `execute_activity`.

---

## Async vs Sync Activities

| Type | When to use |
|---|---|
| `async def` | All I/O is async-safe (e.g., `aiohttp`, `httpx`) |
| Sync (thread) | Uses blocking libraries (e.g., `requests`) — pass `activity_executor=ThreadPoolExecutor` to Worker |

> Never make blocking calls (e.g., `requests.get()`) inside an `async` activity — it blocks the entire event loop.

---

## Executing Activities — Function vs Method

Use **`execute_activity`** when the activity is a plain function:
```python
result = await workflow.execute_activity(
    say_hello, name, start_to_close_timeout=timedelta(seconds=5)
)
```

Use **`execute_activity_method`** when the activity is a method on a class:
```python
result = await workflow.execute_activity_method(
    TranslateActivities.greet_in_spanish, name, start_to_close_timeout=timedelta(seconds=5)
)
```

For non-blocking dispatch (fire and retrieve later), use `start_activity_method` which returns a handle:
```python
handle = workflow.start_activity_method(
    TranslateActivities.greet_in_spanish, name, start_to_close_timeout=timedelta(seconds=5)
)
result = await handle  # await whenever you're ready
```

---

## Sandbox Import Pattern (Python-Specific)

Workflow files are **reloaded in a sandbox on every execution**. To avoid reloading third-party imports each time, mark them as pass-through:

```python
from temporalio import workflow

# Standard library and temporalio imports are passed through automatically.
# For everything else (activities, third-party libs), do this:
with workflow.unsafe.imports_passed_through():
    from translate import TranslateActivities
```

Keep Workflow files as small as possible — only the workflow class, not activities or shared types.

---

## Custom Retry Policy

```python
from datetime import timedelta
from temporalio.common import RetryPolicy

result = await workflow.execute_activity_method(
    TranslateActivities.greet_in_spanish,
    name,
    start_to_close_timeout=timedelta(seconds=10),
    retry_policy=RetryPolicy(
        initial_interval=timedelta(seconds=1),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(seconds=30),
        maximum_attempts=5,
    ),
)
```

---

## Deployment Options

| Option | Description |
|---|---|
| `temporal server start-dev` | Local single-process dev server. No external deps. |
| Docker Compose | Full local cluster with DB, good for integration testing |
| Kubernetes | Production self-hosted deployment |
| **Temporal Cloud** | Fully managed SaaS by Temporal. 99.9% uptime, SOC2, consumption-based pricing. You still run your own Workers. |

> Regardless of deployment option — **your code always runs on your own servers**. Temporal never executes or accesses your code.

---

## Integrating Temporal with a Web/Mobile App

The typical pattern is to go through a backend service, not call Temporal directly from the frontend:

```
User (browser/app) → REST API (your backend) → Temporal Client → Temporal Cluster → Worker
```

The backend extracts data from the HTTP request and calls `client.execute_workflow(...)` or `client.start_workflow(...)`. This is also better for security — the Temporal cluster only needs to accept connections from your backend, not from every end user.

---

## Key Development Rules

1. **Workflow code must be deterministic** — no random numbers, no `datetime.now()`, no direct I/O
2. All non-deterministic work goes in **Activities**
3. Use `await` when calling `workflow.execute_activity(...)` — forgetting it returns a coroutine, not the result
4. Timeouts must be `timedelta` objects, not plain integers
5. Task queue names must **exactly match** between Worker and workflow start call
6. Restart the Worker after code changes (Python SDK sandbox helps, but restart is safest)

---

## Versioning (Brief)

If a Workflow is already running and you need to change its logic, use **Versioning** so:
- Old executions continue with the original code path
- New executions use the updated code

Covered in depth in the separate Temporal Versioning course.

---

## Repo Structure

```
Tasks/
  Greet-User/           # Custom hands-on task: greet a user via workflow + activity
Resources/
  temporal_101/
    demos/              # Demo workflows (service-workflow, writing-a-workflow-definition)
    exercises/          # Course exercises (hello-workflow, farewell-workflow, finale-workflow)
    samples/            # Sample code (greeting, retry-policy)
  temporal_102/
    exercises/          # Advanced exercises (debug-activity, durable-execution, testing-code)
    samples/            # Dataclass I/O, age estimation
Tutorial/
  learn_temporal_tutorial/   # Structured tutorial with activities/workers/workflows split
  failing_activity_tutorial/ # Demonstrates activity failure and retry
```

---

## Course Coverage (Temporal 101)

| Chapter | Topic |
|---|---|
| 1–3 | What is Temporal, architecture, setup |
| 4 | Writing Workflow Definitions, running from CLI and code |
| 5 | Event History, Web UI, `temporal workflow show` |
| 6 | Making code changes, Worker restart |
| 7 | Activities — what they are, async vs sync, registering |
| 8 | Activity failure, retry policies, timeouts |

---

## Hands-On Exercises (Temporal 101)

### Exercise 1 — Hello Workflow (`exercises/hello-workflow/`)
- Review the provided Workflow Definition (`greeting.py`) — understand its input, logic, and return value
- Set the task queue name (`greeting-tasks`) in `worker.py`
- Start the Worker: `python worker.py`
- Start the Workflow from the CLI:
  ```bash
  temporal workflow start --type GreetSomeone --task-queue greeting-tasks --workflow-id my-first-workflow --input '"Mason"'
  ```
- Retrieve the result: `temporal workflow show --workflow-id my-first-workflow`

### Exercise 2 — Hello Web UI (`exercises/hello-web-ui/`)
- Open the Temporal Web UI (`http://localhost:8233`)
- Find the Workflow Execution from Exercise 1
- Locate on the detail page:
  - Task queue name, start time, close time
  - Input and output values (under `</> Input and Results`)

### Exercise 3 — Farewell Workflow (`exercises/farewell-workflow/`)
- Write a new `farewell_in_spanish` Activity method in `translate.py` by copying `greet_in_spanish` and changing the service stem to `get-spanish-farewell`
- Register the new Activity on the Worker in `worker.py`
- Modify `greeting.py` to call both activities and return `f"{greeting}\n{farewell}"`
- Start the microservice: `python microservice.py`
- Run the Workflow: `python starter.py YourName`
- **Bonus experiment:** Stop the microservice mid-run and observe automatic retries in the Web UI. Restart it — the Workflow completes on the next retry.

### Exercise 4 — Finale Workflow (`exercises/finale-workflow/`)
- Demonstrates **cross-language Temporal**: Workflow in Python, Activity in Java
- The Java Activity uses a Java graphics library to generate a PDF course completion certificate
- Run the Java Activity Worker:
  ```bash
  java -classpath java-activity-and-worker-1.1.jar io.temporal.training.PdfCertWorker
  ```
- Run the Python Workflow Worker: `python worker.py`
- Start the Workflow: `python starter.py "Your Full Name"`
- Download the generated `101_certificate_your_name.pdf` — your course completion certificate

### Custom Task — Greet User (`Tasks/Greet-User/`)
- Self-directed task built outside the course exercises
- Implements: `Greeting_worflow.py`, `greet_activity.py`, `worker.py`, `starter_or_client.py`
- Bugs encountered and fixed:
  - Missing `await` on `execute_activity` → `TypeError: coroutine is not JSON serializable`
  - `schedule_to_close_timeout=10` (int) → must be `timedelta(seconds=10)`

---
---

# Temporal 102 — Durable Execution, Testing & Debugging

> Builds on 101. Digs into *how* Temporal's durable execution actually works, how to write tests, and how to debug real activity failures.

---

## What's New in 102

| Topic | What you learn |
|---|---|
| Durable Execution | How Temporal reconstructs state after a crash using Event History |
| Logging | Adding structured logs to Workflows and Activities |
| Timers | `asyncio.sleep()` inside Workflows — durable, not just a delay |
| Testing | Unit-testing Activities and Workflows with the Temporal test environment |
| Time-skipping | Test environment skips past timers instantly |
| Debugging | Using Web UI Event History to diagnose real bugs |
| Sticky Execution | How Workers cache Workflow state for performance |

---

## Local Dev Server — 102 Specific Command

102 exercises use a **persistent DB file** so you can observe crash/recovery:

```bash
temporal server start-dev --ui-port 8080 --db-filename clusterdata.db
```

The `--db-filename` flag makes the dev server persist state across restarts (normally it's in-memory and resets). This is essential for the durable execution exercise.

---

## Durable Execution — How It Actually Works

When a Workflow runs, Temporal records every event (activity scheduled, activity completed, timer fired, etc.) into an **Event History** stored in its database.

If a Worker crashes mid-execution:
1. The Temporal Cluster detects the crash via heartbeat timeout
2. It reschedules the remaining work to another available Worker
3. The new Worker **replays** the Event History to reconstruct state — re-running Workflow code up to the point of failure, but **skipping already-completed Activities** (their results are replayed from history, not re-executed)
4. Execution continues from exactly where it left off

This is why Workflow code must be **deterministic** — replaying the same history must produce the same sequence of commands.

```
Event History (stored in DB):
  WorkflowExecutionStarted
  ActivityTaskScheduled    → say_hello
  ActivityTaskCompleted    → "Hello, Stanislav"   ← replayed, not re-run
  TimerStarted             → 10s
  TimerFired               ← replayed
  ActivityTaskScheduled    → say_goodbye          ← resumes here after crash
  ActivityTaskCompleted    → "Goodbye, Stanislav"
  WorkflowExecutionCompleted
```

---

## Logging in Workflows and Activities

Use `workflow.logger` inside Workflows and `activity.logger` inside Activities (not Python's standard `logging` directly in Workflow code — it's not replay-safe):

```python
# In a Workflow
@workflow.defn
class TranslationWorkflow:
    @workflow.run
    async def run(self, input: WorkflowInput) -> str:
        workflow.logger.info("Workflow started", extra={"input": input})
        result = await workflow.execute_activity_method(...)
        return result
```

```python
# In an Activity
@activity.defn
async def translate_term(self, input: ActivityInput) -> str:
    activity.logger.info("Activity started", extra={"term": input.term})
    # ... do work
    activity.logger.debug("Translation successful", extra={"result": result})
    return result
```

Configure log level in `worker.py`:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

---

## Timers in Workflows

Use `await asyncio.sleep(seconds)` inside a Workflow to create a **durable timer**. Unlike a normal `sleep`, if the Worker crashes during the wait, Temporal will restore and continue once the timer fires — the delay is tracked by the Cluster, not the Worker.

```python
import asyncio
from temporalio import workflow

@workflow.defn
class TranslationWorkflow:
    @workflow.run
    async def run(self, input):
        hello = await workflow.execute_activity_method(...)
        workflow.logger.info("Sleeping between translation calls")
        await asyncio.sleep(10)   # durable 10-second timer
        goodbye = await workflow.execute_activity_method(...)
        return f"{hello}\n{goodbye}"
```

---

## Testing

### Testing an Activity

Use `ActivityEnvironment` from the Temporal test SDK to run an Activity in isolation:

```python
import pytest
from temporalio.testing import ActivityEnvironment
from activities import TranslationActivities
from shared import TranslationActivityInput

@pytest.mark.asyncio
async def test_translate_hello_to_german():
    async with aiohttp.ClientSession() as session:
        env = ActivityEnvironment()
        activities = TranslationActivities(session)
        input = TranslationActivityInput(term="Hello", language_code="de")
        result = await env.run(activities.translate_term, input)
    assert result.translation == "Hallo"
```

Use `pytest.mark.parametrize` to test multiple inputs without repeating test code.

Test for expected failures too:
```python
@pytest.mark.asyncio
async def test_bad_language_code():
    with pytest.raises(Exception) as e:
        input = TranslationActivityInput("goodbye", "xq")
        async with aiohttp.ClientSession() as session:
            env = ActivityEnvironment()
            activities = TranslationActivities(session)
            await env.run(activities.translate_term, input)
    assert "Invalid language code" in str(e)
```

### Testing a Workflow

Use `WorkflowEnvironment` to test an entire Workflow end-to-end, including real activity execution:

```python
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

@pytest.mark.asyncio
async def test_translation_workflow():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with aiohttp.ClientSession() as session:
            activities = TranslationActivities(session)
            async with Worker(env.client, task_queue="...", workflows=[TranslationWorkflow], activities=[activities.translate_term]):
                result = await env.client.execute_workflow(
                    TranslationWorkflow.run,
                    WorkflowInput(name="Pierre", language_code="fr"),
                    id="test-workflow", task_queue="..."
                )
        assert result.hello_message == "Bonjour, Pierre"
        assert result.goodbye_message == "Au revoir, Pierre"
```

### Time-Skipping

`WorkflowEnvironment.start_time_skipping()` creates a test environment that **automatically fast-forwards past any timers** in the Workflow. A Workflow with `await asyncio.sleep(15)` still completes in milliseconds in tests.

### Mocking Activities in Workflow Tests

To test a Workflow in isolation from the real Activity implementation, use a mock:

```python
@activity.defn(name="translate_term")   # same name as the real activity
async def translate_term_mocked_french(input: TranslationActivityInput):
    if input.term == "hello":
        return TranslationActivityOutput("Bonjour")
    else:
        return TranslationActivityOutput("Au revoir")
```

Register the mock in the Worker instead of the real activity. The Workflow won't know the difference.

---

## Debugging with Web UI

The Web UI Event History is your primary debugging tool. For any Workflow Execution you can see:

- **Sticky execution** — whether the same Worker handled consecutive Workflow Tasks (look at `WorkflowTaskScheduled` events)
- **Activity inputs/outputs** — expand `ActivityTaskScheduled` / `ActivityTaskCompleted` events
- **Which Worker ran what** — each event shows the Worker identity
- **Retry attempts** — each retry shows as a new `ActivityTaskScheduled` event with `attempt: N`
- **Retry Policy details** — visible in the `ActivityTaskScheduled` event (max interval, timeout, etc.)
- **Timer durations** — shown in `TimerStarted` events as a timeout value

**Compact view** — summarizes activities and timers in a clean table, great for quick overview.
**Expand All** — shows all events correlated by activity, helpful for seeing the full lifecycle of each task.

---

## Hands-On Exercises (Temporal 102)

### Exercise 1 — Observing Durable Execution (`exercises/durable-execution/`)

**What you build:** A Translation Workflow that calls two activities (hello + goodbye) with a 10-second timer between them, plus structured logging throughout.

**Steps:**
1. Add `workflow.logger` calls to Workflow and `activity.logger` calls to Activities
2. Set log level to `INFO` in `worker.py`
3. Add `await asyncio.sleep(10)` timer between the two activity calls
4. Start **two Workers** simultaneously
5. Start the Workflow, watch which Worker picks it up
6. When you see the timer log, **kill that Worker with Ctrl-C**
7. Observe the second Worker resume and complete the Workflow

**Key insight:** The microservice logs show that the first Activity (`say_hello`) ran only **once** — the completed activity was replayed from history, not re-executed on the new Worker.

---

### Exercise 2 — Testing the Translation Workflow (`exercises/testing-code/`)

**What you build:** A test suite using `pytest` and Temporal's test SDK.

**Steps:**
1. Run the provided `test_activities.py` — a passing test for `translate_term("Hello" → German)`
2. Add a second parametrized test case: `translate_term("Goodbye" → Latvian)` → `"Ardievu"`
3. Add a test for invalid input (bad language code) — assert exception contains `"Invalid language code"`
4. Write assertions in `test_workflow.py`:
   - `result.hello_message == "Bonjour, Pierre"`
   - `result.goodbye_message == "Au revoir, Pierre"`
5. Run tests — they will **fail** due to a bug in the Workflow Definition
6. Find and fix the bug
7. Run again — all tests pass; timer is skipped automatically by the test environment
8. *(Optional)* Swap real activities for mock activities and re-run

---

### Exercise 3 — Debugging an Activity Failure (`exercises/debug-activity/`)

**What you build:** You diagnose and fix a latent bug in a pizza-order Workflow using Web UI + tests.

**Part A–B: Run and interpret the Workflow**
1. Start two Workers, run `python starter.py` — $27 pizza order completes successfully
2. Use Web UI Event History to answer:
   - Which Worker ran which Activity? (check `ActivityTaskStarted` identity field)
   - Timer duration between activities? (check `TimerStarted` timeout)
   - Input/output for `get_distance`? (expand `ActivityTaskScheduled` / `ActivityTaskCompleted`)
   - Retry Policy max interval and timeout for `send_bill`?
   - Practice Compact view and Expand All

**Part C: Trigger the bug**
1. Edit `shared.py` — add `pizza3` with description `"Medium, with extra cheese"` and price `1300` ($13). Add to `pizza_list`
2. Total is now $41 — triggers the `>$30` discount logic
3. Restart Workers, re-run — Workflow gets stuck, never completes
4. Open Web UI → **Pending Activities** tab → read the error: `invalid charge amount: -500`

**Part D: Write a test and fix the bug**
1. In `tests/`, update the test case: set `amount` to `6500` ($65, qualifies for discount), expected result to `6000` ($65 − $5 discount)
2. Run `python -m pytest` — test fails (confirms bug)
3. Open `activities.py` → find the bug in `send_bill`:
   ```python
   charge_amount = -500    # BUG: sets to -500 instead of subtracting $5
   charge_amount -= 500    # FIX: subtract the $5 discount
   ```
4. Fix the line, run `python -m pytest` — test passes

**Part E: Deploy and verify the fix**
1. Ctrl-C both Workers (cache must clear for new code to take effect)
2. Restart both Workers: `python worker.py`
3. Web UI → **History** tab → enable **Auto refresh**
4. `send_bill` retries automatically (max interval: 10s) — Workflow status changes from **Running** → **Completed**

**Key insights:**
- Web UI **Pending Activities** tab is the fastest way to see failure details and retry count
- Activity code can be fixed and redeployed without risk of non-determinism (unlike Workflow code)
- In-flight Workflow Executions recover automatically on the next Activity retry after a fix is deployed

---

## 102 Course Coverage

| Chapter | Topic |
|---|---|
| 1–2 | Durable execution model, Event History replay |
| 3 | Logging in Workflows and Activities |
| 4 | Timers — `asyncio.sleep()` as a durable delay |
| 5–6 | Testing Activities and Workflows with `pytest` + Temporal test SDK |
| 7 | Time-skipping in tests, mock activities |
| 8 | Debugging with Web UI Event History |
| 9 | Sticky execution, Worker caching |

---
---

# Zigflow — Declarative Workflow Engine on Temporal

> Zigflow lets you define Temporal workflows in **YAML** instead of Python code. Built on the [CNCF Serverless Workflow DSL v1.0.0](https://github.com/serverlessworkflow/specification). No Python required for the workflow orchestration layer — just describe what to do, and Zigflow compiles it into a Temporal Workflow.

---

## Index (Zigflow)

- [What is Zigflow?](#what-is-zigflow)
- [Zigflow vs Python SDK](#zigflow-vs-python-sdk)
- [Architecture](#zigflow-architecture)
- [Local Setup](#zigflow-local-setup)
- [Zigflow DSL Structure](#zigflow-dsl-structure)
- [Task Types](#task-types)
- [Runtime Expressions](#runtime-expressions)
- [Running a Zigflow Workflow](#running-a-zigflow-workflow)
- [Zigflow CLI Cheatsheet](#zigflow-cli-cheatsheet-1)
- [Repo Examples](#repo-examples)
- [Key Rules](#zigflow-key-rules)
- [Repo Structure (Zigflow)](#repo-structure-zigflow)
- [Cheatsheet Files](#cheatsheet-files)

---

## What is Zigflow?

**Zigflow is a declarative workflow engine** that sits on top of Temporal. Instead of writing Python classes, you describe the workflow in a YAML file.

```
YAML → Validation → Compilation → Temporal Workflow → Execution
```

| Component | Role |
|---|---|
| YAML file | Single source of truth for workflow behavior |
| Zigflow Worker | Compiles YAML → Temporal workflow; polls the Task Queue |
| Temporal Server | Orchestrates scheduling, retries, history, timers |
| Temporal CLI | Triggers workflow execution and sends signals |

> **Key rule:** Zigflow does NOT self-trigger workflows. After `zigflow run -f workflow.yaml` starts the worker, you trigger execution with `temporal workflow start`.

---

## Zigflow vs Python SDK

| Use Zigflow YAML when… | Use Python SDK when… |
|---|---|
| Workflow is mostly orchestration (call → wait → call) | Workflow has complex business logic in Python |
| Team prefers declarative config | You need type-safe dataclasses and IDE completion |
| Rapid prototyping of integration flows | You need fine-grained control over retry/heartbeat |
| Non-Python teams need to read/write workflows | Activities use Python libraries heavily |

---

## Zigflow Architecture

```
Your YAML File  →  Zigflow Worker  →  Temporal Cluster  →  Temporal Worker (Activities)
```

- **Zigflow Worker** — reads your YAML, compiles it, and polls the Temporal Task Queue. Each `call` task becomes a Temporal Activity.
- **Temporal Cluster** — same dev server you already use. No extra infra needed.
- **Temporal CLI** — used to trigger, signal, query, and inspect Zigflow-driven workflows exactly the same way as Python-SDK workflows.

---

## Zigflow Local Setup

### Prerequisites
- Temporal CLI + dev server already running (`temporal server start-dev`)
- `zigflow` CLI installed

### Install Zigflow CLI

```bash
# Homebrew (macOS / Linux)
brew install zigflow

# Or via npm
npm install -g @zigflow/cli

# Verify
zigflow version
```

### Activate repo virtual env

```bash
source .venv/bin/activate
```

---

## Zigflow DSL Structure

Every Zigflow YAML file has two required top-level keys:

```yaml
document:
  dsl: "1.0.0"           # always "1.0.0"
  taskQueue: my-queue    # must match the Zigflow worker's task queue (case-sensitive)
  workflowType: my-wf    # must match the Temporal workflow type (case-sensitive)
  version: "1.0.0"       # your workflow's semantic version
  metadata:              # optional — sets default timeouts for all tasks
    activityOptions:
      startToCloseTimeout:
        minutes: 5

do:                      # ordered list of named tasks
  - taskName:
      <task-definition>
  - anotherTask:
      <task-definition>
```

### document Field Reference

| Field | Required | Notes |
|---|---|---|
| `dsl` | yes | Always `"1.0.0"` |
| `taskQueue` | yes | Temporal Task Queue — case-sensitive, must match `zigflow run` config |
| `workflowType` | yes | Temporal Workflow Type registered by Zigflow worker |
| `version` | yes | Semantic version of the workflow definition |
| `metadata.activityOptions` | no | Default timeouts for all `call`/`run` tasks |

---

## Task Types

| Task | What it does |
|---|---|
| `set` | Assign variables in workflow data |
| `call` | Invoke HTTP / OpenAPI / gRPC / AsyncAPI endpoint |
| `do` | Run subtasks sequentially as a group |
| `fork` | Run branches in parallel (`compete: false` = all, `compete: true` = race) |
| `for` | Loop over a collection |
| `listen` | Wait for an external event / Temporal signal |
| `raise` | Throw an error to fault the workflow |
| `run` | Execute container / shell / script / sub-workflow |
| `switch` | Conditional branching |
| `try` | Error handling with optional retry |
| `wait` | Pause for a duration (durable timer — survives Worker crash) |

### Task Execution Model

| Task type | Runs as | Deterministic? |
|---|---|---|
| `set`, `switch` | Temporal Workflow code | Must be deterministic |
| `call`, `run` | Temporal Activity | Can do I/O; retried on failure |
| `wait` | Temporal Timer | Durable — survives Worker crash |
| `listen` | Temporal Signal handler | Durable — survives Worker crash |
| `fork` | Workflow code + parallel Activities | Branches run concurrently |

### Common Patterns

```yaml
# HTTP call
- fetchUser:
    call: http
    with:
      method: get
      endpoint: https://api.example.com/users/1
    output:
      as:
        user: ${ . }

# Parallel — all branches run, output = array
- gatherAll:
    fork:
      compete: false
      branches:
        - fetchA:
            call: http
            with: { method: get, endpoint: https://api.example.com/a }
        - fetchB:
            call: http
            with: { method: get, endpoint: https://api.example.com/b }

# Race — first branch wins
- fastest:
    fork:
      compete: true
      branches:
        - primary:
            call: http
            with: { method: get, endpoint: https://primary.example.com/data }
        - fallback:
            call: http
            with: { method: get, endpoint: https://fallback.example.com/data }

# Wait for human approval (Temporal signal)
- waitApproval:
    listen:
      to:
        one:
          with:
            id: approve        # matches: temporal workflow signal --name approve
            type: signal

# Durable timer
- pause:
    wait:
      minutes: 10

# Error handling with retry
- safeCall:
    try:
      - fetch:
          call: http
          with:
            method: get
            endpoint: https://unstable.example.com/data
    catch:
      retry:
        delay: { seconds: 2 }
        backoff: { exponential: {} }
        limit:
          attempt:
            count: 3
      do:
        - fallback:
            set:
              result: default_value
```

---

## Runtime Expressions

Expressions use **jq syntax** wrapped in `${ }`.

```yaml
${ $input.userId }          # workflow input
${ $data.fetchUser.name }   # previous task output (by task name)
${ $context.userId }        # accumulated context state
${ $env.API_KEY }           # environment variable
${ uuid }                   # replay-safe UUID
${ timestamp }              # replay-safe timestamp
${ .users | map(.name) }    # jq filter
```

### Built-in Variables

| Variable | Contains |
|---|---|
| `$input` | Raw input passed when the workflow was started |
| `$context` | Accumulated workflow state (from `export.as`) |
| `$data` | Output from the previous task |
| `$env` | Environment variables |

### output.as vs export.as

```yaml
- fetchUser:
    call: http
    with:
      method: get
      endpoint: https://api.example.com/users/1
    output:
      as:
        user: ${ . }                            # shapes what flows to the NEXT task only
    export:
      as: "${ $context + {fetchedUser: .} }"    # persists into $context for ALL later tasks
```

> **Rule:** Always use `${ $context + {key: value} }` in `export.as` — never `${ . }` alone, or you'll overwrite existing context.

---

## Running a Zigflow Workflow

```bash
# Step 1 — validate your YAML
zigflow validate workflow.yaml

# Step 2 — start the Zigflow worker (Terminal 1, keep running)
zigflow run -f workflow.yaml

# Step 3 — trigger the workflow (Terminal 2)
temporal workflow start \
  --type <workflowType> \
  --task-queue <taskQueue> \
  --workflow-id my-run-01 \
  --input '{}'

# Step 4 — send a signal (if workflow uses listen)
temporal workflow signal \
  --workflow-id my-run-01 \
  --name approve \
  --input '{"approved": true}'

# Step 5 — inspect the result
temporal workflow show --workflow-id my-run-01
```

### Zigflow YAML → Temporal CLI Mapping

| Zigflow YAML | Temporal CLI flag |
|---|---|
| `workflowType` | `--type` |
| `taskQueue` | `--task-queue` |
| `listen.to.one.with.id` | `signal --name` |
| workflow start `input` | `--input` |

---

## Zigflow CLI Cheatsheet

```bash
zigflow validate workflow.yaml          # validate against DSL schema
zigflow run -f workflow.yaml            # start worker
zigflow run -f workflow.yaml \
  --log-level debug                     # verbose output
zigflow run -f workflow.yaml \
  --temporal-address localhost:7233     # custom server address
zigflow run -f workflow.yaml \
  --temporal-namespace my-namespace     # custom namespace
zigflow schema                          # print full DSL JSON schema
zigflow graph -f workflow.yaml          # visualise workflow as graph
zigflow version                         # show CLI version
```

---

## Repo Examples

All runnable examples are in `Zigflow/Examples/`:

| File | Task Queue | Workflow Type | Demonstrates |
|---|---|---|---|
| `hello_world.yaml` | `zigflow` | `hello-world` | Minimal `set` + variable output |
| `http_call.yaml` | `zigflow-http` | `fetch-user` | `call: http` with `output.as` |
| `signal_driven_workflow.yaml` | `zigflow-signals` | `signal` | `listen` task + `wait` timer |
| `parallel_task.yaml` | `zigflow-parallel-tasks` | `competing-tasks` | `fork` with `compete: true` (race) |
| `error_handling.yaml` | `zigflow-error-handle` | `try-catch` | `try`/`catch` with fallback `set` |

### Running the Examples

```bash
cd Zigflow/Examples

# Hello World
zigflow run -f hello_world.yaml
temporal workflow start --type hello-world --task-queue zigflow --workflow-id hw-01 --input '{}'

# HTTP Call
zigflow run -f http_call.yaml
temporal workflow start --type fetch-user --task-queue zigflow-http --workflow-id http-01 --input '{}'

# Signal-Driven
zigflow run -f signal_driven_workflow.yaml
temporal workflow start --type signal --task-queue zigflow-signals --workflow-id sig-01 --input '{}'
temporal workflow signal --workflow-id sig-01 --name approve --input '{"approved": true}'

# Parallel / Race
zigflow run -f parallel_task.yaml
temporal workflow start --type competing-tasks --task-queue zigflow-parallel-tasks --workflow-id par-01 --input '{}'

# Error Handling
zigflow run -f error_handling.yaml
temporal workflow start --type try-catch --task-queue zigflow-error-handle --workflow-id err-01 --input '{}'
```

---

## Zigflow Key Rules

1. **Task Queue and Workflow Type are case-sensitive** — `zigflow-HTTP` ≠ `zigflow-http`
2. **`set` must be deterministic** — never use `$env.RANDOM` or wall-clock time; use `${ uuid }` and `${ timestamp }`
3. **Every task needs a name** — the task name is the key under `do`; missing it causes a YAML parse error
4. **Zigflow doesn't self-trigger** — always trigger with `temporal workflow start` after the worker is running
5. **Signal name must match `listen.to.one.with.id`** exactly — `temporal workflow signal --name approve` must match `id: approve` in YAML
6. **`fork compete: false` returns an array** — both branch results are wrapped in an array; don't expect a single value
7. **`export.as` must merge, not replace** — use `${ $context + {key: .} }`, not `${ . }`, or you'll lose all previous context
8. **Validate before running** — always run `zigflow validate workflow.yaml` first; it catches schema errors before Temporal sees them
9. **`metadata.activityOptions` sets defaults for all tasks** — override per-task with a task-level `metadata.timeout`
10. **Activity code changes are safe to hot-deploy** — Workflow (YAML) changes that alter execution order can cause non-determinism for in-flight executions

---

## Repo Structure (Zigflow)

```
Zigflow/
  Examples/
    hello_world.yaml                 # minimal set + output pattern
    http_call.yaml                   # HTTP call with output.as
    signal_driven_workflow.yaml      # listen task + wait timer
    parallel_task.yaml               # fork with compete: true (race)
    error_handling.yaml              # try/catch with fallback
  Tutorials/                         # placeholder for tutorial YAML files
```

---

## Cheatsheet Files

Three standalone quick-reference files at the repo root:

| File | Contents |
|---|---|
| [`Zigflow_DSL_Cheatsheet.md`](Zigflow_DSL_Cheatsheet.md) | All 11 task types, fork/listen/for/switch patterns, expressions, output/export |
| [`Zigflow_CLI_Cheatsheet.md`](Zigflow_CLI_Cheatsheet.md) | All `zigflow` commands, flags, dev flow, failure debugging flow |
| [`Temporal_CLI_Cheatsheet.md`](Temporal_CLI_Cheatsheet.md) | All `temporal` commands — server, workflow, signal, query, update, task queue |

