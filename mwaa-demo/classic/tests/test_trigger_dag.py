"""Unit tests for the trigger_dag Lambda handler (MWAA InvokeRestApi)."""

import json
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add lambda/ directory to import path so trigger_dag can be imported directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lambda"))


@pytest.fixture(autouse=True)
def _reload_module():
    """Force re-import of trigger_dag for each test."""
    if "trigger_dag" in sys.modules:
        del sys.modules["trigger_dag"]
    yield
    if "trigger_dag" in sys.modules:
        del sys.modules["trigger_dag"]


@pytest.fixture()
def mock_boto_client():
    """Stub boto3 MWAA client with a successful invoke_rest_api response."""
    with patch("boto3.client") as mock_client_ctor:
        client = MagicMock()
        client.invoke_rest_api.return_value = {
            "RestApiStatusCode": 200,
            "RestApiResponse": {
                "dag_run_id": "manual__2026-08-06T10:00:00.000000Z",
                "state": "queued",
                "logical_date": "2026-08-06T10:00:00.000000Z",
            },
        }
        mock_client_ctor.return_value = client
        yield client


class TestTriggerDagHandler:
    """Tests for trigger_dag.handler — triggers api_triggered DAG via InvokeRestApi."""

    def test_returns_200_on_success(self, mock_boto_client):
        """Handler returns statusCode 200 when DAG is triggered successfully."""
        from trigger_dag import handler

        result = handler({}, None)

        assert result["statusCode"] == 200

    def test_response_body_contains_dag_run(self, mock_boto_client):
        """Response body contains the DAG run details from InvokeRestApi."""
        from trigger_dag import handler

        result = handler({}, None)
        body = json.loads(result["body"])

        assert body["dag_run_id"] == "manual__2026-08-06T10:00:00.000000Z"
        assert body["state"] == "queued"

    def test_calls_invoke_rest_api_with_correct_params(self, mock_boto_client):
        """Handler calls invoke_rest_api with correct Name, Path, Method, and Body dict."""
        from trigger_dag import handler

        handler({}, None)

        mock_boto_client.invoke_rest_api.assert_called_once()
        call_kwargs = mock_boto_client.invoke_rest_api.call_args[1]

        assert call_kwargs["Name"] == "any-company-mwaa-demo"
        assert call_kwargs["Path"] == "/dags/api_triggered/dagRuns"
        assert call_kwargs["Method"] == "POST"

        # Body is passed as a dict (boto3 1.42+ serializes it)
        body = call_kwargs["Body"]
        assert isinstance(body, dict)
        assert "logical_date" in body
        assert body["conf"]["message"] == "Triggered from Lambda"
        assert body["conf"]["source"] == "mwaa-classic-dag-trigger"

    def test_creates_mwaa_client_in_eu_west_1(self):
        """Handler creates the MWAA client in eu-west-1."""
        with patch("boto3.client") as mock_ctor:
            client = MagicMock()
            client.invoke_rest_api.return_value = {
                "RestApiStatusCode": 200,
                "RestApiResponse": {"dag_run_id": "test", "state": "queued"},
            }
            mock_ctor.return_value = client

            from trigger_dag import handler

            handler({}, None)

            mock_ctor.assert_called_with("mwaa", region_name="eu-west-1")

    def test_body_includes_logical_date_with_microseconds(self, mock_boto_client):
        """Trigger body includes a logical_date with microsecond precision."""
        from trigger_dag import handler

        handler({}, None)

        call_kwargs = mock_boto_client.invoke_rest_api.call_args[1]
        body = call_kwargs["Body"]

        assert body["logical_date"].endswith("Z")
        assert "T" in body["logical_date"]
        assert "." in body["logical_date"], "logical_date should include microseconds"

    def test_body_includes_conf_with_request_id(self, mock_boto_client):
        """Trigger body conf includes a valid UUID4 request_id."""
        from trigger_dag import handler

        handler({}, None)

        call_kwargs = mock_boto_client.invoke_rest_api.call_args[1]
        body = call_kwargs["Body"]

        request_id = body["conf"]["request_id"]
        parsed = uuid.UUID(request_id)
        assert parsed.version == 4

    def test_propagates_client_error(self):
        """Handler lets ClientError from invoke_rest_api propagate."""
        from botocore.exceptions import ClientError

        with patch("boto3.client") as mock_ctor:
            client = MagicMock()
            client.invoke_rest_api.side_effect = ClientError(
                {"Error": {"Code": "AccessDeniedException", "Message": "Not authorized"}},
                "InvokeRestApi",
            )
            mock_ctor.return_value = client

            from trigger_dag import handler

            with pytest.raises(ClientError):
                handler({}, None)

    def test_ignores_event_input(self, mock_boto_client):
        """Handler ignores the event payload — always triggers api_triggered DAG."""
        from trigger_dag import handler

        event_with_body = {"body": json.dumps({"dag_id": "other_dag"})}
        result = handler(event_with_body, None)

        call_kwargs = mock_boto_client.invoke_rest_api.call_args[1]
        assert call_kwargs["Path"] == "/dags/api_triggered/dagRuns"
        assert result["statusCode"] == 200

    def test_prints_dag_run_info(self, mock_boto_client, capsys):
        """Handler prints DAG trigger status, run ID, and state."""
        from trigger_dag import handler

        handler({}, None)

        captured = capsys.readouterr()
        assert "DAG triggered!" in captured.out
        assert "200" in captured.out
        assert "manual__2026-08-06T10:00:00.000000Z" in captured.out
