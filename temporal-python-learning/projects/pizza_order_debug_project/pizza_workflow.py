"""
Pizza Order Debug Project — Workflow

PizzaOrderWorkflow:
    1. Calculate delivery distance via get_distance
    2. Compute total (items + delivery charge)
    3. Send bill via send_bill
    4. Return confirmation with delivery distance
"""

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from pizza_activities import get_distance, send_bill
    from shared import Bill, OrderConfirmation, PizzaOrder

TASK_QUEUE = "pizza-order-tasks"


@workflow.defn
class PizzaOrderWorkflow:
    @workflow.run
    async def run(self, order: PizzaOrder) -> OrderConfirmation:
        distance = await workflow.execute_activity(
            get_distance,
            order,
            start_to_close_timeout=timedelta(seconds=5),
        )
        workflow.logger.info(
            f"Delivery distance for order {order.order_number}: "
            f"{distance.kilometers} km"
        )

        item_total = sum(item.price for item in order.items)
        delivery_charge = distance.kilometers * 100  # $1 per km
        total = item_total + delivery_charge

        bill = Bill(
            customer_id=order.customer.customer_id,
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
