# Workflow Timers

## Overview

Temporal supports **durable timers** — pauses in Workflow execution that survive Worker crashes and restarts. When you use `asyncio.sleep()` in a Workflow, Temporal intercepts it and creates a durable timer backed by the event history.

## Creating a Timer

```python
import asyncio
from temporalio import workflow


@workflow.defn
class TimerWorkflow:
    @workflow.run
    async def run(self) -> str:
        workflow.logger.info("Before timer")

        await asyncio.sleep(10)  # 10-second durable timer

        workflow.logger.info("After timer")
        return "Timer completed"
```

## How Durable Timers Work

1. Workflow calls `asyncio.sleep(10)`
2. Temporal records a `TimerStarted` event in the history
3. Worker is free to process other tasks
4. After 10 seconds, Temporal records a `TimerFired` event
5. Workflow execution resumes

### Event History

```
TimerStarted    (duration: 10s)
TimerFired      (10 seconds later)
```

### On Worker Crash

If the Worker crashes while a timer is running:
- The timer state is preserved in the event history
- When a new Worker picks up the Workflow, the timer continues counting
- The Workflow resumes exactly when the timer was supposed to fire

## Timer in a Real Workflow

```python
@workflow.defn
class TranslationWorkflow:
    @workflow.run
    async def run(self, input: TranslationWorkflowInput) -> TranslationWorkflowOutput:
        # Activity 1
        hello_result = await workflow.execute_activity_method(
            TranslationActivities.translate_term,
            hello_input,
            start_to_close_timeout=timedelta(seconds=5),
        )

        # Durable timer between activities
        workflow.logger.info("sleeping between translation calls")
        await asyncio.sleep(10)

        # Activity 2
        goodbye_result = await workflow.execute_activity_method(
            TranslationActivities.translate_term,
            goodbye_input,
            start_to_close_timeout=timedelta(seconds=5),
        )

        return TranslationWorkflowOutput(...)
```

## Long Timers

Timers can be very long — hours, days, or even months:

```python
# Wait 24 hours
await asyncio.sleep(86400)

# Wait 7 days
await asyncio.sleep(604800)
```

Temporal handles these efficiently — the Worker doesn't need to stay running during the timer.

## Timer vs Activity

| Feature | Timer | Activity |
|---------|-------|----------|
| Purpose | Wait/delay | Execute work |
| Deterministic | Yes | No |
| During replay | Skipped instantly | Result read from history |
| Resource usage | None (server-side) | Worker CPU/memory |

## Best Practices

- Use `asyncio.sleep()` for all delays in Workflows
- Never use `time.sleep()` — it blocks the event loop
- Use short timers in exercises to avoid waiting
- Long timers in production are free — the Worker doesn't idle
- Monitor timers in the Web UI by checking `TimerStarted`/`TimerFired` events

## Exercise

1. Create a Workflow with a 5-second timer between two Activities
2. Run the Workflow and observe the `TimerStarted` and `TimerFired` events in the Web UI
3. Kill the Worker during the timer and restart it — verify the Workflow completes
