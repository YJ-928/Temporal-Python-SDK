# Temporal Architecture

## High-Level Architecture

```
┌─────────────────┐       ┌─────────────────────┐       ┌──────────────┐
│                 │       │                     │       │              │
│   Your Code     │◄─────►│  Temporal Cluster    │◄─────►│   Database   │
│   (Workers)     │  gRPC │   (Server)          │       │ (Event       │
│                 │       │                     │       │  History)    │
└─────────────────┘       └─────────────────────┘       └──────────────┘
        │                         │
        │                         │
        ▼                         ▼
  ┌───────────┐           ┌──────────────┐
  │ Activities│           │  Web UI      │
  │ (I/O work)│           │ :8233        │
  └───────────┘           └──────────────┘
```

## Components in Detail

### 1. Temporal Cluster (Server)

The Temporal server is responsible for:

- **Orchestration**: Scheduling and dispatching tasks to Workers
- **Persistence**: Storing Workflow execution state as event history
- **Visibility**: Providing search and observation of running Workflows
- **Timer management**: Handling durable timers and sleep operations

The server does **not** execute your code. It only manages the orchestration.

### 2. Workers (Your Code)

Workers are processes you write and deploy. They:

- **Poll** Task Queues for work
- **Execute** Workflow and Activity code
- **Report** results back to the Temporal Cluster

```python
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker


async def main():
    client = await Client.connect("localhost:7233", namespace="default")

    worker = Worker(
        client,
        task_queue="greeting-tasks",
        workflows=[GreetingWorkflow],
        activities=[greet],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Database (Event History)

Every Workflow execution produces an **event history** stored in the database:

```
WorkflowExecutionStarted
├── ActivityTaskScheduled
│   ├── ActivityTaskStarted
│   └── ActivityTaskCompleted
├── TimerStarted
│   └── TimerFired
└── WorkflowExecutionCompleted
```

This history enables:
- **Replay**: Reconstruct Workflow state after failure
- **Debugging**: Inspect every step of execution
- **Auditing**: Full record of what happened

### 4. Task Queues

Task Queues are named queues that connect Workers to the Temporal Cluster:

```
┌──────────┐     ┌─────────────┐     ┌──────────┐
│ Starter  │────►│ Task Queue  │────►│ Worker   │
│          │     │ "greeting"  │     │          │
└──────────┘     └─────────────┘     └──────────┘
```

- Workers **poll** a Task Queue for tasks
- Starters **specify** which Task Queue to route work to
- Multiple Workers can poll the **same** Task Queue for scalability

### 5. Temporal Web UI

The Web UI (default: `http://localhost:8233`) provides:

- List of all Workflow executions
- Workflow execution details and status
- Event history visualization
- Input/output inspection

## Communication Flow

1. **Client** sends a `StartWorkflow` request to the Temporal Cluster
2. Cluster creates a **Workflow Task** on the specified Task Queue
3. **Worker** picks up the task, executes the Workflow code
4. Workflow schedules an **Activity Task** on the Task Queue
5. Worker picks up the Activity Task, executes the Activity
6. Activity result is recorded in the **event history**
7. Workflow continues or completes

## Namespaces

Namespaces provide isolation for Workflows:

```python
client = await Client.connect("localhost:7233", namespace="default")
```

- `default` is the standard namespace for development
- Production systems use separate namespaces for different teams or services

## Best Practices

- Run multiple Workers for high availability
- Use separate Task Queues for different workload types
- Monitor Workflow execution through the Web UI
- Use namespaces to isolate environments

## Exercise

1. Start `temporal server start-dev`
2. Open the Web UI at `http://localhost:8233`
3. Explore the namespaces, Workflows, and Task Queues sections
4. Run a Workflow and observe it appear in the Web UI
