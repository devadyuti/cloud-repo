"""Unit tests for the Lambda DAG trigger function."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# Add lambda/ to path so trigger_dag can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lambda"))


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Set required environment variables."""
    monkeypatch.setenv("WORKFLOW_ARN", "arn:aws:airflow-serverless:eu-west-1:123456789012:workflow/test-workflow")


@pytest.fixture(autouse=True)
def reload_module():
    """Force re-import of trigger_dag for each test to pick up env changes."""
    if "trigger_dag" in sys.modules:
        del sys.modules["trigger_dag"]


class TestHandler:
    """Tests for trigger_dag.handler via start_workflow_run."""

    @patch("trigger_dag.boto3.client")
    def test_calls_start_workflow_run(self, mock_boto_client):
        """Handler calls start_workflow_run with the correct workflow ARN."""
        mock_serverless = MagicMock()
        mock_cw = MagicMock()
        mock_boto_client.side_effect = lambda svc: mock_serverless if svc == "mwaa-serverless" else mock_cw
        mock_serverless.start_workflow_run.return_value = {
            "RunId": "run-123",
            "Status": "QUEUED",
        }

        import trigger_dag
        trigger_dag.handler({}, None)

        mock_serverless.start_workflow_run.assert_called_once()
        call_kwargs = mock_serverless.start_workflow_run.call_args[1]
        assert call_kwargs["WorkflowArn"] == "arn:aws:airflow-serverless:eu-west-1:123456789012:workflow/test-workflow"

    @patch("trigger_dag.boto3.client")
    def test_direct_invocation_params(self, mock_boto_client):
        """Direct invocation sets source=lambda_direct."""
        mock_serverless = MagicMock()
        mock_cw = MagicMock()
        mock_boto_client.side_effect = lambda svc: mock_serverless if svc == "mwaa-serverless" else mock_cw
        mock_serverless.start_workflow_run.return_value = {
            "RunId": "run-456",
            "Status": "QUEUED",
        }

        import trigger_dag
        trigger_dag.handler({}, None)

        call_kwargs = mock_serverless.start_workflow_run.call_args[1]
        assert call_kwargs["OverrideParameters"]["source"] == "lambda_direct"
        assert "date" in call_kwargs["OverrideParameters"]

    @patch("trigger_dag.boto3.client")
    def test_s3_event_trigger_params(self, mock_boto_client):
        """S3 event invocation extracts bucket and key from the record."""
        mock_serverless = MagicMock()
        mock_cw = MagicMock()
        mock_boto_client.side_effect = lambda svc: mock_serverless if svc == "mwaa-serverless" else mock_cw
        mock_serverless.start_workflow_run.return_value = {
            "RunId": "run-789",
            "Status": "QUEUED",
        }

        s3_event = {
            "Records": [{
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "my-bucket"},
                    "object": {"key": "serverless/incoming/data.csv"},
                },
            }]
        }

        import trigger_dag
        trigger_dag.handler(s3_event, None)

        call_kwargs = mock_serverless.start_workflow_run.call_args[1]
        assert call_kwargs["OverrideParameters"]["source"] == "s3_event"
        assert call_kwargs["OverrideParameters"]["s3_bucket"] == "my-bucket"
        assert call_kwargs["OverrideParameters"]["s3_key"] == "serverless/incoming/data.csv"

    @patch("trigger_dag.boto3.client")
    def test_returns_success_response(self, mock_boto_client):
        """Handler returns 200 with run details on success."""
        mock_serverless = MagicMock()
        mock_cw = MagicMock()
        mock_boto_client.side_effect = lambda svc: mock_serverless if svc == "mwaa-serverless" else mock_cw
        mock_serverless.start_workflow_run.return_value = {
            "RunId": "run-123",
            "Status": "QUEUED",
        }

        import trigger_dag
        result = trigger_dag.handler({}, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["runId"] == "run-123"
        assert body["status"] == "QUEUED"
        assert body["message"] == "Workflow run started"

    @patch("trigger_dag.boto3.client")
    def test_returns_error_on_failure(self, mock_boto_client):
        """Handler returns 500 with error message on exception."""
        mock_serverless = MagicMock()
        mock_cw = MagicMock()
        mock_boto_client.side_effect = lambda svc: mock_serverless if svc == "mwaa-serverless" else mock_cw
        mock_serverless.start_workflow_run.side_effect = Exception("Service unavailable")

        import trigger_dag
        result = trigger_dag.handler({}, None)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "Service unavailable" in body["error"]

    @patch("trigger_dag.boto3.client")
    def test_publishes_custom_metrics_on_success(self, mock_boto_client):
        """Handler publishes WorkflowRunsStarted metric on success."""
        mock_serverless = MagicMock()
        mock_cw = MagicMock()
        mock_boto_client.side_effect = lambda svc: mock_serverless if svc == "mwaa-serverless" else mock_cw
        mock_serverless.start_workflow_run.return_value = {
            "RunId": "run-123",
            "Status": "QUEUED",
        }

        import trigger_dag
        trigger_dag.handler({}, None)

        # Should have published at least WorkflowRunsStarted and WorkflowDurationMs
        assert mock_cw.put_metric_data.call_count >= 2
        # Check the first call is WorkflowRunsStarted
        first_call = mock_cw.put_metric_data.call_args_list[0]
        assert first_call[1]["Namespace"] == "MWAADemo/Serverless"
        assert first_call[1]["MetricData"][0]["MetricName"] == "WorkflowRunsStarted"

    @patch("trigger_dag.boto3.client")
    def test_publishes_failure_metric_on_error(self, mock_boto_client):
        """Handler publishes WorkflowRunsFailed metric on exception."""
        mock_serverless = MagicMock()
        mock_cw = MagicMock()
        mock_boto_client.side_effect = lambda svc: mock_serverless if svc == "mwaa-serverless" else mock_cw
        mock_serverless.start_workflow_run.side_effect = Exception("Boom")

        import trigger_dag
        trigger_dag.handler({}, None)

        mock_cw.put_metric_data.assert_called()
        call_kwargs = mock_cw.put_metric_data.call_args[1]
        assert call_kwargs["Namespace"] == "MWAADemo/Serverless"
        assert call_kwargs["MetricData"][0]["MetricName"] == "WorkflowRunsFailed"
