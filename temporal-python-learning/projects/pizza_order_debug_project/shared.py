"""
Pizza Order Debug Project — Shared Data Classes

All dataclasses used by the pizza-order Workflow and Activities.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Address:
    line1: str
    line2: str
    city: str
    state: str
    postal_code: str


@dataclass
class Customer:
    customer_id: int
    name: str
    email: str
    phone: str


@dataclass
class Pizza:
    description: str
    price: int  # cents


@dataclass
class PizzaOrder:
    order_number: str
    customer: Customer
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
