"""
Exercise 07 — Debug Activity

Objective:
    Identify and fix a bug in a pizza-order Activity that causes the Workflow to fail.

Concepts:
    - Reading Workflow error output
    - Debugging Activity logic
    - Understanding retry behaviour
    - Using tests to verify fixes

Background:
    The PizzaOrderWorkflow calls `get_distance` then `send_bill`. The `get_distance`
    Activity has a bug: it swaps the address lookup causing a KeyError. Fix the bug
    so the Workflow completes successfully.

Instructions:
    1. Run the worker:  python exercise_07_debug_activity.py worker
    2. In another terminal, start the workflow:  python exercise_07_debug_activity.py starter
    3. Observe the failure, then fix the bug in `get_distance`.
    4. Verify with:  pytest exercise_07_debug_activity.py -v -k test

Expected result after fix:
    The Workflow succeeds with an OrderConfirmation and all tests pass.
"""

import asyncio
import sys
from dataclasses import dataclass
from datetime import timedelta
from typing import List

import pytest
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment
from temporalio.worker import Worker

TASK_QUEUE = "pizza-tasks"


# --- Shared Data ---

@dataclass
class Address:
    line1: str
    line2: str
    city: str
    state: str
    postal_code: str


@dataclass
class Pizza:
    description: str
    price: int  # cents


@dataclass
class PizzaOrder:
    order_number: str
    customer_id: int
    items: List[Pizza]
    address: Address
    is_delivery: bool


@dataclass
class Distance:
    kilometers: int


@dataclass
class Bill:
    customer_id: int
    order_number: str
    description: str
    amount: int


@dataclass
class OrderConfirmation:
    order_number: str
    status: str
    confirmation_number: str
    billing_total: int
    delivery_distance: int


# --- Activities (contains a bug) ---

@activity.defn
async def get_distance(order: PizzaOrder) -> Distance:
    """Calculate delivery distance from address.

    BUG: The address lookup dictionary keys are swapped.
    Fix: correct the keys so that the customer's postal code is found.
    """
    distances = {
        # BUG: Keys are the wrong way round — the customer address
        # postal code should be the *key*, not the value.
        "10001": 10,  # Should map customer postal code → distance
        "90210": 25,
        "60601": 15,
    }

    # This will raise KeyError if the postal code is not a key
    km = distances.get(order.address.postal_code, None)
    if km is None:
        raise Exception(
            f"Unable to find distance for postal code {order.address.postal_code}"
        )
    return Distance(kilometers=km)


@activity.defn
async def send_bill(bill: Bill) -> OrderConfirmation:
    """Simulate sending a bill and returning confirmation."""
    activity.logger.info(
        f"Sending bill #{bill.order_number} for ${bill.amount / 100:.2f}"
    )
    return OrderConfirmation(
        order_number=bill.order_number,
        status="CONFIRMED",
        confirmation_number=f"CONF-{bill.order_number}",
        billing_total=bill.amount,
        delivery_distance=0,
    )


# --- Workflow ---

@workflow.defn
class PizzaOrderWorkflow:
    @workflow.run
    async def run(self, order: PizzaOrder) -> OrderConfirmation:
        # Step 1: Calculate delivery distance
        distance = await workflow.execute_activity(
            get_distance,
            order,
            start_to_close_timeout=timedelta(seconds=5),
        )
        workflow.logger.info(f"Delivery distance: {distance.kilometers} km")

        # Step 2: Build and send the bill
        item_total = sum(item.price for item in order.items)
        delivery_charge = distance.kilometers * 100  # $1 per km
        total = item_total + delivery_charge

        bill = Bill(
            customer_id=order.customer_id,
            order_number=order.order_number,
            description="Pizza order delivery",
            amount=total,
        )
        confirmation = await workflow.execute_activity(
            send_bill,
            bill,
            start_to_close_timeout=timedelta(seconds=5),
        )
        confirmation.delivery_distance = distance.kilometers
        return confirmation


# --- Test Helpers ---

def make_sample_order(postal_code: str = "10001") -> PizzaOrder:
    return PizzaOrder(
        order_number="ORD-100",
        customer_id=42,
        items=[
            Pizza(description="Margherita", price=1500),
            Pizza(description="Pepperoni", price=1800),
        ],
        address=Address(
            line1="123 Main St",
            line2="Apt 4",
            city="New York",
            state="NY",
            postal_code=postal_code,
        ),
        is_delivery=True,
    )


# --- Activity Tests ---

@pytest.mark.asyncio
async def test_get_distance_success():
    """Test get_distance returns correct distance for known postal code."""
    env = ActivityEnvironment()
    order = make_sample_order("10001")
    result = await env.run(get_distance, order)
    assert result.kilometers == 10


@pytest.mark.asyncio
async def test_get_distance_unknown_postal_code():
    """Test that an unknown postal code raises an exception."""
    env = ActivityEnvironment()
    order = make_sample_order("00000")
    with pytest.raises(Exception, match="Unable to find distance"):
        await env.run(get_distance, order)


@pytest.mark.asyncio
async def test_send_bill():
    """Test that send_bill returns a correct confirmation."""
    env = ActivityEnvironment()
    bill = Bill(
        customer_id=42,
        order_number="ORD-100",
        description="Pizza order delivery",
        amount=3300,
    )
    result = await env.run(send_bill, bill)
    assert result.status == "CONFIRMED"
    assert result.billing_total == 3300


# --- Workflow Test ---

@pytest.mark.asyncio
async def test_pizza_order_workflow():
    """Integration test for the full PizzaOrderWorkflow."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[PizzaOrderWorkflow],
            activities=[get_distance, send_bill],
        ):
            order = make_sample_order("10001")
            result = await env.client.execute_workflow(
                PizzaOrderWorkflow.run,
                order,
                id="test-pizza-order",
                task_queue=TASK_QUEUE,
            )
            assert result.status == "CONFIRMED"
            assert result.delivery_distance == 10
            # 1500 + 1800 = 3300 for items, 10 * 100 = 1000 delivery
            assert result.billing_total == 4300


# --- Worker / Starter CLI ---

async def run_worker():
    client = await Client.connect("localhost:7233")
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[PizzaOrderWorkflow],
        activities=[get_distance, send_bill],
    )
    print("Pizza worker started. Ctrl-C to stop.")
    await worker.run()


async def run_starter():
    client = await Client.connect("localhost:7233")
    order = make_sample_order("10001")
    print(f"Starting PizzaOrderWorkflow for order {order.order_number}")
    result = await client.execute_workflow(
        PizzaOrderWorkflow.run,
        order,
        id=f"pizza-order-{order.order_number}",
        task_queue=TASK_QUEUE,
    )
    print(f"Order result: {result}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        asyncio.run(run_worker())
    else:
        asyncio.run(run_starter())
