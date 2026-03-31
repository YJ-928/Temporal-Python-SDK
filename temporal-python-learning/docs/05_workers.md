# Workers

## What Is a Worker?

A Worker is a process that **polls** a Task Queue for tasks and **executes** your Workflow and Activity code. Workers are the runtime environment for your Temporal application code.

## Architecture

```
┌─────────────────────┐
│   Temporal Cluster   │
│                     │
│  ┌───────────────┐  │
│  │  Task Queue   │  │
│  │  "greeting"   │  │
│  └───────┬───────┘  │
│          │          │
└──────────┼──────────┘
           │ poll
           ▼
┌─────────────────────┐
│      Worker         │
│                     │
│  Workflows:         │
│   - GreetSomeone    │
│                     │
│  Activities:        │
│   - greet_in_spanish│
└─────────────────────┘
```

## Creating a Worker

### Basic Worker

```python
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from greeting import GreetSomeone


async def main():
    client = await Client.connect("localhost:7233", namespace="default")

    worker = Worker(
        client,
        task_queue="greeting-tasks",
        workflows=[GreetSomeone],
    )
    print("Starting worker...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Worker with Activities

```python
import asyncio
import aiohttp
from temporalio.client import Client
from temporalio.worker import Worker
from translate import TranslateActivities
from greeting import GreetSomeone


async def main():
    client = await Client.connect("localhost:7233", namespace="default")

    async with aiohttp.ClientSession() as session:
        activities = TranslateActivities(session)

        worker = Worker(
            client,
            task_queue="greeting-tasks",
            workflows=[GreetSomeone],
            activities=[
                activities.greet_in_spanish,
                activities.farewell_in_spanish,
            ],
        )
        print("Starting the worker....")
        await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
```

## Worker Configuration

| Parameter | Description |
|-----------|-------------|
| `client` | Temporal client connected to the cluster |
| `task_queue` | Name of the Task Queue to poll |
| `workflows` | List of Workflow classes to register |
| `activities` | List of Activity functions/methods to register |

## How Workers Execute Tasks

1. Worker establishes a **long-poll** connection to the Temporal Cluster
2. Cluster places a task on the Task Queue when work is available
3. Worker picks up the task and executes the corresponding code
4. Worker reports the result back to the Cluster
5. Cluster records the result in the event history

## Running Multiple Workers

You can run multiple Workers on the same Task Queue for **horizontal scaling**:

```bash
# Terminal 1
python worker.py

# Terminal 2
python worker.py
```

The Temporal Cluster distributes tasks across available Workers.

## Worker Lifecycle

```python
# Worker runs until interrupted (Ctrl+C)
await worker.run()
```

The Worker gracefully shuts down when interrupted, completing any in-progress tasks.

## Logging in Workers

```python
import logging

async def main():
    logging.basicConfig(level=logging.INFO)
    client = await Client.connect("localhost:7233", namespace="default")

    # ...
    logging.info(f"Starting the worker....{client.identity}")
    await worker.run()
```

## Best Practices

- Always register **all** Workflows and Activities the Worker should execute
- Use the same Task Queue name in Workers and Starters
- Run multiple Worker instances for high availability
- Use dependency injection for Activity dependencies (HTTP sessions, DB connections)
- Gracefully handle shutdown signals

## Exercise

1. Create a Worker that registers a simple greeting Workflow
2. Start the Worker and verify it connects to the Temporal Cluster
3. Run a Workflow using the Temporal CLI and observe the Worker execute it
