"""
Pizza Order Debug Project — Activities

Activities for the pizza-order Workflow:
  - get_distance: Calculate delivery distance from the customer's postal code
  - send_bill: Produce an order confirmation after billing
"""

from temporalio import activity

from shared import Bill, Distance, OrderConfirmation, PizzaOrder


@activity.defn
async def get_distance(order: PizzaOrder) -> Distance:
    """Look up the delivery distance for a customer's postal code."""
    distances = {
        "10001": 10,
        "90210": 25,
        "60601": 15,
    }

    km = distances.get(order.address.postal_code)
    if km is None:
        raise ValueError(
            f"No delivery distance defined for postal code "
            f"'{order.address.postal_code}'"
        )
    activity.logger.info(
        f"Distance to {order.address.postal_code}: {km} km"
    )
    return Distance(kilometers=km)


@activity.defn
async def send_bill(bill: Bill) -> OrderConfirmation:
    """Simulate billing and return an order confirmation."""
    activity.logger.info(
        f"Billing customer {bill.customer_id}: "
        f"${bill.amount / 100:.2f} for order {bill.order_number}"
    )
    return OrderConfirmation(
        order_number=bill.order_number,
        status="CONFIRMED",
        confirmation_number=f"CONF-{bill.order_number}",
        billing_total=bill.amount,
        delivery_distance=0,  # Workflow will update this
    )
