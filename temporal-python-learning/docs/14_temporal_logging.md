# Temporal Logging

## Overview

Temporal provides built-in loggers for both Workflows and Activities. Using these loggers ensures proper behavior during replay and provides structured output.

## Workflow Logging

Use `workflow.logger` inside Workflows:

```python
from temporalio import workflow


@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, input: str) -> str:
        workflow.logger.info(f"Workflow started with input: {input}")
        # ...
        workflow.logger.debug("Processing step completed")
        workflow.logger.error("Something went wrong")
        return "done"
```

### Why Not `print()` or `logging`?

During **replay**, Temporal re-executes Workflow code. If you use `print()` or the standard `logging` module, messages would be duplicated during replay. `workflow.logger` suppresses log messages during replay by default.

### Controlling Replay Logging

```python
@workflow.defn
class TranslationWorkflow:
    # Suppress workflow info on log messages
    workflow.logger.workflow_info_on_message = False
```

## Activity Logging

Use `activity.logger` inside Activities:

```python
from temporalio import activity


@activity.defn
async def get_distance(self, address):
    activity.logger.info("get_distance invoked")
    # ...
    activity.logger.info(f"get_distance complete: {distance}")
    return distance
```

Activities are not replayed, so `activity.logger` behaves like standard logging.

## Worker-Level Logging

Configure logging for the entire Worker:

```python
import logging

async def main():
    logging.basicConfig(level=logging.INFO)

    client = await Client.connect("localhost:7233", namespace="default")
    # ...
    logging.info(f"Starting the worker....{client.identity}")
    await worker.run()
```

## Log Levels

| Level | Use Case |
|-------|----------|
| `DEBUG` | Detailed diagnostic information |
| `INFO` | General operational messages |
| `WARNING` | Unexpected but recoverable situations |
| `ERROR` | Errors that need attention |

```python
workflow.logger.debug("Detailed step info")
workflow.logger.info("Workflow progress update")
workflow.logger.warning("Unexpected state encountered")
workflow.logger.error("Critical failure occurred")
```

## Structured Logging Example

```python
@workflow.defn
class PizzaOrderWorkflow:
    @workflow.run
    async def order_pizza(self, order: PizzaOrder) -> OrderConfirmation:
        workflow.logger.info(f"order_pizza workflow invoked")
        workflow.logger.info(f"distance is {distance.kilometers}")
        workflow.logger.error("customer lives outside the service area")
```

## Best Practices

- Use `workflow.logger` in Workflows, `activity.logger` in Activities
- Never use `print()` in production Workflow or Activity code
- Use `logging.basicConfig(level=logging.INFO)` in Workers
- Use `DEBUG` level for development, `INFO` for production
- Include relevant context in log messages (IDs, input values)

## Exercise

1. Add `workflow.logger.info()` messages to a Workflow at each step
2. Add `activity.logger.info()` messages to an Activity
3. Run the Workflow and observe the log output
4. Kill and restart the Worker — verify replay logs are suppressed
