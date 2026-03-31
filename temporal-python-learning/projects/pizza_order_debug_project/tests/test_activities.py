"""
Tests for pizza-order Activities.

Run with:
    pytest tests/ -v
"""

import pytest
from temporalio.testing import ActivityEnvironment

from pizza_activities import get_distance, send_bill
from shared import Address, Bill, Customer, Pizza, PizzaOrder


def make_order(postal_code: str = "10001") -> PizzaOrder:
    return PizzaOrder(
        order_number="ORD-TEST",
        customer=Customer(
            customer_id=1,
            name="Test User",
            email="test@example.com",
            phone="555-0000",
        ),
        items=[Pizza(description="Cheese", price=1200)],
        address=Address(
            line1="1 Test Rd",
            line2="",
            city="Test City",
            state="TS",
            postal_code=postal_code,
        ),
        is_delivery=True,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "postal_code, expected_km",
    [
        ("10001", 10),
        ("90210", 25),
        ("60601", 15),
    ],
)
async def test_get_distance(postal_code: str, expected_km: int):
    env = ActivityEnvironment()
    order = make_order(postal_code)
    result = await env.run(get_distance, order)
    assert result.kilometers == expected_km


@pytest.mark.asyncio
async def test_get_distance_unknown_postal_code():
    env = ActivityEnvironment()
    order = make_order("00000")
    with pytest.raises(ValueError, match="No delivery distance defined"):
        await env.run(get_distance, order)


@pytest.mark.asyncio
async def test_send_bill():
    env = ActivityEnvironment()
    bill = Bill(
        customer_id=1,
        order_number="ORD-TEST",
        description="Test order",
        amount=2200,
    )
    result = await env.run(send_bill, bill)
    assert result.status == "CONFIRMED"
    assert result.billing_total == 2200
    assert result.confirmation_number == "CONF-ORD-TEST"
