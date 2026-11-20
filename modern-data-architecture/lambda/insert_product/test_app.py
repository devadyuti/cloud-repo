"""Unit tests for the InsertProduct Lambda (app.py).

app.py imports ``pg8000.native`` and creates Secrets Manager and SSM clients at
module load time, and neither is available (or should reach the network) in CI.
So we inject a fake ``pg8000`` module and stub ``boto3.client`` before importing
``app``, then drive the handler with a fake DB connection that records the SQL
and parameters it receives.
"""

import importlib
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

LAMBDA_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(LAMBDA_DIR))


class _FakeConnection:
    """Records every ``run(sql, **params)`` call and whether it was closed."""

    def __init__(self):
        self.calls = []
        self.closed = False

    def run(self, sql, **params):
        self.calls.append((sql, params))
        return []

    def close(self):
        self.closed = True


@pytest.fixture
def app(monkeypatch):
    """Import app.py with pg8000 and boto3 stubbed, returning the module.

    A fresh fake connection is attached at ``app._fake_conn`` so each test can
    inspect the SQL/params the handler issued. ``pg8000.native.Connection`` is
    patched to return that connection.
    """
    # Stub pg8000 (not installed outside the Lambda bundle).
    fake_pg8000 = types.ModuleType("pg8000")
    fake_native = types.ModuleType("pg8000.native")
    fake_conn = _FakeConnection()
    fake_native.Connection = MagicMock(name="Connection", return_value=fake_conn)
    fake_pg8000.native = fake_native
    monkeypatch.setitem(sys.modules, "pg8000", fake_pg8000)
    monkeypatch.setitem(sys.modules, "pg8000.native", fake_native)

    # Stub boto3.client so module-level secretsmanager/ssm client creation is inert.
    import boto3

    fake_secrets = MagicMock(name="secretsmanager")
    fake_secrets.get_secret_value.return_value = {
        "SecretString": '{"username": "u", "password": "p"}'
    }
    fake_ssm = MagicMock(name="ssm")
    fake_ssm.get_parameter.return_value = {
        "Parameter": {"Value": "db.example.internal"}
    }

    def _client(name, *a, **k):
        return fake_ssm if name == "ssm" else fake_secrets

    monkeypatch.setattr(boto3, "client", _client)

    # Force a clean import each test to pick up the stubs.
    sys.modules.pop("app", None)
    module = importlib.import_module("app")

    module._fake_conn = fake_conn
    return module


def _insert_call(app):
    """Return the (sql, params) tuple for the INSERT the handler issued."""
    return next(
        (sql, p) for sql, p in app._fake_conn.calls if sql.startswith("INSERT")
    )


class TestValidation:
    @pytest.mark.parametrize(
        "missing_field", ["product_id", "product_name", "product_category"]
    )
    def test_missing_required_field_returns_400(self, app, missing_field):
        payload = {
            "product_id": 999999,
            "product_name": "Zero-ETL Test Product",
            "product_category": "Electronics",
        }
        del payload[missing_field]

        result = app.lambda_handler(payload, None)

        assert result["statusCode"] == 400
        # No INSERT should have been attempted.
        assert not any(
            sql.startswith("INSERT") for sql, _ in app._fake_conn.calls
        )

    def test_empty_event_returns_400(self, app):
        result = app.lambda_handler({}, None)
        assert result["statusCode"] == 400

    def test_none_event_returns_400(self, app):
        result = app.lambda_handler(None, None)
        assert result["statusCode"] == 400


class TestProductInsert:
    def test_three_field_payload_binds_price_and_quantity_as_none(self, app):
        payload = {
            "product_id": 999999,
            "product_name": "Zero-ETL Test Product",
            "product_category": "Electronics",
        }

        result = app.lambda_handler(payload, None)

        assert result["statusCode"] == 200
        sql, params = _insert_call(app)
        # All five columns are named in the INSERT.
        assert "product_id" in sql
        assert "product_name" in sql
        assert "price" in sql
        assert "quantity" in sql
        assert "product_category" in sql
        # price/quantity default to None (NULL) when not supplied.
        assert params["price"] is None
        assert params["quantity"] is None
        assert params["product_id"] == 999999
        assert params["product_name"] == "Zero-ETL Test Product"
        assert params["product_category"] == "Electronics"
        assert app._fake_conn.closed is True

    def test_five_field_payload_binds_price_and_quantity(self, app):
        payload = {
            "product_id": 999999,
            "product_name": "Zero-ETL Test Product",
            "product_category": "Electronics",
            "price": 19.99,
            "quantity": 42,
        }

        result = app.lambda_handler(payload, None)

        assert result["statusCode"] == 200
        _, params = _insert_call(app)
        assert params["price"] == 19.99
        assert params["quantity"] == 42

    def test_success_body_echoes_all_fields(self, app):
        payload = {
            "product_id": 999999,
            "product_name": "Zero-ETL Test Product",
            "product_category": "Electronics",
            "price": 19.99,
            "quantity": 42,
        }

        result = app.lambda_handler(payload, None)
        body = json.loads(result["body"])

        assert body["message"] == "Product inserted successfully"
        assert body["product_id"] == 999999
        assert body["product_name"] == "Zero-ETL Test Product"
        assert body["product_category"] == "Electronics"
        assert body["price"] == 19.99
        assert body["quantity"] == 42

    def test_connection_closed_on_db_error(self, app):
        payload = {
            "product_id": 999999,
            "product_name": "Zero-ETL Test Product",
            "product_category": "Electronics",
        }

        def _boom(*a, **k):
            raise RuntimeError("db down")

        app._fake_conn.run = _boom

        result = app.lambda_handler(payload, None)

        assert result["statusCode"] == 500
        assert app._fake_conn.closed is True
