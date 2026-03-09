from datetime import datetime

ORDERS = {
    "ORD001": {
        "customer_name": "Vasupradha",
        "product": "Samsung Galaxy Buds Pro",
        "amount": 8999,
        "status": "Delivered",
        "promised_delivery": "2026-03-04",
        "delivery_date": "2026-03-05",
        "return_eligible": False,
        "return_reason_needed": True
    },
    "ORD002": {
        "customer_name": "Ravi Kumar",
        "product": "Noise ColorFit Pro 5",
        "amount": 3499,
        "status": "Delivered",
        "promised_delivery": "2026-02-16",
        "delivery_date": "2026-02-20",
        "return_eligible": False,
        "return_reason_needed": False
    },
    "ORD003": {
        "customer_name": "Priya Lakshmi",
        "product": "boAt Rockerz 450",
        "amount": 1799,
        "status": "Delivered",
        "promised_delivery": "2026-03-06",
        "delivery_date": "2026-03-07",
        "return_eligible": True,
        "return_reason_needed": True
    },
    "ORD004": {
        "customer_name": "Vasupradha",
        "product": "Dr.Althea 345 Cream",
        "amount": 2199,
        "status": "Out for Delivery",
        "promised_delivery": "2026-03-09",
        "delivery_date": "Expected by 2026-03-10",
        "return_eligible": False,
        "return_reason_needed": False
    },
    "ORD005": {
        "customer_name": "Arjun Mehta",
        "product": "Apple AirPods Pro 2",
        "amount": 24999,
        "status": "Shipped",
        "promised_delivery": "2026-03-12",
        "delivery_date": "Expected by 2026-03-12",
        "return_eligible": False,
        "return_reason_needed": False
    },
    "ORD006": {
        "customer_name": "Divya Nair",
        "product": "Dyson Vacuum Cleaner",
        "amount": 44999,
        "status": "Delivered",
        "promised_delivery": "2026-03-08",
        "delivery_date": "2026-03-10",
        "return_eligible": False,
        "return_reason_needed": False
    },
    "ORD007": {
        "customer_name": "Karthik Subramanian",
        "product": "OnePlus 13 5G",
        "amount": 69999,
        "status": "Out for Delivery",
        "promised_delivery": "2026-03-08",
        "delivery_date": "Expected by 2026-03-10",
        "return_eligible": False,
        "return_reason_needed": False
    },
    "ORD008": {
        "customer_name": "Meera Iyer",
        "product": "Levi's 511 Slim Jeans",
        "amount": 2999,
        "status": "Delivered",
        "promised_delivery": "2026-03-01",
        "delivery_date": "2026-03-01",
        "return_eligible": True,
        "return_reason_needed": True
    },
    "ORD009": {
        "customer_name": "Rahul Sharma",
        "product": "Ikea MALM Bed Frame",
        "amount": 18999,
        "status": "Shipped",
        "promised_delivery": "2026-03-14",
        "delivery_date": "Expected by 2026-03-14",
        "return_eligible": False,
        "return_reason_needed": False
    },
    "ORD010": {
        "customer_name": "Vasupradha",
        "product": "Dior Sauvage Parfum 100ml",
        "amount": 12500,
        "status": "Delivered",
        "promised_delivery": "2026-03-07",
        "delivery_date": "2026-03-09",
        "return_eligible": False,
        "return_reason_needed": False
    }
}

RETURN_TICKETS = {}

def get_order(order_id: str):
    return ORDERS.get(order_id.upper())

def get_orders_by_name(customer_name: str) -> list:
    return [
        (oid, order) for oid, order in ORDERS.items()
        if order["customer_name"].lower() == customer_name.lower()
    ]

def create_return_ticket(order_id: str, reason: str):
    ticket_id = f"RET{order_id[-3:]}_{len(RETURN_TICKETS)+1:03d}"
    RETURN_TICKETS[ticket_id] = {
        "order_id": order_id,
        "reason": reason,
        "status": "Initiated",
        "pickup_date": "March 15, 2026",

    }
    return ticket_id, RETURN_TICKETS[ticket_id]
