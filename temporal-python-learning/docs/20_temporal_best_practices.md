# Temporal Best Practices

## Workflow Best Practices

### 1. Keep Workflows Deterministic

Workflows must produce the same result when replayed. Avoid:

```python
# BAD — Non-deterministic
import random
result = random.random()

import datetime
now = datetime.datetime.now()

import requests
response = requests.get("https://api.example.com")
```

Use Temporal-safe alternatives:

```python
# GOOD — Deterministic
now = workflow.now()                    # Temporal-safe time
result = await workflow.execute_activity(...)  # Delegate I/O to Activities
```

### 2. Use Activities for All I/O

```python
# BAD — I/O in Workflow
@workflow.defn
class BadWorkflow:
    @workflow.run
    async def run(self):
        response = await aiohttp.get("https://api.example.com")  # NO!

# GOOD — I/O in Activity
@workflow.defn
class GoodWorkflow:
    @workflow.run
    async def run(self):
        result = await workflow.execute_activity(
            fetch_data, start_to_close_timeout=timedelta(seconds=10)
        )
```

### 3. Use Dataclasses for Input/Output

```python
from dataclasses import dataclass


@dataclass
class OrderInput:
    customer_id: int
    items: list


@dataclass
class OrderOutput:
    order_number: str
    status: str
```

### 4. Set Timeouts on Every Activity

```python
await workflow.execute_activity(
    process_order,
    order,
    start_to_close_timeout=timedelta(seconds=30),
)
```

### 5. Use Workflow Logging

```python
workflow.logger.info(f"Processing order {order.id}")
```

## Activity Best Practices

### 1. Use Class-Based Activities for Dependencies

```python
class OrderActivities:
    def __init__(self, db_session, http_session):
        self.db = db_session
        self.http = http_session

    @activity.defn
    async def process_order(self, order: Order) -> OrderResult:
        ...
```

### 2. Use Activity Logging

```python
@activity.defn
async def process_order(self, order: Order) -> OrderResult:
    activity.logger.info(f"Processing order {order.id}")
    ...
    activity.logger.info(f"Order processed: {result}")
    return result
```

### 3. Raise ApplicationError for Business Errors

```python
from temporalio.exceptions import ApplicationError

@activity.defn
async def validate_order(self, order: Order):
    if order.total < 0:
        raise ApplicationError("Invalid order total", non_retryable=True)
```

### 4. Configure Appropriate Retry Policies

```python
retry_policy = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=5,
)
```

## Worker Best Practices

### 1. Register All Required Workflows and Activities

```python
worker = Worker(
    client,
    task_queue=TASK_QUEUE_NAME,
    workflows=[OrderWorkflow],
    activities=[activities.process_order, activities.send_confirmation],
)
```

### 2. Use Constants for Task Queue Names

```python
# shared.py
TASK_QUEUE_NAME = "order-tasks"
WORKFLOW_ID_PREFIX = "order-workflow-"
```

### 3. Configure Logging

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### 4. Run Multiple Workers for High Availability

```bash
# Terminal 1
python worker.py

# Terminal 2
python worker.py
```

## Testing Best Practices

### 1. Test Activities Independently

```python
async def test_activity():
    env = ActivityEnvironment()
    result = await env.run(activities.process_order, order)
    assert result.status == "SUCCESS"
```

### 2. Use Time Skipping for Workflow Tests

```python
async with await WorkflowEnvironment.start_time_skipping() as env:
    ...
```

### 3. Mock Activities for Unit Tests

```python
@activity.defn(name="process_order")
async def process_order_mocked(order):
    return OrderResult(status="SUCCESS")
```

### 4. Test Both Success and Failure

```python
async def test_success():
    ...

async def test_failure_invalid_input():
    with pytest.raises(WorkflowFailureError):
        ...
```

## Code Organization Best Practices

### Recommended File Structure

```
project/
├── shared.py      # Dataclasses, constants
├── activities.py  # Activity definitions
├── workflow.py    # Workflow definitions
├── worker.py      # Worker setup
├── starter.py     # Workflow starter
└── tests/
    ├── test_activities.py
    ├── test_workflow.py
    └── test_workflow_with_mocks.py
```

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Workflow class | PascalCase | `PizzaOrderWorkflow` |
| Activity method | snake_case | `get_distance` |
| Task Queue | kebab-case string | `"pizza-tasks"` |
| Workflow ID | descriptive with prefix | `"pizza-workflow-order-XD001"` |

## Summary Checklist

- [ ] Workflows are deterministic
- [ ] All I/O is in Activities
- [ ] Timeouts set on every Activity
- [ ] Dataclasses for input/output
- [ ] Retry policies configured
- [ ] Logging with `workflow.logger` and `activity.logger`
- [ ] Tests with `ActivityEnvironment` and `WorkflowEnvironment`
- [ ] Mocked Activities for unit tests
- [ ] Time skipping for timer tests
- [ ] Multiple Workers for production
- [ ] Meaningful Workflow IDs
- [ ] Constants for Task Queue names
