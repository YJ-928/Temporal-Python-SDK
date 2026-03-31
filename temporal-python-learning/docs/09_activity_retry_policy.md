# Activity Retry Policy

## Overview

Temporal automatically retries failed Activities. A **Retry Policy** customizes how retries behave: how many times, how long between attempts, and which errors trigger retries.

## Default Retry Behavior

Without an explicit Retry Policy, Temporal uses these defaults:

| Setting | Default |
|---------|---------|
| Initial Interval | 1 second |
| Backoff Coefficient | 2.0 |
| Maximum Interval | 100 × initial interval |
| Maximum Attempts | Unlimited |

This means Activities retry **forever** by default, with exponential backoff.

## Defining a Retry Policy

```python
from datetime import timedelta
from temporalio.common import RetryPolicy

retry_policy = RetryPolicy(
    initial_interval=timedelta(seconds=15),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=160),
    maximum_attempts=100,
)
```

## Applying a Retry Policy

```python
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import TranslateActivities


@workflow.defn
class GreetSomeone:
    @workflow.run
    async def run(self, name: str) -> str:
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=15),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=160),
            maximum_attempts=100,
        )

        greeting = await workflow.execute_activity_method(
            TranslateActivities.greet_in_spanish,
            name,
            start_to_close_timeout=timedelta(seconds=5),
            retry_policy=retry_policy,
        )
        return greeting
```

## Retry Policy Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `initial_interval` | `timedelta` | Wait time before the first retry |
| `backoff_coefficient` | `float` | Multiplier for each subsequent retry interval |
| `maximum_interval` | `timedelta` | Cap on the retry interval |
| `maximum_attempts` | `int` | Total number of attempts (including first) |
| `non_retryable_error_types` | `list[str]` | Error types that should not be retried |

## Retry Timing Example

With `initial_interval=15s` and `backoff_coefficient=2.0`:

```
Attempt 1: immediate
Attempt 2: wait 15s
Attempt 3: wait 30s
Attempt 4: wait 60s
Attempt 5: wait 120s
Attempt 6: wait 160s  (capped at maximum_interval)
Attempt 7: wait 160s
...
```

## Non-Retryable Errors

Some errors should not be retried (e.g., invalid input):

```python
from temporalio.exceptions import ApplicationError

@activity.defn
async def process_order(self, order):
    if order.amount < 0:
        raise ApplicationError(
            "Invalid order amount",
            non_retryable=True,    # Will not be retried
        )
```

## Monitoring Retries

In the Temporal Web UI:
1. Open the Workflow's event history
2. Look for multiple `ActivityTaskScheduled` → `ActivityTaskFailed` → `ActivityTaskScheduled` sequences
3. Each retry appears as a new scheduled/failed pair

## Best Practices

- Set `maximum_attempts` for Activities that call external services
- Use `non_retryable_error_types` for validation errors
- Set reasonable `maximum_interval` to avoid excessively long waits
- Use shorter `initial_interval` for transient failures
- Monitor retry counts in the Web UI

## Exercise

1. Create an Activity that randomly fails 70% of the time
2. Apply a Retry Policy with `maximum_attempts=10`
3. Run the Workflow and observe the retries in the Web UI
