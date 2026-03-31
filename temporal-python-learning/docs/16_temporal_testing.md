# Temporal Testing

## Overview

The Temporal Python SDK provides testing utilities to test Workflows and Activities without running a full Temporal Cluster. Two key environments are available:

- `ActivityEnvironment` — tests Activities in isolation
- `WorkflowEnvironment` — tests Workflows with a lightweight server

## Testing Activities

### ActivityEnvironment

`ActivityEnvironment` runs Activities outside of Temporal, providing the Activity context (`activity.logger`, `activity.info`, etc.):

```python
import pytest
from temporalio.testing import ActivityEnvironment


@pytest.mark.asyncio
async def test_greet_activity():
    activity_environment = ActivityEnvironment()
    result = await activity_environment.run(greet, "Alice")
    assert result == "Hello, Alice!"
```

### Testing Class-Based Activities

```python
from activities import PizzaOrderActivities
from shared import Address, Distance


@pytest.mark.asyncio
async def test_get_distance():
    activity_environment = ActivityEnvironment()
    activities = PizzaOrderActivities()

    address = Address(
        line1="701 Mission Street",
        line2="Apartment 9C",
        city="San Francisco",
        state="CA",
        postal_code="94104",
    )

    result = await activity_environment.run(activities.get_distance, address)
    assert result == Distance(20)
```

### Parametrized Activity Tests

```python
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input, output",
    [
        (
            Address(line1="701 Mission Street", line2="Apartment 9C",
                    city="San Francisco", state="CA", postal_code="94104"),
            Distance(20),
        ),
        (
            Address(line1="917 Delores Street", line2="",
                    city="San Francisco", state="CA", postal_code="94104"),
            Distance(8),
        ),
    ],
)
async def test_get_distance(input, output):
    activity_environment = ActivityEnvironment()
    activities = PizzaOrderActivities()
    assert output == await activity_environment.run(activities.get_distance, input)
```

### Testing Error Cases

```python
@pytest.mark.asyncio
async def test_send_bill_fails_negative_amount():
    bill = Bill(
        customer_id=21974,
        order_number="QU812",
        description="1 large supreme pizza",
        amount=-1000,
    )
    with pytest.raises(Exception) as e:
        activity_environment = ActivityEnvironment()
        activities = PizzaOrderActivities()
        await activity_environment.run(activities.send_bill, bill)
    assert "invalid charge amount" in str(e)
```

## Testing Workflows

### WorkflowEnvironment

`WorkflowEnvironment` starts a lightweight Temporal server for testing:

```python
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker


@pytest.mark.asyncio
async def test_successful_pizza_order():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        activities = PizzaOrderActivities()
        async with Worker(
            env.client,
            task_queue="test-pizza-order",
            workflows=[PizzaOrderWorkflow],
            activities=[activities.get_distance, activities.send_bill],
        ):
            order = create_pizza_order()
            confirmation = await env.client.execute_workflow(
                PizzaOrderWorkflow.order_pizza,
                order,
                id="test-pizza-order-id",
                task_queue="test-pizza-order",
            )

            assert "XD001" == confirmation.order_number
            assert "SUCCESS" == confirmation.status
```

### Testing Workflow Failures

```python
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import ApplicationError


@pytest.mark.asyncio
async def test_failed_pizza_order_outside_delivery():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        with pytest.raises(WorkflowFailureError) as e:
            activities = PizzaOrderActivities()
            async with Worker(
                env.client,
                task_queue="test-pizza-order",
                workflows=[PizzaOrderWorkflow],
                activities=[get_distance_mocked, activities.send_bill],
            ):
                order = create_pizza_order()
                await env.client.execute_workflow(
                    PizzaOrderWorkflow.order_pizza,
                    order,
                    id="test-pizza-order-id",
                    task_queue="test-pizza-order",
                )
        assert isinstance(e.value.cause, ApplicationError)
        assert "customer lives outside the service area" == str(e.value.cause)
```

## Running Tests

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_activities.py -v

# Run specific test
pytest tests/test_activities.py::test_get_distance -v
```

## pytest-asyncio Configuration

Temporal tests are async. Use `pytest-asyncio`:

```ini
# pyproject.toml or pytest.ini
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Or use the decorator:

```python
@pytest.mark.asyncio
async def test_example():
    ...
```

## Best Practices

- Test Activities independently using `ActivityEnvironment`
- Test Workflows using `WorkflowEnvironment.start_time_skipping()`
- Use parametrized tests for multiple input/output combinations
- Test both success and failure cases
- Use mocked Activities for unit testing Workflows
- Use real Activities for integration testing

## Exercise

Write tests for:
1. An Activity that calculates a distance
2. A Workflow that processes an order

See [exercise_06_testing_workflow.py](../exercises/exercise_06_testing_workflow.py)
