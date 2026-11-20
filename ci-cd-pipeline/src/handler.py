import json
from datetime import datetime

ORDERS = [
    {"id": "ORD-001", "customer": "Acme Corp", "product": "Widget A", "status": "shipped"},
    {"id": "ORD-002", "customer": "Beta Ltd", "product": "Widget B", "status": "processing"},
    {"id": "ORD-003", "customer": "Gamma Inc", "product": "Widget C", "status": "pending"},
    {"id": "ORD-004", "customer": "Delta Systems", "product": "Widget D", "status": "confirmed"},
]


def lambda_handler(event, context):
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/orders")

    if http_method == "GET" and path == "/orders":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"orders": ORDERS, "count": len(ORDERS)})
        }

    elif http_method == "POST" and path == "/orders":
        body = json.loads(event.get("body", "{}"))
        new_order = {
            "id": f"ORD-{datetime.now().strftime('%H%M%S')}",
            "customer": body.get("customer", "Unknown"),
            "product": body.get("product", "Unknown"),
            "status": "pending"
        }
        ORDERS.append(new_order)
        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Order created", "order": new_order})
        }

    return {
        "statusCode": 404,
        "body": json.dumps({"error": "Not found"})
    }
