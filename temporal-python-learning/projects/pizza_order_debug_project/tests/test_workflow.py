"""
Tests for the PizzaOrderWorkflow (integration with real Activities).

Run with:
    pytest tests/ -v
"""

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from pizza_activities import get_distance, send_bill
from pizza_workflow import PizzaOrderWorkflow, TASK_QUEUE
from shared import Address, Customer, Pizza, PizzaOrder


def make_order() -> PizzaOrder:
    return PizzaOrder(
        order_number="ORD-INT",
        customer=Customer(
            customer_id=2,
            name="Integration",
            email="int@example.com",
            phone="555-1111",
        ),
        items=[
            Pizza(description="Margherita", price=1500),
            Pizza(description="Pepperoni", price=1800),
        ],
        address=Address(
            line1="456 Oak Ave",
            line2="",
            city="Beverly Hills",
            state="CA",
            postal_code="90210",
        ),
        is_delivery=True,
    )


@pytest.mark.asyncio
async def test_pizza_order_workflow():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[PizzaOrderWorkflow],
            activities=[get_distance, send_bill],
        ):
            order = make_order()
            result = await env.client.execute_workflow(
                PizzaOrderWorkflow.run,
                order,
                id="test-pizza-int",
                task_queue=TASK_QUEUE,
            )
            assert result.status == "CONFIRMED"
            assert result.delivery_distance == 25
            # items: 1500 + 1800 = 3300, delivery: 25 * 100 = 2500
            assert result.billing_total == 5800
