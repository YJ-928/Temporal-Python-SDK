"""
Tests for PizzaOrderWorkflow with mocked Activities.

Demonstrates how to replace a real Activity with a mock to test
Workflow logic in isolation.

Run with:
    pytest tests/ -v
"""

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from pizza_activities import send_bill
from pizza_workflow import PizzaOrderWorkflow, TASK_QUEUE
from shared import Address, Customer, Distance, Pizza, PizzaOrder


# --- Mocked Activity ---

@activity.defn(name="get_distance")
async def get_distance_mocked(order: PizzaOrder) -> Distance:
    """Mock that always returns 5 km."""
    return Distance(kilometers=5)


def make_order() -> PizzaOrder:
    return PizzaOrder(
        order_number="ORD-MOCK",
        customer=Customer(
            customer_id=3,
            name="Mock User",
            email="mock@example.com",
            phone="555-9999",
        ),
        items=[Pizza(description="Veggie", price=1400)],
        address=Address(
            line1="789 Elm St",
            line2="",
            city="Chicago",
            state="IL",
            postal_code="60601",
        ),
        is_delivery=True,
    )


@pytest.mark.asyncio
async def test_pizza_order_workflow_with_mocked_distance():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[PizzaOrderWorkflow],
            activities=[get_distance_mocked, send_bill],
        ):
            order = make_order()
            result = await env.client.execute_workflow(
                PizzaOrderWorkflow.run,
                order,
                id="test-pizza-mock",
                task_queue=TASK_QUEUE,
            )
            assert result.status == "CONFIRMED"
            assert result.delivery_distance == 5
            # items: 1400, delivery: 5 * 100 = 500
            assert result.billing_total == 1900
