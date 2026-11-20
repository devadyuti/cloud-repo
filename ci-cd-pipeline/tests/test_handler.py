import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.handler import lambda_handler


def test_get_orders():
    event = {"httpMethod": "GET", "path": "/orders"}
    response = lambda_handler(event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "orders" in body
    assert body["count"] == 4


def test_post_order():
    event = {
        "httpMethod": "POST",
        "path": "/orders",
        "body": json.dumps({"customer": "Test Co", "product": "Widget X"})
    }
    response = lambda_handler(event, None)
    assert response["statusCode"] == 201
    body = json.loads(response["body"])
    assert body["order"]["customer"] == "Test Co"
    assert body["order"]["status"] == "pending"


def test_not_found():
    event = {"httpMethod": "DELETE", "path": "/orders"}
    response = lambda_handler(event, None)
    assert response["statusCode"] == 404
