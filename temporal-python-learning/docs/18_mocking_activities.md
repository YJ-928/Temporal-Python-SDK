# Mocking Activities

## Overview

Mocking Activities allows you to test Workflow logic **without** calling real external services. You replace an Activity with a mock that returns predefined values, isolating the Workflow from its dependencies.

## Why Mock Activities?

| Concern | Without Mocking | With Mocking |
|---------|----------------|--------------|
| External services | Must be running | Not needed |
| Test speed | Slow (network calls) | Fast |
| Determinism | Flaky (service may be down) | Deterministic |
| Test isolation | Integration test | Unit test |

## Creating a Mock Activity

Define a standalone function with the same Activity name:

```python
from temporalio import activity
from shared import TranslationActivityInput, TranslationActivityOutput


@activity.defn(name="translate_term")
async def translate_term_mocked(input: TranslationActivityInput):
    if input.term == "hello":
        return TranslationActivityOutput("Bonjour")
    else:
        return TranslationActivityOutput("Au revoir")
```

The `name="translate_term"` parameter must match the original Activity's registered name.

## Using Mocked Activities in Tests

```python
import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from workflow import TranslationWorkflow
from shared import TranslationWorkflowInput


@activity.defn(name="translate_term")
async def translate_term_mocked_french(input: TranslationActivityInput):
    if input.term == "hello":
        return TranslationActivityOutput("Bonjour")
    else:
        return TranslationActivityOutput("Au revoir")


@pytest.mark.asyncio
async def test_successful_translation():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-translation-workflow",
            workflows=[TranslationWorkflow],
            activities=[translate_term_mocked_french],  # <-- Mock
        ):
            input = TranslationWorkflowInput("Pierre", "fr")
            output = await env.client.execute_workflow(
                TranslationWorkflow.run,
                input,
                id="test-translation-workflow-id",
                task_queue="test-translation-workflow",
            )
            assert "Bonjour, Pierre" == output.hello_message
            assert "Au revoir, Pierre" == output.goodbye_message
```

## Mocking for Failure Testing

Mock an Activity to simulate failures:

```python
from shared import Address, Distance


@activity.defn(name="get_distance")
async def get_distance_mocked(address: Address):
    return Distance(30)  # Returns distance outside delivery area


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

## Mixing Real and Mocked Activities

You can use some real Activities and some mocks in the same test:

```python
async with Worker(
    env.client,
    task_queue="test-queue",
    workflows=[PizzaOrderWorkflow],
    activities=[
        get_distance_mocked,       # Mocked
        activities.send_bill,      # Real
    ],
):
```

## Mock Pattern for Age Estimation

```python
from shared import EstimatorResponse


@activity.defn(name="retrieve_estimate")
async def estimate_age_mocked(input: str) -> EstimatorResponse:
    if input == "Stanislav":
        return EstimatorResponse(name="Stanislav", count=8928, age=21)
    else:
        return EstimatorResponse(name="Mason", count=1487, age=40)
```

## Best Practices

- Use `@activity.defn(name="...")` to match the original Activity name exactly
- Mock Activities for unit tests; use real Activities for integration tests
- Test both success and failure paths with mocks
- Keep mocked return values realistic
- Combine mocking with time skipping for fast, comprehensive tests

## Exercise

1. Create a mock Activity that returns a hardcoded translation
2. Write a test that uses the mock instead of a real translation service
3. Verify the Workflow produces the expected output
