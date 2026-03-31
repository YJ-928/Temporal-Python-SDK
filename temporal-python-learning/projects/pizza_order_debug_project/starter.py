"""
Pizza Order Debug Project — Starter

Usage:
    python starter.py
"""

import asyncio

from temporalio.client import Client

from pizza_workflow import PizzaOrderWorkflow, TASK_QUEUE
from shared import Address, Customer, Pizza, PizzaOrder


async def main():
    client = await Client.connect("localhost:7233")

    order = PizzaOrder(
        order_number="ORD-200",
        customer=Customer(
            customer_id=42,
            name="Alice Johnson",
            email="alice@example.com",
            phone="555-0100",
        ),
        items=[
            Pizza(description="Margherita", price=1500),
            Pizza(description="Pepperoni", price=1800),
        ],
        address=Address(
            line1="123 Main St",
            line2="Apt 4",
            city="New York",
            state="NY",
            postal_code="10001",
        ),
        is_delivery=True,
    )

    print(f"Starting PizzaOrderWorkflow for order {order.order_number}")
    result = await client.execute_workflow(
        PizzaOrderWorkflow.run,
        order,
        id=f"pizza-{order.order_number}",
        task_queue=TASK_QUEUE,
    )
    print(f"Order confirmed: {result}")


if __name__ == "__main__":
    asyncio.run(main())
