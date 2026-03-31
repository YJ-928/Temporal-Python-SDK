# Workflows

## What Is a Workflow?

A Workflow is a **durable function** that orchestrates the execution of Activities and other operations. It defines the sequence of steps in your business logic.

Workflows are the core building block of Temporal applications.

## Workflow Rules

Workflow code must be **deterministic**. This means:

| Rule | Reason |
|------|--------|
| No direct I/O (HTTP, DB, file system) | I/O must go through Activities |
| No random number generation | Results would differ on replay |
| No system clock access | Use `workflow.now()` instead |
| No threading or global mutable state | Must be single-threaded and isolated |
| No non-deterministic libraries | Results must be identical on replay |

Why? Temporal **replays** Workflow code from the event history to reconstruct state. If code behaves differently on replay, the Workflow breaks.

## Defining a Workflow

```python
from temporalio import workflow


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return f"Hello, {name}!"
```

### Key Decorators

- `@workflow.defn` — Marks a class as a Workflow Definition
- `@workflow.run` — Marks the entry-point method (must be `async`)

## Executing Activities from a Workflow

```python
from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import greet


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        result = await workflow.execute_activity(
            greet,
            name,
            start_to_close_timeout=timedelta(seconds=5),
        )
        return result
```

### Activity Execution Methods

| Method | Use Case |
|--------|----------|
| `workflow.execute_activity()` | Standalone function-based Activities |
| `workflow.execute_activity_method()` | Class-based Activities (method reference) |

### Class-Based Activity Example

```python
@workflow.defn
class GreetSomeone:
    @workflow.run
    async def run(self, name: str) -> str:
        greeting = await workflow.execute_activity_method(
            TranslateActivities.greet_in_spanish,
            name,
            start_to_close_timeout=timedelta(seconds=5),
        )
        return greeting
```

## Workflow Sandbox and Imports

Temporal runs Workflows in a **sandbox** to enforce determinism. Use `workflow.unsafe.imports_passed_through()` to import Activity modules:

```python
with workflow.unsafe.imports_passed_through():
    from activities import TranslateActivities
```

This passes the import through without reloading the module inside the sandbox.

## Long-Running Workflows

Workflows can run for **days, months, or years**:

```python
import asyncio

@workflow.defn
class LongRunningWorkflow:
    @workflow.run
    async def run(self) -> str:
        await asyncio.sleep(86400)  # 1 day — handled as a durable timer
        return "Done after 1 day"
```

Temporal converts `asyncio.sleep()` into a **durable timer** backed by the event history.

## Workflow Input and Output

Use Python dataclasses for structured input/output:

```python
from dataclasses import dataclass


@dataclass
class WorkflowInput:
    name: str
    language_code: str


@dataclass
class WorkflowOutput:
    hello_message: str
    goodbye_message: str


@workflow.defn
class TranslationWorkflow:
    @workflow.run
    async def run(self, input: WorkflowInput) -> WorkflowOutput:
        # ...
        return WorkflowOutput(
            hello_message="Bonjour, Pierre",
            goodbye_message="Au revoir, Pierre",
        )
```

## Best Practices

- Keep Workflow code focused on orchestration, not business logic
- Use Activities for all I/O and side effects
- Use dataclasses for Workflow input/output
- Always set timeouts on Activity executions
- Use `workflow.logger` for logging inside Workflows

## Exercise

Create a Workflow that:
1. Accepts a `name` parameter
2. Calls a greeting Activity
3. Returns the greeting message

See [exercise_01_hello_workflow.py](../exercises/exercise_01_hello_workflow.py)
