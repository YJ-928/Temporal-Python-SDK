# Async vs Sync Activities

## Overview

The Temporal Python SDK supports both **async** and **sync** Activity definitions. Understanding when to use each is important for performance and correctness.

## Async Activities

Async Activities use Python's `asyncio` and are the recommended approach:

```python
from temporalio import activity


@activity.defn
async def fetch_data(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
```

### When to Use Async Activities

- HTTP calls using `aiohttp`
- Any I/O-bound operation
- When you need to run multiple operations concurrently
- When using async libraries

### Advantages

- Non-blocking I/O
- Better concurrency — multiple Activities can run on a single thread
- Works naturally with `asyncio`-based libraries

## Sync Activities

Sync Activities use regular (non-async) functions:

```python
import requests
from temporalio import activity


@activity.defn
def fetch_data_sync(url: str) -> str:
    response = requests.get(url)
    return response.text
```

### When to Use Sync Activities

- CPU-bound operations
- Libraries that only support synchronous I/O
- Legacy code integration

### How Sync Activities Are Executed

Temporal runs sync Activities in a **thread pool** to avoid blocking the event loop. This is handled automatically by the Worker.

## Comparing Async vs Sync

| Aspect | Async | Sync |
|--------|-------|------|
| Definition | `async def` | `def` |
| Execution | Event loop | Thread pool |
| I/O model | Non-blocking | Blocking |
| Concurrency | High (many on one thread) | Limited by thread pool size |
| Libraries | `aiohttp`, `asyncpg` | `requests`, `psycopg2` |
| Recommended | Yes (default choice) | When necessary |

## Mixing Async and Sync Activities

You can register both async and sync Activities on the same Worker:

```python
worker = Worker(
    client,
    task_queue="mixed-tasks",
    workflows=[MyWorkflow],
    activities=[
        fetch_data,          # async
        compute_heavy_task,  # sync
    ],
)
```

## Worker Thread Pool Configuration

For sync Activities, you can configure the thread pool:

```python
from concurrent.futures import ThreadPoolExecutor

worker = Worker(
    client,
    task_queue="my-tasks",
    workflows=[MyWorkflow],
    activities=[compute_heavy_task],
    activity_executor=ThreadPoolExecutor(max_workers=10),
)
```

## Best Practices

- Default to async Activities
- Use sync Activities only when required by the library or computation type
- Configure thread pool size for sync-heavy workloads
- Avoid mixing blocking I/O in async Activities — use `asyncio.to_thread()` if needed
- Use `aiohttp` instead of `requests` for HTTP calls in async Activities

## Exercise

1. Create an async Activity that fetches data from an API
2. Create a sync Activity that performs a CPU-bound calculation
3. Register both on the same Worker and observe execution
