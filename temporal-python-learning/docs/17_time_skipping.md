# Time Skipping

## Overview

The Temporal test framework supports **time skipping** — automatically advancing time past `asyncio.sleep()` calls in Workflows. This allows you to test Workflows with long timers (minutes, hours, days) in milliseconds.

## How Time Skipping Works

When you use `WorkflowEnvironment.start_time_skipping()`, the test server:

1. Detects when a Workflow calls `asyncio.sleep()`
2. Instantly advances the clock to the timer's end
3. Fires the timer and continues execution

No real time passes — tests complete instantly.

## Using Time Skipping

```python
import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker


@pytest.mark.asyncio
async def test_workflow_with_timer():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[TranslationWorkflow],
            activities=[activities.translate_term],
        ):
            input = TranslationWorkflowInput("Pierre", "fr")
            output = await env.client.execute_workflow(
                TranslationWorkflow.run,
                input,
                id="test-translation-workflow-id",
                task_queue="test-queue",
            )
            assert "Bonjour, Pierre" == output.hello_message
            assert "Au revoir, Pierre" == output.goodbye_message
```

Even though `TranslationWorkflow` has `await asyncio.sleep(10)`, the test completes instantly.

## Time Skipping vs Local Environment

| Feature | `start_time_skipping()` | `start_local()` |
|---------|------------------------|------------------|
| Timer handling | Skipped instantly | Real-time wait |
| Use case | Testing Workflows with timers | Testing real-time behavior |
| Speed | Fast | Slow (waits for timers) |

```python
# Time skipping — fast
async with await WorkflowEnvironment.start_time_skipping() as env:
    ...

# Local — real time
async with await WorkflowEnvironment.start_local() as env:
    ...
```

## Example: Testing a Workflow with a Long Timer

Consider a Workflow that sleeps for 24 hours:

```python
@workflow.defn
class DailyReportWorkflow:
    @workflow.run
    async def run(self) -> str:
        await asyncio.sleep(86400)  # 24 hours
        return "Report generated"
```

Test it in milliseconds:

```python
@pytest.mark.asyncio
async def test_daily_report():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[DailyReportWorkflow],
        ):
            result = await env.client.execute_workflow(
                DailyReportWorkflow.run,
                id="test-daily-report",
                task_queue="test-queue",
            )
            assert result == "Report generated"
```

## Best Practices

- Always use `start_time_skipping()` for Workflows with timers
- Use `start_local()` only when you need real-time behavior
- Combine time skipping with mocked Activities for fast, isolated tests
- Use unique Task Queue names in tests to avoid conflicts

## Exercise

1. Create a Workflow with a 60-second timer
2. Write a test using `start_time_skipping()` that completes instantly
3. Verify the timer doesn't block the test
