# Task Queues

## What Is a Task Queue?

A Task Queue is a **named queue** that acts as a routing mechanism between clients (starters) and Workers. When a Workflow is started, it specifies a Task Queue. Workers poll that same Task Queue to pick up work.

## How Task Queues Work

```
┌──────────┐                    ┌──────────┐
│ Starter  │──start_workflow──►│          │
│          │  task_queue=       │  Temporal│
└──────────┘  "greeting"       │  Cluster │
                               │          │
┌──────────┐                   │          │
│ Worker   │◄──poll────────────│          │
│          │  task_queue=       │          │
└──────────┘  "greeting"       └──────────┘
```

## Task Queue in a Starter

```python
handle = await client.start_workflow(
    GreetSomeone.run,
    "Alice",
    id="greeting-workflow",
    task_queue="greeting-tasks",    # <-- Task Queue name
)
```

## Task Queue in a Worker

```python
worker = Worker(
    client,
    task_queue="greeting-tasks",    # <-- Must match the starter
    workflows=[GreetSomeone],
    activities=[greet],
)
```

## Types of Tasks

| Task Type | Description |
|-----------|-------------|
| **Workflow Task** | Instructs a Worker to execute a Workflow function |
| **Activity Task** | Instructs a Worker to execute an Activity function |

Both types flow through the same Task Queue.

## Multiple Task Queues

You can use different Task Queues for different workloads:

```python
# Worker 1 — handles greeting tasks
worker1 = Worker(client, task_queue="greeting-tasks", ...)

# Worker 2 — handles pizza order tasks
worker2 = Worker(client, task_queue="pizza-tasks", ...)
```

This enables:
- **Workload isolation**: Different tasks on different queues
- **Resource allocation**: Assign specific hardware to specific queues
- **Priority management**: Prioritize certain queues over others

## Task Queue Properties

- Task Queues are **created on demand** — no manual setup required
- They are **lightweight** and managed by the Temporal Cluster
- Tasks are delivered in a **fair-dispatch** manner
- Unmatched tasks **wait** in the queue until a Worker polls

## Sticky Task Queues

Temporal uses "sticky" Task Queues internally to optimize Workflow replay by routing subsequent tasks to the same Worker that previously executed the Workflow. This caching avoids full replays.

## Best Practices

- Use descriptive Task Queue names: `"pizza-tasks"`, `"translation-tasks"`
- Keep the Task Queue name consistent between Workers and Starters
- Use separate Task Queues for different types of work
- Define Task Queue names as constants in a shared module:

```python
# shared.py
TASK_QUEUE_NAME = "pizza-tasks"
```

## Exercise

1. Run a Workflow with a specific Task Queue name
2. Start a Worker with a **different** Task Queue name
3. Observe that the Workflow does not execute
4. Fix the Worker's Task Queue name and watch it execute
