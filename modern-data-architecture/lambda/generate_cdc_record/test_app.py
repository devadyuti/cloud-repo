"""Unit tests for the GenerateCDCRecord Lambda (app.py).

app.py imports ``pg8000.native`` and creates a Secrets Manager client at module
load time, and neither is available (or should reach the network) in CI. So we
inject a fake ``pg8000`` module and stub ``boto3.client`` before importing
``app``, then drive the handler with a fake DB connection that records the SQL
and parameters it receives.
"""

import importlib
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
    inspect the SQL/params the handler issued.
    """
    # Stub pg8000 (not installed outside the Lambda bundle).
    fake_pg8000 = types.ModuleType("pg8000")
    fake_native = types.ModuleType("pg8000.native")
    fake_native.Connection = MagicMock(name="Connection")
    fake_pg8000.native = fake_native
    monkeypatch.setitem(sys.modules, "pg8000", fake_pg8000)
    monkeypatch.setitem(sys.modules, "pg8000.native", fake_native)

    # Stub boto3.client so module-level secretsmanager client creation is inert.
    import boto3

    fake_secrets = MagicMock(name="secretsmanager")
    fake_secrets.get_secret_value.return_value = {
        "SecretString": '{"username": "u", "password": "p"}'
    }
    monkeypatch.setattr(boto3, "client", lambda *a, **k: fake_secrets)

    # Required environment variables.
    monkeypatch.setenv("AURORA_SECRET_ARN", "arn:aws:secretsmanager:eu-west-1:1:secret:x")
    monkeypatch.setenv("AURORA_HOST", "db.example.internal")
    monkeypatch.setenv("AURORA_DB_NAME", "mdacluster")
    monkeypatch.setenv("AURORA_PORT", "5432")

    # Force a clean import each test to pick up the stubs and env vars.
    sys.modules.pop("app", None)
    module = importlib.import_module("app")

    # Make _connect() return a fresh recording connection.
    fake_conn = _FakeConnection()
    module._fake_conn = fake_conn
    monkeypatch.setattr(module, "_connect", lambda: fake_conn)

    return module


class TestAdminActions:
    def test_droptable_drops_reviews_and_closes(self, app):
        result = app.handler({"action": "droptable"}, None)

        assert result["statusCode"] == 200
        assert "dropped" in result["message"]
        assert app._fake_conn.calls == [("DROP TABLE IF EXISTS reviews", {})]
        assert app._fake_conn.closed is True

    def test_initdb_creates_reviews_table(self, app):
        result = app.handler({"action": "initdb"}, None)

        assert result["statusCode"] == 200
        assert "ready" in result["message"]
        assert app._fake_conn.calls == [(app.CREATE_TABLE_SQL, {})]
        assert app._fake_conn.closed is True


class TestReviewInsert:
    def _payload(self):
        return {
            "product_id": "88236",
            "comment": "What an amazing product!",
            "rating": "5",
            "name": "Your name",
        }

    def test_insert_creates_table_then_inserts(self, app):
        result = app.handler(self._payload(), None)

        assert result["statusCode"] == 200
        assert result["message"] == "review inserted"
        assert result["review"] == self._payload()

        # First ensures the table exists, then inserts.
        sqls = [sql for sql, _ in app._fake_conn.calls]
        assert app.CREATE_TABLE_SQL in sqls
        insert_sql = next(s for s in sqls if s.startswith("INSERT INTO reviews"))
        assert "CURRENT_TIMESTAMP" in insert_sql

    def test_insert_coerces_param_types(self, app):
        app.handler(self._payload(), None)

        _, params = next(
            (sql, p) for sql, p in app._fake_conn.calls if sql.startswith("INSERT")
        )
        assert params["product_id"] == "88236"
        assert params["rating"] == 5  # coerced to int
        assert isinstance(params["rating"], int)
        assert params["name"] == "Your name"

    @pytest.mark.parametrize("missing_field", ["product_id", "comment", "rating", "name"])
    def test_missing_field_returns_400(self, app, missing_field):
        payload = self._payload()
        del payload[missing_field]

        result = app.handler(payload, None)

        assert result["statusCode"] == 400
        assert missing_field in result["error"]
        # No INSERT should have been attempted.
        assert not any(sql.startswith("INSERT") for sql, _ in app._fake_conn.calls)

    def test_empty_event_returns_400(self, app):
        result = app.handler({}, None)
        assert result["statusCode"] == 400

    def test_none_event_returns_400(self, app):
        result = app.handler(None, None)
        assert result["statusCode"] == 400
