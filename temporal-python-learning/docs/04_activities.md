# Activities

## What Is an Activity?

An Activity is a function that performs **non-deterministic work** — operations that interact with the outside world. Activities are where you put code for:

- HTTP/API calls
- Database reads/writes
- File system operations
- Sending emails or notifications
- Any operation with side effects

## Why Separate Activities from Workflows?

| Concern | Workflow | Activity |
|---------|----------|----------|
| Determinism | Must be deterministic | Can be non-deterministic |
| I/O | Not allowed | Allowed |
| Retries | Managed by Temporal | Automatic with retry policies |
| Replay | Replayed from history | Not replayed — result is cached |

When Temporal replays a Workflow, it does **not** re-execute Activities. Instead, it uses the recorded result from the event history.

## Defining an Activity

### Function-Based Activity

```python
from temporalio import activity


@activity.defn
async def greet(name: str) -> str:
    return f"Hello, {name}!"
```

### Class-Based Activity

Class-based Activities allow dependency injection (e.g., HTTP sessions, DB connections):

```python
import urllib.parse
from temporalio import activity


class TranslateActivities:
    def __init__(self, session):
        self.session = session

    @activity.defn
    async def greet_in_spanish(self, name: str) -> str:
        base = "http://localhost:9999/get-spanish-greeting"
        url = f"{base}?name={urllib.parse.quote(name)}"

        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.text()

    @activity.defn
    async def farewell_in_spanish(self, name: str) -> str:
        base = "http://localhost:9999/get-spanish-farewell"
        url = f"{base}?name={urllib.parse.quote(name)}"

        async with self.session.get(url) as response:
            response.raise_for_status()
            return await response.text()
```

## Executing Activities

### From a Workflow — Function-Based

```python
result = await workflow.execute_activity(
    greet,
    name,
    start_to_close_timeout=timedelta(seconds=5),
)
```

### From a Workflow — Class Method

```python
result = await workflow.execute_activity_method(
    TranslateActivities.greet_in_spanish,
    name,
    start_to_close_timeout=timedelta(seconds=5),
)
```

## Activity Timeouts

Every Activity execution requires at least one timeout:

| Timeout | Description |
|---------|-------------|
| `start_to_close_timeout` | Max time from Activity start to completion |
| `schedule_to_close_timeout` | Max time from scheduling to completion (includes queue wait) |
| `schedule_to_start_timeout` | Max time waiting in the Task Queue |
| `heartbeat_timeout` | Max time between heartbeat signals |

```python
await workflow.execute_activity(
    greet,
    name,
    start_to_close_timeout=timedelta(seconds=5),
    schedule_to_close_timeout=timedelta(seconds=30),
)
```

## Activity Logging

Use `activity.logger` inside Activities:

```python
@activity.defn
async def get_distance(self, address: Address) -> Distance:
    activity.logger.info("get_distance invoked")
    # ...
    activity.logger.info(f"get_distance complete: {distance}")
    return distance
```

## Activity Errors

Raise `ApplicationError` for business logic errors:

```python
from temporalio.exceptions import ApplicationError


@activity.defn
async def send_bill(self, bill: Bill) -> OrderConfirmation:
    if bill.amount < 0:
        raise ApplicationError(f"invalid charge amount: {bill.amount}")
    # ...
```

## Using Dataclasses for Input/Output

```python
from dataclasses import dataclass


@dataclass
class TranslationActivityInput:
    term: str
    language_code: str


@dataclass
class TranslationActivityOutput:
    translation: str


@activity.defn
async def translate_term(
    self, input: TranslationActivityInput
) -> TranslationActivityOutput:
    # ...
    return TranslationActivityOutput(translation="Bonjour")
```

## Best Practices

- Keep Activities focused on a single unit of work
- Use class-based Activities for dependency injection
- Always set appropriate timeouts
- Use `activity.logger` instead of `print()`
- Raise `ApplicationError` for expected failures
- Use dataclasses for structured input/output

## Exercise

Create a farewell Activity that:
1. Accepts a name
2. Calls an external service
3. Returns a farewell message

See [exercise_03_farewell_workflow.py](../exercises/exercise_03_farewell_workflow.py)
