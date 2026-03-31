# Temporal Overview

## What Is Temporal?

Temporal is an open-source **durable execution platform** that ensures your application code runs to completion, even in the presence of failures such as network outages, server crashes, or bugs.

Traditional applications lose state when a process crashes. Temporal solves this by persisting every step of your application's execution as an **event history**. If a failure occurs, Temporal automatically replays the history to restore the exact state before the failure.

## Key Concepts

### Durable Execution

Durable execution means your code **always completes**, regardless of infrastructure failures. Temporal achieves this by:

1. Recording every step of execution as events
2. Replaying events on recovery to reconstruct state
3. Retrying failed operations automatically

### Why Workflows Are Useful

Without Temporal, building reliable distributed systems requires:

- Manual retry logic
- State persistence code
- Distributed transaction management
- Complex error handling
- Idempotency guarantees

With Temporal, you write **plain application code** and Temporal handles reliability.

## Core Components

| Component | Description |
|-----------|-------------|
| **Workflow** | Durable function that orchestrates tasks |
| **Activity** | Non-deterministic work (API calls, DB writes) |
| **Worker** | Process that executes Workflows and Activities |
| **Task Queue** | Named queue that routes work to Workers |
| **Temporal Cluster** | Server that manages orchestration and history |

## Example: Simple Greeting Workflow

```python
from datetime import timedelta
from temporalio import workflow, activity


@activity.defn
async def greet(name: str) -> str:
    return f"Hello, {name}!"


@workflow.defn
class GreetingWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            greet,
            name,
            start_to_close_timeout=timedelta(seconds=5),
        )
```

## How Temporal Differs from Message Queues

| Feature | Message Queues | Temporal |
|---------|---------------|----------|
| State management | Manual | Automatic |
| Retries | Manual configuration | Built-in with policies |
| Long-running processes | Complex | Native support |
| Visibility | Limited | Full event history |
| Error handling | Per-consumer | Centralized |

## Best Practices

- Start with the simplest Workflow that fulfills your requirements
- Use Activities for all non-deterministic operations
- Set appropriate timeouts on every Activity
- Use the Temporal Web UI to observe and debug Workflows

## Exercise

1. Install the Temporal CLI: `brew install temporal` or download from [temporal.io](https://temporal.io)
2. Start a dev server: `temporal server start-dev`
3. Open the Web UI: `http://localhost:8233`
4. Verify the server is running: `temporal workflow list`
