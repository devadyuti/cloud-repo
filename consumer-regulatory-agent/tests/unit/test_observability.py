"""Unit tests for the observability module.

Tests X-Ray tracing setup, structured logging, CloudWatch metrics emission,
and subsegment context manager behavior.

Requirements: 9.1, 9.2, 9.3, 9.4
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# StructuredLogger tests
# ---------------------------------------------------------------------------


class TestStructuredLogger:
    """Tests for the StructuredLogger class."""

    def test_info_emits_json_with_required_fields(self, caplog):
        from lambdas.shared.observability import StructuredLogger

        logger = StructuredLogger("test_logger", component="test.component")

        with caplog.at_level(logging.INFO):
            logger.info(
                "assessment_completed",
                request_id="req-123",
                user_id="user-456",
                response_time_ms=1500,
            )

        assert len(caplog.records) == 1
        entry = json.loads(caplog.records[0].message)
        assert entry["event"] == "assessment_completed"
        assert entry["component"] == "test.component"
        assert entry["level"] == "INFO"
        assert entry["request_id"] == "req-123"
        assert entry["user_id"] == "user-456"
        assert entry["response_time_ms"] == 1500
        assert "timestamp" in entry

    def test_warning_emits_warning_level(self, caplog):
        from lambdas.shared.observability import StructuredLogger

        logger = StructuredLogger("test_logger", component="test.component")

        with caplog.at_level(logging.WARNING):
            logger.warning("latency_threshold_breached", response_time_ms=35000)

        assert len(caplog.records) == 1
        entry = json.loads(caplog.records[0].message)
        assert entry["level"] == "WARNING"
        assert entry["event"] == "latency_threshold_breached"

    def test_error_emits_error_level(self, caplog):
        from lambdas.shared.observability import StructuredLogger

        logger = StructuredLogger("test_logger", component="test.component")

        with caplog.at_level(logging.ERROR):
            logger.error("agent_invocation_failed", error="timeout")

        assert len(caplog.records) == 1
        entry = json.loads(caplog.records[0].message)
        assert entry["level"] == "ERROR"
        assert entry["event"] == "agent_invocation_failed"
        assert entry["error"] == "timeout"

    def test_structured_fields_include_all_assessment_fields(self, caplog):
        """Verify structured logs can include all required observability fields."""
        from lambdas.shared.observability import StructuredLogger

        logger = StructuredLogger("test_logger", component="orchestrator.handler")

        with caplog.at_level(logging.INFO):
            logger.info(
                "assessment_completed",
                request_id="req-abc",
                user_id="user-xyz",
                query_type="campaign_compliance",
                jurisdictions=["UK", "EU"],
                response_time_ms=4200,
                risk_levels={"UK": "High", "EU": "Medium"},
            )

        entry = json.loads(caplog.records[0].message)
        assert entry["request_id"] == "req-abc"
        assert entry["user_id"] == "user-xyz"
        assert entry["query_type"] == "campaign_compliance"
        assert entry["jurisdictions"] == ["UK", "EU"]
        assert entry["response_time_ms"] == 4200
        assert entry["risk_levels"] == {"UK": "High", "EU": "Medium"}


# ---------------------------------------------------------------------------
# get_logger factory tests
# ---------------------------------------------------------------------------


class TestGetLogger:
    """Tests for the get_logger factory function."""

    def test_returns_structured_logger_instance(self):
        from lambdas.shared.observability import StructuredLogger, get_logger

        logger = get_logger("my_module", component="my.component")
        assert isinstance(logger, StructuredLogger)

    def test_default_component_uses_name(self, caplog):
        from lambdas.shared.observability import get_logger

        logger = get_logger("my_module")

        with caplog.at_level(logging.INFO):
            logger.info("test_event")

        entry = json.loads(caplog.records[0].message)
        assert entry["component"] == "my_module"


# ---------------------------------------------------------------------------
# X-Ray tracing tests
# ---------------------------------------------------------------------------


class TestXRayTracing:
    """Tests for X-Ray tracing initialization and subsegments."""

    def test_init_xray_tracing_no_op_without_sdk(self):
        """init_xray_tracing should not raise even if SDK is unavailable."""
        from lambdas.shared.observability import init_xray_tracing

        # Should not raise
        init_xray_tracing()

    def test_trace_subsegment_no_op_without_xray(self):
        """trace_subsegment should yield None when X-Ray is not enabled."""
        from lambdas.shared.observability import trace_subsegment

        with trace_subsegment("test_operation") as subsegment:
            assert subsegment is None

    def test_trace_subsegment_no_op_does_not_affect_code(self):
        """Code inside trace_subsegment should execute normally."""
        from lambdas.shared.observability import trace_subsegment

        result = None
        with trace_subsegment("test_operation", {"key": "value"}):
            result = 42

        assert result == 42

    def test_trace_subsegment_propagates_exceptions(self):
        """Exceptions inside trace_subsegment should propagate."""
        from lambdas.shared.observability import trace_subsegment

        with pytest.raises(ValueError, match="test error"):
            with trace_subsegment("failing_operation"):
                raise ValueError("test error")

    @patch.dict(os.environ, {"ENABLE_XRAY": "true"})
    @patch("lambdas.shared.observability._XRAY_ENABLED", True)
    @patch("lambdas.shared.observability._XRAY_SDK_AVAILABLE", True)
    @patch("lambdas.shared.observability.xray_recorder")
    def test_trace_subsegment_creates_subsegment_when_enabled(self, mock_recorder):
        """When X-Ray is enabled, subsegments should be created."""
        from lambdas.shared.observability import trace_subsegment

        mock_subsegment = MagicMock()
        mock_recorder.begin_subsegment.return_value = mock_subsegment

        with trace_subsegment("agent_invocation", {"model_id": "claude-3"}):
            pass

        mock_recorder.begin_subsegment.assert_called_once_with("agent_invocation")
        mock_subsegment.put_metadata.assert_called_once_with("model_id", "claude-3")
        mock_recorder.end_subsegment.assert_called_once()

    @patch.dict(os.environ, {"ENABLE_XRAY": "true"})
    @patch("lambdas.shared.observability._XRAY_ENABLED", True)
    @patch("lambdas.shared.observability._XRAY_SDK_AVAILABLE", True)
    @patch("lambdas.shared.observability.xray_recorder")
    def test_trace_subsegment_records_exception(self, mock_recorder):
        """When an exception occurs, it should be recorded on the subsegment."""
        from lambdas.shared.observability import trace_subsegment

        mock_subsegment = MagicMock()
        mock_recorder.begin_subsegment.return_value = mock_subsegment

        with pytest.raises(RuntimeError):
            with trace_subsegment("failing_op"):
                raise RuntimeError("boom")

        mock_subsegment.add_exception.assert_called_once()
        mock_recorder.end_subsegment.assert_called_once()


# ---------------------------------------------------------------------------
# CloudWatch metrics tests
# ---------------------------------------------------------------------------


class TestEmitLatencyMetric:
    """Tests for the emit_latency_metric function."""

    @patch("lambdas.shared.observability.boto3.client")
    def test_emits_latency_metric_below_threshold(self, mock_client):
        from lambdas.shared.observability import emit_latency_metric

        mock_cw = MagicMock()
        mock_client.return_value = mock_cw

        emit_latency_metric(
            response_time_ms=5000,
            assessment_type="campaign_compliance",
            request_id="req-123",
        )

        mock_client.assert_called_once_with("cloudwatch")
        mock_cw.put_metric_data.assert_called_once()

        call_kwargs = mock_cw.put_metric_data.call_args[1]
        assert call_kwargs["Namespace"] == "ConsumerRegulatoryAgent"

        metric_data = call_kwargs["MetricData"]
        # Only AssessmentLatency should be emitted (no threshold breach)
        assert len(metric_data) == 1
        assert metric_data[0]["MetricName"] == "AssessmentLatency"
        assert metric_data[0]["Value"] == 5000.0
        assert metric_data[0]["Unit"] == "Milliseconds"
        assert metric_data[0]["Dimensions"] == [
            {"Name": "AssessmentType", "Value": "campaign_compliance"}
        ]

    @patch("lambdas.shared.observability.boto3.client")
    def test_emits_threshold_breach_metric_above_30s(self, mock_client):
        from lambdas.shared.observability import emit_latency_metric

        mock_cw = MagicMock()
        mock_client.return_value = mock_cw

        emit_latency_metric(
            response_time_ms=35000,
            assessment_type="campaign_compliance",
            request_id="req-456",
        )

        call_kwargs = mock_cw.put_metric_data.call_args[1]
        metric_data = call_kwargs["MetricData"]

        # Both AssessmentLatency and LatencyThresholdBreached should be emitted
        assert len(metric_data) == 2
        assert metric_data[0]["MetricName"] == "AssessmentLatency"
        assert metric_data[0]["Value"] == 35000.0
        assert metric_data[1]["MetricName"] == "LatencyThresholdBreached"
        assert metric_data[1]["Value"] == 1.0
        assert metric_data[1]["Unit"] == "Count"

    @patch("lambdas.shared.observability.boto3.client")
    def test_does_not_emit_breach_at_exactly_30s(self, mock_client):
        from lambdas.shared.observability import emit_latency_metric

        mock_cw = MagicMock()
        mock_client.return_value = mock_cw

        emit_latency_metric(response_time_ms=30000)

        call_kwargs = mock_cw.put_metric_data.call_args[1]
        metric_data = call_kwargs["MetricData"]
        # Exactly 30000ms should NOT trigger breach (must exceed, not equal)
        assert len(metric_data) == 1
        assert metric_data[0]["MetricName"] == "AssessmentLatency"

    @patch("lambdas.shared.observability.boto3.client")
    def test_metric_emission_failure_does_not_raise(self, mock_client):
        """Metric emission failures should be swallowed to not break main flow."""
        from lambdas.shared.observability import emit_latency_metric

        mock_cw = MagicMock()
        mock_client.return_value = mock_cw
        mock_cw.put_metric_data.side_effect = Exception("CloudWatch unavailable")

        # Should not raise
        emit_latency_metric(response_time_ms=5000, request_id="req-789")

    @patch("lambdas.shared.observability.boto3.client")
    def test_no_dimensions_when_assessment_type_not_provided(self, mock_client):
        from lambdas.shared.observability import emit_latency_metric

        mock_cw = MagicMock()
        mock_client.return_value = mock_cw

        emit_latency_metric(response_time_ms=2000)

        call_kwargs = mock_cw.put_metric_data.call_args[1]
        metric_data = call_kwargs["MetricData"]
        assert metric_data[0]["Dimensions"] == []


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------


class TestObservabilityConstants:
    """Tests for observability module constants."""

    def test_latency_threshold_is_30_seconds(self):
        from lambdas.shared.observability import LATENCY_THRESHOLD_MS

        assert LATENCY_THRESHOLD_MS == 30_000

    def test_metrics_namespace(self):
        from lambdas.shared.observability import METRICS_NAMESPACE

        assert METRICS_NAMESPACE == "ConsumerRegulatoryAgent"
