from langchain_core.tools import tool
from mock_db import get_order, create_return_ticket, RETURN_TICKETS

@tool
def lookup_order(order_id: str) -> str:
    """Look up an order by order ID. Returns full order details
    including product name, amount, delivery date, and return eligibility."""
    order = get_order(order_id)
    if not order:
        return f"Order {order_id} not found. Please check the order ID."
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
    order = get_order(order_id)
    if not order:
        return f"Order {order_id} not found."
    return (
        f"Order {order_id} ({order['product']}) is currently: {order['status']}. "
        f"Delivery date: {order['delivery_date']}."
    )

@tool
def get_order_amount(order_id: str) -> str:
    """Get the amount paid for a specific order using order ID."""
    order = get_order(order_id)
    if not order:
        return f"Order {order_id} not found."
    return f"The amount paid for Order {order_id} ({order['product']}) is ₹{order['amount']}."

@tool
def get_amount_by_name(customer_name: str) -> str:
    """Get the amount paid for all orders using the customer's name
    instead of order ID."""
    from mock_db import get_orders_by_name
    orders = get_orders_by_name(customer_name)
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
    order = get_order(order_id)
    if not order:
        return f"Order {order_id} not found."
    return f"Order {order_id} is registered under: {order['customer_name']}."

@tool
def process_return(order_id: str, reason: str) -> str:
    """Process a return request for a delivered order.
    Requires the order ID and reason for return."""
    order = get_order(order_id)
    if not order:
        return f"Cannot process return — Order {order_id} not found."
    if not order["return_eligible"]:
        return f"Sorry, Order {order_id} is not eligible for return — the return window has expired."
    ticket_id, ticket = create_return_ticket(order_id, reason)
    return (
        f"Return successfully initiated! Ticket ID: {ticket_id}. "
        f"Pickup scheduled for {ticket['pickup_date']}. "
        f"Refund of ₹{order['amount']} will be processed in 5-7 business days."
    )

@tool
def check_return_status(ticket_id: str) -> str:
    """Check the status of an existing return ticket using the ticket ID."""
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
    from mock_db import get_orders_by_name
    orders = get_orders_by_name(customer_name)
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
    from mock_db import ORDERS
    from datetime import datetime

    order = ORDERS.get(order_id.upper())
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
        promised_date = datetime.strptime(promised, "%Y-%m-%d")
        actual_date = datetime.strptime(actual, "%Y-%m-%d")
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
    from mock_db import ORDERS
    order = ORDERS.get(order_id.upper())
    if not order:
        return f"Order {order_id} not found."
    ORDERS[order_id.upper()]["return_eligible"] = True
    return (
        f"Return window for Order {order_id} has been extended. "
        f"Reason: {reason}. "
        f"Customer can now initiate a return."
    )

@tool
def check_duplicate_orders(customer_name: str) -> str:
    """Check if a customer has placed duplicate orders for the same product."""
    from mock_db import get_orders_by_name
    orders = get_orders_by_name(customer_name)
    if not orders:
        return f"No orders found for {customer_name}."

    products = {}
    for oid, order in orders:
        product = order["product"]
        if product not in products:
            products[product] = []
        products[product].append(oid)

    duplicates = {p: ids for p, ids in products.items() if len(ids) > 1}
    if not duplicates:
        return f"No duplicate orders found for {customer_name}."

    result = [
        f"Duplicate orders for '{p}': {', '.join(ids)}"
        for p, ids in duplicates.items()
    ]
    return "Duplicate orders found!\n" + "\n".join(result)
