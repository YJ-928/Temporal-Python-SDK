# Zigflow + Temporal — Complete Knowledge Base & Cheatsheet

> **Purpose:** Authoritative reference for building, running, debugging, and operating workflows using Zigflow + Temporal. Covers DSL, CLI, execution model, and best practices.

---

## Table of Contents

1. [Zigflow Knowledge Base](#1-zigflow-knowledge-base)
   - 1.1 [What is Zigflow (ELI5 + Architecture)](#11-what-is-zigflow-eli5--architecture)
   - 1.2 [Core Concepts](#12-core-concepts)
   - 1.3 [DSL Structure](#13-dsl-structure)
   - 1.4 [Task Types](#14-task-types)
   - 1.5 [Runtime Expressions](#15-runtime-expressions)
   - 1.6 [Metadata & Configuration](#16-metadata--configuration)
   - 1.7 [Execution Model](#17-execution-model)
   - 1.8 [Debugging & Observability](#18-debugging--observability)
   - 1.9 [Common Mistakes](#19-common-mistakes)
2. [Zigflow DSL Cheatsheet](#2-zigflow-dsl-cheatsheet)
3. [Zigflow CLI Cheatsheet](#3-zigflow-cli-cheatsheet)
4. [Temporal CLI Cheatsheet](#4-temporal-cli-cheatsheet)

---

## 1. Zigflow Knowledge Base

### 1.1 What is Zigflow (ELI5 + Architecture)

**ELI5:** Zigflow lets you describe a workflow as a YAML file. You write what steps happen, in what order, and Zigflow runs them reliably on top of Temporal — meaning steps survive crashes, retries are automatic, and you can inspect everything in the Temporal Web UI.

**Longer definition:** Zigflow is a declarative workflow engine that implements the [CNCF Serverless Workflow DSL v1.0.0](https://github.com/serverlessworkflow/specification). It compiles YAML workflow definitions into Temporal workflows, providing:
- Durable, fault-tolerant execution
- Built-in retry, signal/event handling, and parallel execution
- Observable execution via Temporal's event history and CloudEvents

#### Architecture Pipeline

```
YAML file
    │
    ▼
Validation        ← zigflow validate workflow.yaml
    │
    ▼
Compilation       ← Zigflow parses DSL → generates Temporal workflow code
    │
    ▼
Temporal Workflow ← Registered on a Worker polling a Task Queue
    │
    ▼
Execution         ← Triggered via Temporal CLI or client SDK
```

#### Component Roles

| Component | Role |
|---|---|
| Zigflow Worker | Polls Temporal Task Queue, executes compiled workflow logic |
| Temporal Server | Orchestrates scheduling, retries, history, timers |
| Temporal Web UI | Observes workflow runs, event history, signals |
| YAML file | Single source of truth for workflow behavior |

> Zigflow does NOT trigger workflows itself. You trigger a workflow execution using `temporal workflow start` or a Temporal client SDK after the worker is running.

---

### 1.2 Core Concepts

#### Workflow
- The top-level unit of work, defined by a YAML file
- Has two required sections: `document` (metadata) and `do` (task list)
- Runs as a Temporal Workflow identified by `workflowType` on a `taskQueue`

#### Task Queue vs Workflow Type

| Field | Purpose | Temporal Equivalent |
|---|---|---|
| `taskQueue` | Routes work to the right Worker | `task_queue` in `Worker(...)` |
| `workflowType` | Names the workflow definition | `workflow_type` registered on Worker |

Both must match exactly (case-sensitive) between the YAML and the running Worker.

#### Determinism Rules
- Workflow execution is **replayed** from event history on resume
- Expressions inside tasks must be **deterministic** — same input always produces same output
- Avoid: random numbers, current timestamps, external I/O directly in expressions
- Use `uuid` and `timestamp` runtime functions provided by the DSL (replay-safe)

#### Event-Driven Execution
- Tasks can pause and wait for external signals via `listen`
- Signals arrive as CloudEvents with `id`, `type`, and optional `data`
- The workflow resumes deterministically once the expected event arrives

#### Validation Model
- Zigflow validates the YAML structure against the DSL schema before running
- Validation catches: missing required fields, unknown task types, malformed expressions
- Always run `zigflow validate` before `zigflow run`

---

### 1.3 DSL Structure

Every Zigflow workflow file has two top-level keys: `document` and `do`.

```yaml
document:
  dsl: "1.0.0"          # DSL version — always "1.0.0"
  taskQueue: my-queue   # Temporal Task Queue name
  workflowType: my-wf   # Temporal Workflow Type name
  version: "1.0.0"      # Your workflow's semantic version
  metadata:             # Optional: activityOptions, custom tags
    activityOptions:
      startToCloseTimeout:
        minutes: 5

do:                     # Ordered list of named tasks
  - taskName:
      <task-definition>
```

#### `document` Fields

| Field | Required | Description |
|---|---|---|
| `dsl` | yes | DSL version. Use `"1.0.0"` |
| `taskQueue` | yes | Temporal Task Queue to poll. Must match Worker config. |
| `workflowType` | yes | Temporal Workflow Type. Must match Worker registration. |
| `version` | yes | Semantic version of your workflow definition |
| `metadata` | no | Additional config: `activityOptions`, custom key/value tags |

#### `do` Structure

`do` is an ordered list of named task objects. Each entry is a map with one key (the task name) whose value is the task definition:

```yaml
do:
  - stepOne:          # task name — used by flow directives (then: stepOne)
      set:
        value: hello
  - stepTwo:
      call: http
      with:
        method: get
        endpoint: https://api.example.com/data
```

---

### 1.4 Task Types

#### `set` — Assign variables

Sets key/value pairs in the workflow data. The primary way to initialise or update state.

```yaml
- initState:
    set:
      userId: ${ $input.userId }
      status: pending
      requestId: ${ uuid }
```

**When to use:** Initialise state, store intermediate values, create computed fields.

---

#### `call` — Invoke external services

Calls HTTP endpoints, OpenAPI operations, gRPC services, or AsyncAPI channels.

```yaml
# HTTP call
- getUser:
    call: http
    with:
      method: get
      endpoint: https://api.example.com/users/1
    output:
      as:
        user: ${ . }

# OpenAPI call
- findPets:
    call: openapi
    with:
      document:
        endpoint: https://petstore.swagger.io/v2/swagger.json
      operationId: findPetsByStatus
      parameters:
        status: available
```

**Supported call targets:** `http`, `openapi`, `grpc`, `asyncapi`

**When to use:** Any interaction with an external service or API.

---

#### `do` — Sequential subtask group

Groups multiple tasks to run sequentially as a logical unit.

```yaml
- processOrder:
    do:
      - validatePayment:
          call: http
          with:
            method: post
            endpoint: https://payments.example.com/validate
      - fulfillOrder:
          call: http
          with:
            method: post
            endpoint: https://fulfillment.example.com/fulfill
```

**When to use:** Grouping related steps, nested logic within `fork` branches or `for` loops.

---

#### `fork` — Parallel execution

Runs multiple branches concurrently. Two modes:
- **Parallel** (`compete: false`): all branches run, output is an array of all results
- **Race** (`compete: true`): first branch to finish wins, its output becomes the task output

```yaml
# Parallel — collect all results
- gatherData:
    fork:
      compete: false
      branches:
        - fetchUsers:
            call: http
            with:
              method: get
              endpoint: https://api.example.com/users
        - fetchProducts:
            call: http
            with:
              method: get
              endpoint: https://api.example.com/products

# Race — first response wins
- fastestProvider:
    fork:
      compete: true
      branches:
        - providerA:
            call: http
            with:
              method: get
              endpoint: https://provider-a.example.com/data
        - providerB:
            call: http
            with:
              method: get
              endpoint: https://provider-b.example.com/data
```

**When to use:** Parallel data fetching, redundant calls for resilience, fan-out patterns.

---

#### `for` — Loop over a collection

Iterates over an array, executing a subtask for each item.

```yaml
- processItems:
    for:
      each: item       # loop variable name (default: item)
      in: .items       # jq expression for the array
      at: index        # index variable name (default: index)
    while: ${ .continue == true }  # optional continuation condition
    do:
      - processOne:
          call: http
          with:
            method: post
            endpoint: https://api.example.com/process
            body:
              id: ${ $item.id }
```

**When to use:** Batch processing, per-item operations, iterating over API results.

---

#### `listen` — Wait for an external event/signal

Suspends the workflow until one or more CloudEvents arrive. Works with Temporal signals.

```yaml
- waitForApproval:
    listen:
      to:
        one:
          with:
            id: approve          # signal name (matched against event id)
            type: signal         # event type

# Listen for any of multiple events
- waitForVital:
    listen:
      to:
        any:
          - with:
              type: com.hospital.vitals.temperature
              data: ${ .temperature > 38 }
          - with:
              type: com.hospital.vitals.bpm
              data: ${ .bpm < 60 }
```

**Event consumption strategies:**
- `one` — wait for exactly one matching event
- `any` — wait for any of the listed events
- `all` — wait for all listed events

**When to use:** Human approval flows, waiting for external triggers, event-driven branching.

---

#### `raise` — Throw an error

Deliberately raises an error to fault the workflow or trigger a `catch` block.

```yaml
- raiseValidationError:
    raise:
      error:
        type: https://errors.example.com/validation
        status: 400
        title: Invalid Input
        detail: "userId must be a positive integer"
```

**Standard error types:**

| URI | Status | Use for |
|---|---|---|
| `.../errors/configuration` | 400 | Bad config/env |
| `.../errors/validation` | 400 | Schema/input failures |
| `.../errors/expression` | 400 | Bad runtime expression |
| `.../errors/authentication` | 401 | Auth failures |
| `.../errors/authorization` | 403 | Permission denied |
| `.../errors/timeout` | 408 | Timeout |
| `.../errors/communication` | 500 | Network/service errors |
| `.../errors/runtime` | 500 | Unexpected runtime errors |

**When to use:** Business rule violations, invalid state, explicit fault escalation.

---

#### `run` — Execute a process

Runs a container, shell command, script, or sub-workflow.

```yaml
# Shell command
- runShell:
    run:
      shell:
        command: 'echo "Processing ${ .userId }"'

# Python/JS script
- runScript:
    run:
      script:
        language: js
        code: >
          console.log("Hello from script")

# Sub-workflow
- runSubWorkflow:
    run:
      workflow:
        namespace: my-namespace
        name: child-workflow
        version: "1.0.0"
        input:
          userId: ${ .userId }
```

**When to use:** Shell automation, inline scripts, launching child workflows.

---

#### `switch` — Conditional branching

Routes execution to different tasks based on runtime conditions.

```yaml
- routeByPriority:
    switch:
      - highPriority:
          when: .priority == "high"
          then: escalate        # flow directive: jump to named task
      - lowPriority:
          when: .priority == "low"
          then: queue
      - default:                # no 'when' = default case
          then: normalProcess
```

**Flow directives for `then`:**
- `continue` — next task in sequence (default)
- `exit` — stop current branch
- `end` — complete the workflow
- `<task-name>` — jump to named task

**When to use:** Priority routing, feature flags, error path selection.

---

#### `try` — Error handling with catch

Wraps tasks and catches errors, optionally with retry logic.

```yaml
- safeApiCall:
    try:
      - callApi:
          call: http
          with:
            method: get
            endpoint: https://unstable-api.example.com/data
    catch:
      errors:
        with:
          type: https://serverlessworkflow.io/spec/1.0.0/errors/communication
          status: 503
      as: error               # save error to variable
      retry:
        delay:
          seconds: 3
        backoff:
          exponential: {}     # 3s, 6s, 12s...
        limit:
          attempt:
            count: 5
      do:
        - setFallback:
            set:
              result: fallback_value
```

**When to use:** Wrapping unreliable external calls, implementing retry with backoff, graceful degradation.

---

#### `wait` — Pause execution

Pauses the workflow for a specified duration. Backed by a durable Temporal timer.

```yaml
- pauseBeforeRetry:
    wait:
      seconds: 30

# ISO 8601 duration string also supported
- pauseOneHour:
    wait: PT1H
```

**When to use:** Rate limiting, cooldown periods, scheduled delays, polling intervals.

---

### 1.5 Runtime Expressions

Zigflow uses **jq-style** runtime expressions wrapped in `${ }`.

#### Syntax

```yaml
${ <jq-expression> }
```

#### Built-in Variables

| Variable | Description |
|---|---|
| `$input` | The raw input passed when the workflow was started |
| `$context` | The current workflow context (exported state across tasks) |
| `$data` | The current task's input data (output from previous task) |
| `$env` | Environment variables available to the runtime |
| `$task` | Metadata about the current task (name, reference) |
| `$workflow` | Metadata about the current workflow (input, definition) |

#### Built-in Functions

| Function | Returns | Example |
|---|---|---|
| `uuid` | A new UUID string | `${ uuid }` |
| `timestamp` | Current ISO 8601 timestamp | `${ timestamp }` |

> **Determinism note:** `uuid` and `timestamp` are provided by the Zigflow/Temporal runtime and are replay-safe. Do NOT use external random/time sources.

#### Expression Examples

```yaml
# Access workflow input
userId: ${ $input.userId }

# Access previous task output
userName: ${ $data.createUser.name }

# Access context (accumulated state)
allResults: ${ $context.results }

# Conditional value
status: ${ if .score > 90 then "pass" else "fail" end }

# Array transformation
names: ${ .users | map(.name) }

# Generate ID
requestId: ${ uuid }

# Merge into context
export:
  as: "${ $context + {lastResult: .} }"
```

#### `output` vs `export`

| Keyword | Scope | Purpose |
|---|---|---|
| `output.as` | Task output | Transform what this task returns to the next task |
| `export.as` | Workflow context | Persist data into `$context` for later tasks |

```yaml
- fetchUser:
    call: http
    with:
      method: get
      endpoint: https://api.example.com/users/1
    output:
      as:
        user: ${ . }          # next task receives {user: ...}
    export:
      as: "${ $context + {fetchedUser: .} }"  # persisted in $context
```

---

### 1.6 Metadata & Configuration

#### Document-Level Metadata

```yaml
document:
  dsl: "1.0.0"
  taskQueue: my-queue
  workflowType: my-workflow
  version: "1.0.0"
  metadata:
    activityOptions:
      startToCloseTimeout:
        minutes: 5        # default timeout for all activities
    environment: production
    team: platform
```

#### Activity Options (`metadata.activityOptions`)

| Option | Description | Example |
|---|---|---|
| `startToCloseTimeout` | Max time from activity start to finish | `minutes: 5` |
| `scheduleToCloseTimeout` | Max total time including queue wait | `minutes: 10` |
| `heartbeatTimeout` | Max time between heartbeats | `seconds: 30` |

```yaml
metadata:
  activityOptions:
    startToCloseTimeout:
      minutes: 1
    heartbeatTimeout:
      seconds: 30
```

#### Task-Level Metadata (Timeout Override)

```yaml
- longTask:
    metadata:
      timeout: 10m         # override timeout for this specific task
    call: http
    with:
      method: post
      endpoint: https://slow-api.example.com/process
```

#### Reusable Components (`use`)

Define retry policies, authentication, and functions once and reference by name:

```yaml
document:
  dsl: "1.0.0"
  taskQueue: my-queue
  workflowType: my-workflow
  version: "1.0.0"

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
    myApiAuth:
      bearer:
        token: ${ $env.API_TOKEN }

do:
  - callApi:
      try:
        - fetch:
            call: http
            with:
              method: get
              endpoint:
                uri: https://api.example.com/data
                authentication:
                  use: myApiAuth
      catch:
        retry:
          use: standardRetry    # reference by name
```

---

### 1.7 Execution Model

#### How Zigflow Compiles and Executes

```
1. zigflow run -f workflow.yaml
       │
       ▼
2. YAML parsed → validated against DSL 1.0.0 schema
       │
       ▼
3. Compiled to a Temporal workflow (registered under workflowType)
       │
       ▼
4. Worker starts polling Temporal server on taskQueue
       │
       ▼
5. temporal workflow start --type <workflowType> --task-queue <taskQueue>
       │
       ▼
6. Temporal schedules workflow → Worker picks it up
       │
       ▼
7. Tasks execute sequentially (or in parallel for fork)
       │
       ▼
8. Side effects (HTTP calls, scripts) = Temporal Activities
       │
       ▼
9. Pure logic (set, switch, export) = Workflow code (deterministic)
```

#### Deterministic Replay

Temporal persists every event to durable storage. If the Worker crashes mid-workflow:

1. Temporal replays the workflow from the beginning using the stored event history
2. For completed activities: result is injected from history (NOT re-executed)
3. For pending activities: re-scheduled and executed fresh
4. Workflow code must produce the same sequence of commands on every replay

**Why this matters for Zigflow:**
- `set` tasks run as Workflow code → must be deterministic
- `call` tasks run as Activities → can be non-deterministic (HTTP call), but must be idempotent
- `wait` tasks create durable Temporal timers → survive Worker crashes
- `listen` tasks create durable event correlations → survive Worker crashes

#### Activities vs Workflow Code

| Task Type | Runs As | Notes |
|---|---|---|
| `call` | Temporal Activity | Can do I/O; retried on failure |
| `run` | Temporal Activity | Executes container/script/shell |
| `set` | Workflow code | Must be deterministic |
| `switch` | Workflow code | Must be deterministic |
| `wait` | Temporal Timer | Durable; survives crashes |
| `listen` | Temporal Signal handler | Durable event correlation |
| `fork` | Workflow code + child Activities | Branches run concurrently |
| `for` | Workflow code loop + child Activities | Loop body = Activity per iteration |

---

### 1.8 Debugging & Observability

#### CloudEvents (Lifecycle Events)

Zigflow emits CloudEvents for every significant state change. These can be consumed by external systems for monitoring, logging, or triggering downstream workflows.

**Workflow lifecycle events:**

| Event Type | When Emitted |
|---|---|
| `workflow.started` | Workflow begins execution |
| `workflow.suspended` | Workflow paused (e.g., waiting on `listen`) |
| `workflow.resumed` | Workflow unpaused after event arrives |
| `workflow.completed` | Workflow ran to completion |
| `workflow.faulted` | Workflow failed with an error |
| `workflow.cancelled` | Workflow was cancelled |

**Task lifecycle events:**

| Event Type | When Emitted |
|---|---|
| `task.created` | Task is scheduled |
| `task.started` | Task begins execution |
| `task.completed` | Task finishes successfully |
| `task.faulted` | Task failed |
| `task.retried` | Task is being retried |
| `task.cancelled` | Task was cancelled |

#### Example Event Payload

```json
{
  "type": "task.completed",
  "workflow": "orderWorkflow-abc123.samples",
  "task": "/do/1/fetchUser",
  "completedAt": "2024-07-26T16:59:57-05:00",
  "output": { "userId": "42", "name": "Alice" }
}
```

#### Using Temporal Web UI for Debugging

- **URL:** `http://localhost:8233` (dev server) or `http://localhost:8080` (Docker)
- View event history: `temporal workflow show --workflow-id <id>`
- Check input/output of each activity
- See retry attempts and error details
- Inspect pending signals (listen tasks awaiting events)

#### Debug Workflow

```bash
# 1. Validate YAML first
zigflow validate workflow.yaml

# 2. Run with debug logging
zigflow run -f workflow.yaml --log-level debug

# 3. Check Temporal event history
temporal workflow show --workflow-id <id> --detailed

# 4. List running workflows
temporal workflow list

# 5. Check Worker logs for activity errors
```

---

### 1.9 Common Mistakes

#### 1. Task Queue / Workflow Type mismatch
```yaml
# YAML says:
taskQueue: my-queue
workflowType: my-workflow

# Worker must be started with EXACTLY these values (case-sensitive)
# "My-Queue" ≠ "my-queue"
```

#### 2. Non-deterministic expressions in `set`
```yaml
# BAD — random is not deterministic
- initId:
    set:
      id: ${ $env.RANDOM }   # broken on replay

# GOOD — uuid function is replay-safe
- initId:
    set:
      id: ${ uuid }
```

#### 3. Invalid YAML structure (wrong nesting)
```yaml
# BAD — task must be a named key under do
do:
  set:              # missing task name
    value: hello

# GOOD
do:
  - initValue:      # task name is required
      set:
        value: hello
```

#### 4. Wrong `export` expression (losing context)
```yaml
# BAD — overwrites entire context with just this task's output
export:
  as: "${ . }"

# GOOD — merges into existing context
export:
  as: "${ $context + {thisTaskResult: .} }"
```

#### 5. Expecting Zigflow to trigger workflows
Zigflow does NOT self-trigger workflows. You must:
1. Start the Zigflow worker (`zigflow run -f workflow.yaml`)
2. Separately trigger execution via `temporal workflow start` or Temporal client SDK

#### 6. Missing `output.as` when chaining tasks
Without `output.as`, each task's raw output flows to the next. If you need to reshape or name the output:
```yaml
- fetchUser:
    call: http
    with:
      method: get
      endpoint: https://api.example.com/users/1
    output:
      as:
        user: ${ . }    # next task receives {user: {...}} not the raw response
```

#### 7. Using `compete: false` fork and expecting a single result
When `compete: false`, fork outputs an **array** of all branch results in declaration order:
```yaml
# output will be: [{result from branch1}, {result from branch2}]
- parallelFetch:
    fork:
      compete: false
      branches:
        - branch1: ...
        - branch2: ...
```

#### 8. Misusing `listen` — wrong event id/type
```yaml
# Signal sent via Temporal CLI:
temporal workflow signal --name approve --input '{"approved": true}'

# YAML must match the signal name exactly:
listen:
  to:
    one:
      with:
        id: approve      # must match --name in CLI
        type: signal
```

---

## 2. Zigflow DSL Cheatsheet

### Minimal Workflow

```yaml
document:
  dsl: "1.0.0"
  taskQueue: my-queue
  workflowType: hello-world
  version: "1.0.0"

do:
  - greet:
      set:
        message: Hello from Zigflow
```

---

### Task Patterns

#### Sequential

```yaml
do:
  - step1:
      set:
        status: started
  - step2:
      call: http
      with:
        method: get
        endpoint: https://api.example.com/data
  - step3:
      set:
        status: done
```

#### Parallel (all branches)

```yaml
- gatherAll:
    fork:
      compete: false
      branches:
        - fetchA:
            call: http
            with:
              method: get
              endpoint: https://api.example.com/a
        - fetchB:
            call: http
            with:
              method: get
              endpoint: https://api.example.com/b
# output: [{result of fetchA}, {result of fetchB}]
```

#### Race (first wins)

```yaml
- fastestResponse:
    fork:
      compete: true
      branches:
        - primary:
            call: http
            with:
              method: get
              endpoint: https://primary.example.com/data
        - fallback:
            call: http
            with:
              method: get
              endpoint: https://fallback.example.com/data
# output: result of whichever branch completes first
```

#### Loop (for)

```yaml
- processAll:
    for:
      each: item
      in: .items
      at: index
    do:
      - handleItem:
          call: http
          with:
            method: post
            endpoint: https://api.example.com/process
            body:
              id: ${ $item.id }
              position: ${ $index }
```

#### Signal listener (listen)

```yaml
- waitForSignal:
    listen:
      to:
        one:
          with:
            id: approve
            type: signal
- handleResult:
    export:
      as: "${ $context + {approvalData: $data.waitForSignal} }"
    set:
      approved: ${ $data.waitForSignal.approved }
```

#### Error handling (try/catch with retry)

```yaml
- safeCall:
    try:
      - apiCall:
          call: http
          with:
            method: get
            endpoint: https://unstable.example.com/resource
    catch:
      as: error
      retry:
        delay:
          seconds: 2
        backoff:
          exponential: {}
        limit:
          attempt:
            count: 3
      do:
        - fallback:
            set:
              result: default_value
```

#### Conditional branching (switch)

```yaml
- routeRequest:
    switch:
      - isPremium:
          when: .user.tier == "premium"
          then: fastPath
      - isBasic:
          when: .user.tier == "basic"
          then: slowPath
      - default:
          then: rejectRequest
- fastPath:
    call: http
    with:
      method: post
      endpoint: https://api.example.com/premium
    then: end
- slowPath:
    call: http
    with:
      method: post
      endpoint: https://api.example.com/basic
    then: end
- rejectRequest:
    raise:
      error:
        type: https://errors.example.com/unauthorized
        status: 403
        title: Access Denied
```

#### Delay (wait)

```yaml
- cooldown:
    wait:
      seconds: 30

- longDelay:
    wait:
      hours: 2
      minutes: 30
```

---

### Expression Examples

```yaml
# Access workflow input
userId: ${ $input.userId }

# Access previous task output by task name
userName: ${ $data.fetchUser.name }

# Access workflow context (accumulated state)
allIds: ${ $context.ids }

# Generate a UUID (replay-safe)
requestId: ${ uuid }

# Current timestamp (replay-safe)
createdAt: ${ timestamp }

# jq filter
activeUsers: ${ .users | map(select(.active == true)) }

# Conditional
label: ${ if .score >= 50 then "pass" else "fail" end }

# String interpolation
message: ${ "Hello, " + .name + "!" }
```

---

### Export Patterns

```yaml
# Merge task output into context (RECOMMENDED)
export:
  as: "${ $context + {taskResult: .} }"

# Replace context entirely with task output
export:
  as: "${ . }"

# Append to a context array
export:
  as: "${ $context + {results: ($context.results + [.])} }"

# Store named result
export:
  as: "${ $context + {userId: .id, userName: .name} }"
```

---

### Output Transformation

```yaml
# Reshape output before passing to next task
output:
  as:
    user: ${ . }          # wraps response in {user: ...}

# Extract a field
output:
  as: ${ .id }            # only passes the id field forward

# No transformation (default — passes raw output)
# (omit output.as entirely)
```

---

### Full Example: HTTP + Signal + Error Handling

```yaml
document:
  dsl: "1.0.0"
  taskQueue: order-queue
  workflowType: process-order
  version: "1.0.0"
  metadata:
    activityOptions:
      startToCloseTimeout:
        minutes: 2

do:
  - initOrder:
      set:
        orderId: ${ uuid }
        status: pending
      export:
        as: "${ $context + {orderId: ${ uuid }, status: \"pending\"} }"

  - fetchProduct:
      try:
        - getProduct:
            call: http
            with:
              method: get
              endpoint: https://api.example.com/products/${ $input.productId }
            output:
              as:
                product: ${ . }
      catch:
        retry:
          delay:
            seconds: 3
          backoff:
            exponential: {}
          limit:
            attempt:
              count: 3
        do:
          - raiseError:
              raise:
                error:
                  type: https://errors.example.com/product-not-found
                  status: 404
                  title: Product Not Found

  - waitForApproval:
      metadata:
        timeout: 10m
      listen:
        to:
          one:
            with:
              id: approve
              type: signal

  - routeByApproval:
      switch:
        - approved:
            when: $data.waitForApproval.approved == true
            then: completeOrder
        - rejected:
            then: cancelOrder

  - completeOrder:
      set:
        status: completed
      then: end

  - cancelOrder:
      set:
        status: cancelled
```

---

### DO / DON'T

| Do | Don't |
|---|---|
| Use `set` for initialising and updating workflow state | Use `set` for I/O (HTTP calls, DB queries) |
| Use `call` for all external service interactions | Put direct API logic in expressions |
| Use `export` to persist data across tasks via `$context` | Assume `$data` carries forward more than one task deep |
| Use `try`/`catch` around unreliable external calls | Let network errors crash the entire workflow |
| Use `uuid` and `timestamp` for IDs and times | Use `$env.RANDOM` or external time sources in expressions |
| Keep expressions deterministic and replay-safe | Use non-deterministic operations in `set` or `switch` |
| Run `zigflow validate` before `zigflow run` | Skip validation and debug at runtime |
| Match `taskQueue` and `workflowType` exactly | Assume case-insensitive matching |
| Use `compete: true` for race patterns | Expect `compete: false` to return a single value |
| Use `listen` with explicit `id` and `type` | Send signals with names that don't match YAML |

---

## 3. Zigflow CLI Cheatsheet

### Core Commands

```bash
# Validate a workflow YAML file
zigflow validate workflow.yaml

# Run a workflow worker (starts polling Temporal for this workflow)
zigflow run -f workflow.yaml

# Run from a directory of workflow files
zigflow run -f ./workflows/

# Show Zigflow version
zigflow version

# Show the DSL JSON schema
zigflow schema

# Generate a visual graph of the workflow
zigflow graph -f workflow.yaml
```

---

### Dev Flow

```
1. Write YAML
       │
       ▼
2. zigflow validate workflow.yaml
   → Fix any schema errors before proceeding
       │
       ▼
3. zigflow run -f workflow.yaml
   → Worker starts, polls Temporal on the configured taskQueue
       │
       ▼
4. (separate terminal) temporal workflow start \
     --type <workflowType> \
     --task-queue <taskQueue> \
     --workflow-id <your-id> \
     --input '{"key": "value"}'
       │
       ▼
5. Send signals (if workflow uses listen):
   temporal workflow signal \
     --workflow-id <your-id> \
     --name <signal-id> \
     --input '{"approved": true}'
       │
       ▼
6. Observe execution:
   temporal workflow show --workflow-id <your-id>
   → or open http://localhost:8233
```

---

### Useful Flags

| Flag | Description | Example |
|---|---|---|
| `--log-level debug` | Enable verbose debug logging | `zigflow run -f wf.yaml --log-level debug` |
| `--log-level info` | Standard info logging (default) | |
| `--validate=false` | Skip YAML validation on run | `zigflow run -f wf.yaml --validate=false` |
| `--temporal-address` | Override Temporal server address | `--temporal-address localhost:7233` |
| `--temporal-namespace` | Override Temporal namespace | `--temporal-namespace my-ns` |

---

### Debugging Checklist

1. **Always validate first:** `zigflow validate workflow.yaml`
2. **Enable debug logs:** `zigflow run -f workflow.yaml --log-level debug`
3. **Check Temporal history:** `temporal workflow show --workflow-id <id> --detailed`
4. **Check for non-determinism errors** in Worker logs — caused by `set` using random/time
5. **Verify task queue and workflowType** match exactly between YAML and Worker registration
6. **Verify signal names** match between `listen.to.one.with.id` and `temporal workflow signal --name`
7. **Use CloudEvents** emitted by Zigflow for external monitoring/alerting

---

## 4. Temporal CLI Cheatsheet

### Server Management

```bash
# Start local dev server (in-memory, good for development)
temporal server start-dev

# Start with persistent storage (survives restarts)
temporal server start-dev --db-filename clusterdata.db

# Start with custom ports
temporal server start-dev --ui-port 8080 --port 7233

# Web UI: http://localhost:8233 (dev server)
# Web UI: http://localhost:8080 (Docker / custom)
# gRPC:   localhost:7233
```

---

### Workflow Commands

```bash
# Start a workflow
temporal workflow start \
  --type <workflowType> \
  --task-queue <taskQueue> \
  --workflow-id <unique-id> \
  --input '{"key": "value"}'

# Start and wait for result
temporal workflow execute \
  --type <workflowType> \
  --task-queue <taskQueue> \
  --workflow-id <unique-id> \
  --input '{"key": "value"}'

# Show event history (summary)
temporal workflow show --workflow-id <id>

# Show event history (detailed with payloads)
temporal workflow show --workflow-id <id> --detailed

# List all workflows
temporal workflow list

# List with filter
temporal workflow list --query 'WorkflowType="process-order" AND ExecutionStatus="Running"'

# Describe workflow (status, config, pending activities)
temporal workflow describe --workflow-id <id>

# Cancel a running workflow
temporal workflow cancel --workflow-id <id>

# Terminate (hard kill, no cleanup)
temporal workflow terminate --workflow-id <id> --reason "manual termination"
```

---

### Signals

Send a signal to a running workflow (used to unblock a `listen` task):

```bash
temporal workflow signal \
  --workflow-id <id> \
  --name <signal-name> \
  --input '{"approved": true}'

# Examples matching Zigflow listen tasks:
temporal workflow signal \
  --workflow-id zigflow-signals \
  --name approve \
  --input '{"approved": true}'

temporal workflow signal \
  --workflow-id order-workflow-01 \
  --name payment-confirmed \
  --input '{"transactionId": "txn-123"}'
```

> **Signal name must match** `listen.to.one.with.id` (or `any[].with.id`) exactly in the YAML.

---

### Queries

Query the current state of a running workflow (if query handlers are registered):

```bash
temporal workflow query \
  --workflow-id <id> \
  --query-type <queryName>

# With input
temporal workflow query \
  --workflow-id <id> \
  --query-type getStatus \
  --input '{"verbose": true}'
```

> Note: Standard Zigflow workflows do not expose custom queries unless the underlying Temporal workflow implementation supports it.

---

### Updates

Send an update (synchronous request that can modify state and return a value):

```bash
temporal workflow update \
  --workflow-id <id> \
  --name <updateName> \
  --input '{"value": 42}'
```

---

### Task Queue & Worker Inspection

```bash
# Describe a task queue (see registered workers and pollers)
temporal task-queue describe --task-queue <queueName>

# List workers polling a task queue
temporal task-queue get-build-ids --task-queue <queueName>
```

> **Task Queue must match** `taskQueue` in `document` section of YAML.
> **Workflow Type must match** `workflowType` in `document` section of YAML.

---

### Namespace Commands

```bash
# List namespaces
temporal operator namespace list

# Describe a namespace
temporal operator namespace describe --namespace default

# Create a namespace
temporal operator namespace create --namespace my-namespace
```

---

### Activity & Schedule Commands

```bash
# List schedules
temporal schedule list

# Describe a specific schedule
temporal schedule describe --schedule-id <id>

# Trigger a scheduled workflow immediately
temporal schedule trigger --schedule-id <id>
```

---

### Full Local Dev Workflow Example

```bash
# Terminal 1 — Start Temporal dev server
temporal server start-dev

# Terminal 2 — Start Zigflow worker
zigflow run -f workflow.yaml

# Terminal 3 — Trigger the workflow
temporal workflow start \
  --type fetch-user \
  --task-queue zigflow-http \
  --workflow-id fetch-user-01 \
  --input '{"userId": "42"}'

# Monitor
temporal workflow show --workflow-id fetch-user-01

# If workflow uses a listen task, send the signal
temporal workflow signal \
  --workflow-id fetch-user-01 \
  --name approve \
  --input '{"approved": true}'

# View result
temporal workflow show --workflow-id fetch-user-01 --detailed
```

---

### Common Temporal Error Messages & Fixes

| Error | Cause | Fix |
|---|---|---|
| `Workflow type not registered` | Worker doesn't know the `workflowType` | Verify YAML `workflowType` matches Worker registration |
| `No pollers for task queue` | Worker not running or wrong `taskQueue` | Start Zigflow worker; verify `taskQueue` matches |
| `NonDeterminismError` | Workflow code is non-deterministic | Remove random/time calls from `set` expressions |
| `WorkflowExecutionAlreadyStarted` | Workflow ID already in use | Use a unique ID or cancel the existing workflow first |
| `ActivityTaskTimedOut` | Activity took longer than `startToCloseTimeout` | Increase timeout in `metadata.activityOptions` |
| `Signal name not found` | No `listen` task waiting for that signal name | Check signal `id` in YAML; ensure workflow is in the `listen` state |

---

*Generated from: CNCF Serverless Workflow DSL v1.0.0, Zigflow examples in `Zigflow/Examples/`, and Temporal Python SDK conventions in this repository.*
