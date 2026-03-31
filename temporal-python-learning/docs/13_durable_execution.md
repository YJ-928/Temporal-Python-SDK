# Durable Execution

## What Is Durable Execution?

Durable execution is Temporal's core guarantee: your Workflow code **always runs to completion**, regardless of failures. If a Worker crashes, the Temporal Cluster replays the event history to restore the Workflow's state and continue execution.

## How It Works

### Event History

Every Workflow execution produces an **event history** — a sequence of events stored by the Temporal Cluster:

```
1. WorkflowExecutionStarted     ← Workflow received input
2. WorkflowTaskScheduled        ← Cluster dispatched task
3. WorkflowTaskStarted          ← Worker picked up task
4. WorkflowTaskCompleted        ← Worker completed task
5. ActivityTaskScheduled        ← Activity dispatched
6. ActivityTaskStarted          ← Activity started executing
7. ActivityTaskCompleted        ← Activity returned result
8. TimerStarted                 ← asyncio.sleep() started
9. TimerFired                   ← Timer completed
10. ActivityTaskScheduled       ← Next Activity dispatched
11. ActivityTaskCompleted       ← Next Activity completed
12. WorkflowExecutionCompleted  ← Workflow finished
```

### Replay

When a Worker needs to resume a Workflow (e.g., after a crash):

1. Temporal sends the **full event history** to the Worker
2. The Worker **replays** the Workflow code from the beginning
3. During replay, Activity calls are **not re-executed** — their cached results from the history are used
4. Timers are **skipped** — their completion is already recorded
5. Once replay catches up to the last recorded event, normal execution resumes

## Example: Translation Workflow with Timer

```python
import asyncio
from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import TranslationActivities
    from shared import (
        TranslationActivityInput,
        TranslationWorkflowInput,
        TranslationWorkflowOutput,
    )


@workflow.defn
class TranslationWorkflow:
    @workflow.run
    async def run(self, input: TranslationWorkflowInput) -> TranslationWorkflowOutput:
        workflow.logger.info(f"TranslationWorkflow invoked with {input}")

        # Activity 1: Translate "hello"
        hello_input = TranslationActivityInput(
            language_code=input.language_code, term="hello"
        )
        hello_result = await workflow.execute_activity_method(
            TranslationActivities.translate_term,
            hello_input,
            start_to_close_timeout=timedelta(seconds=5),
        )
        hello_message = f"{hello_result.translation}, {input.name}"

        # Durable timer — survives crashes
        workflow.logger.info("sleeping between translation calls")
        await asyncio.sleep(10)

        # Activity 2: Translate "goodbye"
        goodbye_input = TranslationActivityInput(
            language_code=input.language_code, term="goodbye"
        )
        goodbye_result = await workflow.execute_activity_method(
            TranslationActivities.translate_term,
            goodbye_input,
            start_to_close_timeout=timedelta(seconds=5),
        )
        goodbye_message = f"{goodbye_result.translation}, {input.name}"

        return TranslationWorkflowOutput(
            hello_message=hello_message, goodbye_message=goodbye_message
        )
```

### Event History for This Workflow

```
WorkflowExecutionStarted
  ↓
ActivityTaskScheduled (translate "hello")
  ↓
ActivityTaskCompleted → "Bonjour"
  ↓
TimerStarted (10 seconds)
  ↓
TimerFired
  ↓
ActivityTaskScheduled (translate "goodbye")
  ↓
ActivityTaskCompleted → "Au revoir"
  ↓
WorkflowExecutionCompleted
```

### What Happens on Crash

If the Worker crashes after the timer:

1. Temporal detects the Worker stopped polling
2. A new Worker picks up the Workflow
3. Replay starts from the beginning
4. Activity 1 result ("Bonjour") is read from history — **not re-executed**
5. Timer is skipped — completion already recorded
6. Activity 2 executes normally
7. Workflow completes

## Why Determinism Matters

During replay, the Workflow code runs **exactly the same way** as the original execution. This is why Workflow code must be deterministic:

| Allowed | Not Allowed |
|---------|-------------|
| `workflow.execute_activity()` | HTTP calls |
| `asyncio.sleep()` | `random.random()` |
| `workflow.now()` | `datetime.now()` |
| `workflow.logger` | File I/O |

## Shared Data Definitions

```python
from dataclasses import dataclass

TASK_QUEUE_NAME = "translation-tasks"


@dataclass
class TranslationWorkflowInput:
    name: str
    language_code: str


@dataclass
class TranslationWorkflowOutput:
    hello_message: str
    goodbye_message: str


@dataclass
class TranslationActivityInput:
    term: str
    language_code: str


@dataclass
class TranslationActivityOutput:
    translation: str
```

## Best Practices

- Trust the replay mechanism — don't add manual checkpoint logic
- Keep Workflow code deterministic
- Use `asyncio.sleep()` for durable timers (Temporal intercepts it)
- Use Activities for all external operations
- Monitor event histories in the Web UI to understand execution flow

## Exercise

1. Create a Workflow with two Activities and a timer between them
2. Run the Workflow and kill the Worker during the timer
3. Restart the Worker and observe the Workflow resume from where it left off

See [exercise_05_durable_execution.py](../exercises/exercise_05_durable_execution.py)
