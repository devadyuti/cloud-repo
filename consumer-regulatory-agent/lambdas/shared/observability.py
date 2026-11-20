"""Observability utilities for the Consumer Regulatory Protection Agent.

Provides X-Ray tracing setup, structured JSON logging, CloudWatch custom metrics,
and subsegment context managers for distributed tracing across service boundaries.

Requirements: 9.1, 9.2, 9.3, 9.4
"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator

import boto3

# ---------------------------------------------------------------------------
# X-Ray SDK setup (conditional import for testability)
# ---------------------------------------------------------------------------

_XRAY_ENABLED = os.environ.get("AWS_XRAY_DAEMON_ADDRESS") or os.environ.get(
    "ENABLE_XRAY", ""
)

try:
    from aws_xray_sdk.core import xray_recorder, patch_all as _xray_patch_all

    _XRAY_SDK_AVAILABLE = True
except ImportError:
    _XRAY_SDK_AVAILABLE = False
    xray_recorder = None  # type: ignore[assignment]
    _xray_patch_all = None  # type: ignore[assignment]


def init_xray_tracing() -> None:
    """Initialize X-Ray tracing and patch boto3/requests for trace propagation.

    Patches boto3 and botocore so that all AWS SDK calls automatically
    propagate trace IDs across API Gateway → Lambda → Bedrock → DynamoDB.

    Safe to call in test environments where X-Ray SDK is not available or
    the daemon is not running — will silently no-op.
    """
    if not _XRAY_SDK_AVAILABLE:
        return

    if not _XRAY_ENABLED:
        # In test/local environments without X-Ray daemon, disable SDK
        xray_recorder.configure(context_missing="LOG_ERROR")
        return

    # Configure recorder for Lambda environment
    xray_recorder.configure(
        context_missing="LOG_ERROR",
        daemon_address=os.environ.get("AWS_XRAY_DAEMON_ADDRESS", "127.0.0.1:2000"),
    )

    # Patch boto3, botocore, and requests for automatic trace propagation
    _xray_patch_all()


# ---------------------------------------------------------------------------
# Subsegment tracing context manager
# ---------------------------------------------------------------------------


@contextmanager
def trace_subsegment(
    name: str, metadata: dict[str, Any] | None = None
) -> Generator[Any, None, None]:
    """Context manager for creating X-Ray subsegments around operations.

    Usage:
        with trace_subsegment("agent_invocation", {"model_id": model_id}):
            result = agent.invoke(query)

    Args:
        name: Name of the subsegment (e.g., 'agent_invocation', 'guardrails', 'ddb_write').
        metadata: Optional metadata dict to attach to the subsegment.

    Yields:
        The subsegment object (or None if X-Ray is not available).
    """
    if not _XRAY_SDK_AVAILABLE or not _XRAY_ENABLED:
        yield None
        return

    subsegment = None
    try:
        subsegment = xray_recorder.begin_subsegment(name)
        if subsegment and metadata:
            for key, value in metadata.items():
                subsegment.put_metadata(key, value)
        yield subsegment
    except Exception as exc:
        if subsegment:
            subsegment.add_exception(exc)
        raise
    finally:
        try:
            xray_recorder.end_subsegment()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Structured JSON logger factory
# ---------------------------------------------------------------------------


class StructuredLogger:
    """Structured JSON logger with consistent fields for CloudWatch Logs.

    Emits log entries as JSON objects with standard fields:
    - timestamp, level, event, request_id, component
    - Plus any additional context fields passed at log time.
    """

    def __init__(self, name: str, component: str | None = None) -> None:
        """Initialize the structured logger.

        Args:
            name: Logger name (typically __name__).
            component: Component identifier (e.g., 'orchestrator.handler').
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)
        self._component = component or name

    def info(self, event: str, **kwargs: Any) -> None:
        """Emit a structured INFO log entry."""
        self._emit("INFO", event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        """Emit a structured WARNING log entry."""
        self._emit("WARNING", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        """Emit a structured ERROR log entry."""
        self._emit("ERROR", event, **kwargs)

    def _emit(self, level: str, event: str, **kwargs: Any) -> None:
        """Emit a structured log entry as JSON."""
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "component": self._component,
            "event": event,
        }
        entry.update(kwargs)

        log_line = json.dumps(entry, default=str)

        if level == "ERROR":
            self._logger.error(log_line)
        elif level == "WARNING":
            self._logger.warning(log_line)
        else:
            self._logger.info(log_line)


def get_logger(name: str, component: str | None = None) -> StructuredLogger:
    """Factory function to create a StructuredLogger.

    Args:
        name: Logger name (typically __name__).
        component: Component identifier for log entries.

    Returns:
        A configured StructuredLogger instance.
    """
    return StructuredLogger(name, component)


# ---------------------------------------------------------------------------
# CloudWatch custom metrics helper
# ---------------------------------------------------------------------------

# Latency threshold in milliseconds (30 seconds)
LATENCY_THRESHOLD_MS = 30_000

# CloudWatch namespace for all agent metrics
METRICS_NAMESPACE = "ConsumerRegulatoryAgent"


def emit_latency_metric(
    response_time_ms: int,
    assessment_type: str | None = None,
    request_id: str | None = None,
) -> None:
    """Emit CloudWatch custom metrics for assessment latency.

    Emits:
    - AssessmentLatency: The actual response time in milliseconds.
    - LatencyThresholdBreached: Emitted (value=1) when response_time_ms > 30000ms.

    Args:
        response_time_ms: The response time in milliseconds.
        assessment_type: Optional assessment type for metric dimensions.
        request_id: Optional request ID for logging context.
    """
    try:
        cloudwatch = boto3.client("cloudwatch")

        dimensions = []
        if assessment_type:
            dimensions.append({"Name": "AssessmentType", "Value": assessment_type})

        # Always emit the latency metric
        metric_data: list[dict[str, Any]] = [
            {
                "MetricName": "AssessmentLatency",
                "Value": float(response_time_ms),
                "Unit": "Milliseconds",
                "Timestamp": datetime.now(timezone.utc),
                "Dimensions": dimensions,
            }
        ]

        # Emit threshold breach metric if latency exceeds 30s
        if response_time_ms > LATENCY_THRESHOLD_MS:
            metric_data.append(
                {
                    "MetricName": "LatencyThresholdBreached",
                    "Value": 1.0,
                    "Unit": "Count",
                    "Timestamp": datetime.now(timezone.utc),
                    "Dimensions": dimensions,
                }
            )

            # Log the threshold breach
            logger = logging.getLogger(__name__)
            logger.warning(
                json.dumps(
                    {
                        "event": "latency_threshold_breached",
                        "response_time_ms": response_time_ms,
                        "threshold_ms": LATENCY_THRESHOLD_MS,
                        "request_id": request_id,
                        "assessment_type": assessment_type,
                    }
                )
            )

        cloudwatch.put_metric_data(
            Namespace=METRICS_NAMESPACE,
            MetricData=metric_data,
        )

    except Exception as exc:
        # Metrics emission should never break the main flow
        logger = logging.getLogger(__name__)
        logger.warning(
            json.dumps(
                {
                    "event": "metric_emission_failed",
                    "error": str(exc),
                    "request_id": request_id,
                }
            )
        )
