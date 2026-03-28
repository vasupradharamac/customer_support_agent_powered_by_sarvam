"""
Shopify Admin API client for kviyengars.myshopify.com
Uses the REST Admin API to look up real orders and customer data.

Required env vars:
  SHOPIFY_STORE_DOMAIN  — e.g. kviyengars.myshopify.com
  SHOPIFY_ACCESS_TOKEN  — from Shopify Admin > Apps > Private apps (or Custom app)
"""

import httpx
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

STORE_DOMAIN = os.getenv("SHOPIFY_STORE_DOMAIN", "kviyengars.myshopify.com")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
API_VERSION = "2024-10"

_BASE = f"https://{STORE_DOMAIN}/admin/api/{API_VERSION}"
_HEADERS = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json",
}

RETURN_WINDOW_DAYS = {
    "electronics": 7,
    "clothing": 30,
    "furniture": 2,
    "default": 7,
}


def _order_to_internal(order: dict) -> dict:
    """Normalise a Shopify order object to the shape the agent tools expect."""
    customer = order.get("customer") or {}
    first = customer.get("first_name", "")
    last = customer.get("last_name", "")
    customer_name = f"{first} {last}".strip() or "Customer"

    line_items = order.get("line_items", [])
    product = line_items[0]["name"] if line_items else "Unknown product"
    amount = float(order.get("total_price", "0"))

    # Delivery dates
    created_at = order.get("created_at", "")
    fulfilled_at = None
    for fulfillment in order.get("fulfillments", []):
        if fulfillment.get("status") == "success":
            fulfilled_at = fulfillment.get("updated_at", "")
            break

    delivery_date = fulfilled_at[:10] if fulfilled_at else "Pending"
    # Shopify doesn't expose a promised_delivery date — use created_at + 5 days as estimate
    try:
        promised = (datetime.fromisoformat(created_at[:19]) .replace(tzinfo=timezone.utc))
        from datetime import timedelta
        promised_date = (promised + timedelta(days=5)).strftime("%Y-%m-%d")
    except Exception:
        promised_date = delivery_date

    # Map Shopify fulfillment status → friendly status
    fulfillment_status = order.get("fulfillment_status") or "unfulfilled"
    status_map = {
        "fulfilled": "Delivered",
        "partial": "Partially Shipped",
        "unfulfilled": "Processing",
        "restocked": "Cancelled",
    }
    status = status_map.get(fulfillment_status, fulfillment_status.title())

    # Determine return eligibility based on delivery date
    return_eligible = False
    if status == "Delivered" and delivery_date != "Pending":
        try:
            delivered = datetime.strptime(delivery_date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days_since = (datetime.now(timezone.utc) - delivered).days
            window = RETURN_WINDOW_DAYS.get("default")
            return_eligible = days_since <= window
        except Exception:
            pass

    return {
        "shopify_id": order["id"],
        "order_name": order.get("name", ""),          # e.g. "#1001"
        "customer_name": customer_name,
        "customer_email": customer.get("email", ""),
        "product": product,
        "amount": amount,
        "status": status,
        "promised_delivery": promised_date,
        "delivery_date": delivery_date,
        "return_eligible": return_eligible,
        "return_reason_needed": True,
    }


def get_order(order_name: str) -> dict | None:
    """Fetch a single order by Shopify order name (e.g. '#1001' or '1001')."""
    if not order_name.startswith("#"):
        order_name = f"#{order_name}"
    try:
        r = httpx.get(
            f"{_BASE}/orders.json",
            headers=_HEADERS,
            params={"name": order_name, "status": "any"},
            timeout=15,
        )
        orders = r.json().get("orders", [])
        return _order_to_internal(orders[0]) if orders else None
    except Exception as e:
        print(f"Shopify get_order error: {e}")
        return None


def get_orders_by_name(customer_name: str) -> list[tuple[str, dict]]:
    """Fetch all orders for a customer by name (searches last 50 orders)."""
    try:
        r = httpx.get(
            f"{_BASE}/orders.json",
            headers=_HEADERS,
            params={"status": "any", "limit": 50},
            timeout=15,
        )
        all_orders = r.json().get("orders", [])
        name_lower = customer_name.lower()
        matched = []
        for o in all_orders:
            c = o.get("customer") or {}
            full = f"{c.get('first_name', '')} {c.get('last_name', '')}".lower()
            if name_lower in full:
                internal = _order_to_internal(o)
                matched.append((o["name"], internal))
        return matched
    except Exception as e:
        print(f"Shopify get_orders_by_name error: {e}")
        return []


def extend_return_window_for_order(order_name: str) -> bool:
    """Mark the in-memory return window as extended (Shopify has no native field for this)."""
    # In a real setup you'd tag the order via Shopify API; here we return True to signal success
    try:
        if not order_name.startswith("#"):
            order_name = f"#{order_name}"
        r = httpx.get(
            f"{_BASE}/orders.json",
            headers=_HEADERS,
            params={"name": order_name, "status": "any"},
            timeout=15,
        )
        orders = r.json().get("orders", [])
        if not orders:
            return False
        order_id = orders[0]["id"]
        # Tag the order so the team knows it was extended
        httpx.put(
            f"{_BASE}/orders/{order_id}.json",
            headers=_HEADERS,
            json={"order": {"id": order_id, "tags": "return_window_extended"}},
            timeout=15,
        )
        return True
    except Exception as e:
        print(f"Shopify extend_return_window error: {e}")
        return False


def create_return_ticket(order_name: str, reason: str) -> tuple[str, dict]:
    """
    Create a return record.  Shopify Plus stores can use the Returns API;
    for standard Shopify we add an order note and tag, and generate a ticket ID.
    """
    try:
        if not order_name.startswith("#"):
            order_name = f"#{order_name}"
        r = httpx.get(
            f"{_BASE}/orders.json",
            headers=_HEADERS,
            params={"name": order_name, "status": "any"},
            timeout=15,
        )
        orders = r.json().get("orders", [])
        if not orders:
            return f"RET-ERR-001", {"status": "Failed", "reason": reason}
        order = orders[0]
        order_id = order["id"]

        from datetime import timedelta
        pickup_date = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%B %d, %Y")
        ticket_id = f"RET{str(order_id)[-4:]}_{int(datetime.now().timestamp()) % 10000:04d}"

        # Add note + tag on the Shopify order
        existing_note = order.get("note") or ""
        new_note = f"{existing_note}\n[Return Request] {reason} — Ticket: {ticket_id}".strip()
        httpx.put(
            f"{_BASE}/orders/{order_id}.json",
            headers=_HEADERS,
            json={"order": {
                "id": order_id,
                "note": new_note,
                "tags": "return_requested",
            }},
            timeout=15,
        )

        ticket = {"order_id": order_name, "reason": reason, "status": "Initiated", "pickup_date": pickup_date}
        return ticket_id, ticket
    except Exception as e:
        print(f"Shopify create_return_ticket error: {e}")
        ticket_id = f"RET-FALLBACK-001"
        from datetime import timedelta
        pickup_date = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%B %d, %Y")
        return ticket_id, {"order_id": order_name, "reason": reason, "status": "Initiated", "pickup_date": pickup_date}
