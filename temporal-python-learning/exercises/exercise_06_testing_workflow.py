"""
Exercise 06 — Testing Workflow

Objective:
    Write tests for a Workflow and its Activities using Temporal's test framework.

Concepts:
    - ActivityEnvironment for isolated Activity tests
    - WorkflowEnvironment with time skipping
    - Mocked Activities for unit testing
    - pytest.mark.asyncio and parametrize

Instructions:
    Run tests: pytest exercise_06_testing_workflow.py -v

Expected output:
    All tests pass.
"""

import asyncio
from dataclasses import dataclass
from datetime import timedelta

import pytest
from temporalio import activity, workflow
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment
from temporalio.worker import Worker


# --- Shared Data ---

TASK_QUEUE = "test-order-tasks"


@dataclass
class OrderInput:
    customer_name: str
    item: str
    quantity: int


@dataclass
class OrderResult:
    order_id: str
    status: str
    total: int


# --- Activities ---

class OrderActivities:
    @activity.defn
    async def calculate_total(self, input: OrderInput) -> int:
        """Calculate order total."""
        price_per_item = 1000  # $10.00 in cents
        total = price_per_item * input.quantity
        activity.logger.info(f"Total for {input.quantity}x {input.item}: {total}")
        return total

    @activity.defn
    async def place_order(self, input: OrderInput) -> OrderResult:
        """Place the order and return confirmation."""
        total = 1000 * input.quantity
        if total <= 0:
            raise ApplicationError("Invalid order total")
        return OrderResult(
            order_id="ORD-001",
            status="CONFIRMED",
            total=total,
        )


# --- Workflow ---

@workflow.defn
class OrderWorkflow:
    @workflow.run
    async def run(self, input: OrderInput) -> OrderResult:
        total = await workflow.execute_activity_method(
            OrderActivities.calculate_total,
            input,
            start_to_close_timeout=timedelta(seconds=5),
        )
        workflow.logger.info(f"Calculated total: {total}")

        # Short timer to simulate processing delay
        await asyncio.sleep(3)

        result = await workflow.execute_activity_method(
            OrderActivities.place_order,
            input,
            start_to_close_timeout=timedelta(seconds=5),
        )
        return result


# --- Activity Tests ---

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_data, expected_total",
    [
        (OrderInput(customer_name="Alice", item="Pizza", quantity=2), 2000),
        (OrderInput(customer_name="Bob", item="Pizza", quantity=5), 5000),
        (OrderInput(customer_name="Carol", item="Pizza", quantity=1), 1000),
    ],
)
async def test_calculate_total(input_data: OrderInput, expected_total: int):
    """Test that calculate_total returns the correct total."""
    env = ActivityEnvironment()
    activities = OrderActivities()
    result = await env.run(activities.calculate_total, input_data)
    assert result == expected_total


@pytest.mark.asyncio
async def test_place_order_success():
    """Test that place_order returns a confirmation."""
    env = ActivityEnvironment()
    activities = OrderActivities()
    input_data = OrderInput(customer_name="Alice", item="Pizza", quantity=2)
    result = await env.run(activities.place_order, input_data)
    assert result.order_id == "ORD-001"
    assert result.status == "CONFIRMED"
    assert result.total == 2000


@pytest.mark.asyncio
async def test_place_order_invalid_quantity():
    """Test that place_order raises an error for zero quantity."""
    env = ActivityEnvironment()
    activities = OrderActivities()
    input_data = OrderInput(customer_name="Alice", item="Pizza", quantity=0)
    with pytest.raises(ApplicationError) as exc_info:
        await env.run(activities.place_order, input_data)
    assert "Invalid order total" in str(exc_info.value)


# --- Workflow Tests ---

@pytest.mark.asyncio
async def test_order_workflow_success():
    """Test the full OrderWorkflow with time skipping."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        activities = OrderActivities()
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[OrderWorkflow],
            activities=[activities.calculate_total, activities.place_order],
        ):
            input_data = OrderInput(customer_name="Alice", item="Pizza", quantity=3)
            result = await env.client.execute_workflow(
                OrderWorkflow.run,
                input_data,
                id="test-order-workflow",
                task_queue=TASK_QUEUE,
            )
            assert result.order_id == "ORD-001"
            assert result.status == "CONFIRMED"
            assert result.total == 3000


# --- Mocked Activity Test ---

@activity.defn(name="calculate_total")
async def calculate_total_mocked(input: OrderInput) -> int:
    """Mock that returns a fixed total."""
    return 9999


@pytest.mark.asyncio
async def test_order_workflow_with_mock():
    """Test OrderWorkflow with a mocked Activity."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        activities = OrderActivities()
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[OrderWorkflow],
            activities=[calculate_total_mocked, activities.place_order],
        ):
            input_data = OrderInput(customer_name="Alice", item="Pizza", quantity=3)
            result = await env.client.execute_workflow(
                OrderWorkflow.run,
                input_data,
                id="test-order-workflow-mocked",
                task_queue=TASK_QUEUE,
            )
            assert result.status == "CONFIRMED"
