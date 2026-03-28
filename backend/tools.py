"""
LangChain tools for the customer support agent.

Data source is controlled by the USE_SHOPIFY environment variable:
  USE_SHOPIFY=true  → live data from Shopify Admin API (kviyengars.myshopify.com)
  USE_SHOPIFY=false → mock_db (demo / local dev, default)
"""

import os
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

_USE_SHOPIFY = os.getenv("USE_SHOPIFY", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Data-source helpers — swap between Shopify and mock
# ---------------------------------------------------------------------------

def _get_order(order_id: str) -> dict | None:
    if _USE_SHOPIFY:
        from shopify_client import get_order
        return get_order(order_id)
    from mock_db import get_order
    return get_order(order_id)


def _get_orders_by_name(customer_name: str) -> list:
    if _USE_SHOPIFY:
        from shopify_client import get_orders_by_name
        return get_orders_by_name(customer_name)
    from mock_db import get_orders_by_name
    return get_orders_by_name(customer_name)


def _create_return_ticket(order_id: str, reason: str):
    if _USE_SHOPIFY:
        from shopify_client import create_return_ticket
        return create_return_ticket(order_id, reason)
    from mock_db import create_return_ticket
    return create_return_ticket(order_id, reason)


def _extend_return_window(order_id: str) -> None:
    if _USE_SHOPIFY:
        from shopify_client import extend_return_window_for_order
        extend_return_window_for_order(order_id)
    else:
        from mock_db import ORDERS
        ORDERS[order_id.upper()]["return_eligible"] = True


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@tool
def lookup_order(order_id: str) -> str:
    """Look up an order by order ID (or Shopify order name like #1001).
    Returns full details: product, amount, delivery date, return eligibility."""
    order = _get_order(order_id)
    if not order:
        return f"Order {order_id} not found. Please check the order number."
    eligibility = "eligible for return" if order["return_eligible"] else "NOT eligible (return window expired)"
    return (
        f"Order {order_id} belongs to {order['customer_name']}. "
        f"Product: {order['product']}, Amount: ₹{order['amount']}. "
        f"Status: {order['status']}, Delivery date: {order['delivery_date']}. "
        f"Return: {eligibility}."
    )


@tool
def get_order_status(order_id: str) -> str:
    """Get the current status of an order — pending, shipped,
    out for delivery, delivered, or cancelled."""
    order = _get_order(order_id)
    if not order:
        return f"Order {order_id} not found."
    return (
        f"Order {order_id} ({order['product']}) is currently: {order['status']}. "
        f"Delivery date: {order['delivery_date']}."
    )


@tool
def get_order_amount(order_id: str) -> str:
    """Get the amount paid for a specific order using order ID."""
    order = _get_order(order_id)
    if not order:
        return f"Order {order_id} not found."
    return f"The amount paid for Order {order_id} ({order['product']}) is ₹{order['amount']}."


@tool
def get_amount_by_name(customer_name: str) -> str:
    """Get the amount paid for all orders using the customer's name
    instead of order ID."""
    orders = _get_orders_by_name(customer_name)
    if not orders:
        return f"No orders found for '{customer_name}'."
    results = [
        f"Order {oid} — {o['product']}: ₹{o['amount']} ({o['status']})"
        for oid, o in orders
    ]
    return f"Orders for {customer_name}:\n" + "\n".join(results)


@tool
def get_customer_name(order_id: str) -> str:
    """Get the customer name associated with an order ID."""
    order = _get_order(order_id)
    if not order:
        return f"Order {order_id} not found."
    return f"Order {order_id} is registered under: {order['customer_name']}."


@tool
def process_return(order_id: str, reason: str) -> str:
    """Process a return request for a delivered order.
    Requires the order ID and reason for return."""
    order = _get_order(order_id)
    if not order:
        return f"Cannot process return — Order {order_id} not found."
    if not order["return_eligible"]:
        return f"Sorry, Order {order_id} is not eligible for return — the return window has expired."
    ticket_id, ticket = _create_return_ticket(order_id, reason)
    return (
        f"Return successfully initiated! Ticket ID: {ticket_id}. "
        f"Pickup scheduled for {ticket['pickup_date']}. "
        f"Refund of ₹{order['amount']} will be processed in 5-7 business days."
    )


@tool
def check_return_status(ticket_id: str) -> str:
    """Check the status of an existing return ticket using the ticket ID."""
    if _USE_SHOPIFY:
        return (
            f"Return ticket {ticket_id} is being processed. "
            "Our team will contact you within 24 hours to confirm pickup."
        )
    from mock_db import RETURN_TICKETS
    ticket = RETURN_TICKETS.get(ticket_id.upper())
    if not ticket:
        return f"No return ticket found with ID {ticket_id}."
    return (
        f"Return ticket {ticket_id}: Status is '{ticket['status']}'. "
        f"Pickup date: {ticket['pickup_date']}. "
        f"Reason: {ticket['reason']}."
    )


@tool
def check_return_policy(product_category: str) -> str:
    """Returns the return policy for a given product category."""
    policies = {
        "electronics": "Electronics can be returned within 7 days of delivery if unused and in original packaging.",
        "clothing": "Clothing can be returned within 30 days. Items must have tags attached.",
        "furniture": "Furniture returns are accepted within 48 hours of delivery only.",
        "default": "Most products have a 7-day return window from the date of delivery."
    }
    return policies.get(product_category.lower(), policies["default"])


@tool
def list_all_orders(customer_name: str) -> str:
    """Find and list all orders placed by a customer using their name."""
    orders = _get_orders_by_name(customer_name)
    if not orders:
        return f"No orders found for customer '{customer_name}'."
    results = [
        f"Order {oid}: {o['product']} — ₹{o['amount']} — {o['status']}"
        for oid, o in orders
    ]
    return f"Orders for {customer_name}:\n" + "\n".join(results)


@tool
def check_delivery_delay(order_id: str) -> str:
    """Check if the platform delayed delivery for this order by comparing
    promised delivery date vs actual delivery date. Use this when a customer
    disputes a return rejection because delivery was late."""
    from datetime import datetime

    order = _get_order(order_id)
    if not order:
        return f"Order {order_id} not found."

    promised = order.get("promised_delivery")
    actual = order.get("delivery_date")

    if not promised or not actual:
        return f"No delivery date data available for Order {order_id}."

    if order["status"] != "Delivered":
        return (
            f"Order {order_id} has not been delivered yet. "
            f"Promised by: {promised}, Current status: {order['status']}."
        )

    try:
        promised_date = datetime.strptime(promised[:10], "%Y-%m-%d")
        actual_date = datetime.strptime(actual[:10], "%Y-%m-%d")
        delay_days = (actual_date - promised_date).days

        if delay_days > 0:
            return (
                f"Confirmed: Order {order_id} was delivered {delay_days} day(s) late. "
                f"Promised delivery: {promised}, Actual delivery: {actual}. "
                f"The delay was on our end. Customer is entitled to a return window "
                f"extension of {delay_days} extra day(s)."
            )
        else:
            return (
                f"Order {order_id} was delivered on time on {actual}. "
                f"No delivery delay found — return window extension not applicable."
            )
    except Exception:
        return f"Could not calculate delay for Order {order_id}."


@tool
def extend_return_window(order_id: str, reason: str) -> str:
    """Extend the return window for an order when delivery was delayed
    by the platform. Updates the order to be return eligible."""
    order = _get_order(order_id)
    if not order:
        return f"Order {order_id} not found."
    _extend_return_window(order_id)
    return (
        f"Return window for Order {order_id} has been extended. "
        f"Reason: {reason}. "
        f"Customer can now initiate a return."
    )


@tool
def check_duplicate_orders(customer_name: str) -> str:
    """Check if a customer has placed duplicate orders for the same product."""
    orders = _get_orders_by_name(customer_name)
    if not orders:
        return f"No orders found for {customer_name}."

    products: dict = {}
    for oid, order in orders:
        product = order["product"]
        products.setdefault(product, []).append(oid)

    duplicates = {p: ids for p, ids in products.items() if len(ids) > 1}
    if not duplicates:
        return f"No duplicate orders found for {customer_name}."

    result = [
        f"Duplicate orders for '{p}': {', '.join(ids)}"
        for p, ids in duplicates.items()
    ]
    return "Duplicate orders found!\n" + "\n".join(result)
