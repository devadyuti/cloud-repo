"""Error handling utilities for the Consumer Regulatory Protection Agent.

Provides custom exception classes, user-friendly error formatting,
structured logging, and retry logic with exponential backoff.

Requirements: 9.4
"""

from __future__ import annotations

import json
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom Exception Classes
# ---------------------------------------------------------------------------


class AgentError(Exception):
    """Base exception for all agent errors.

    Attributes:
        status_code: HTTP status code for the error response.
        user_message: Safe, user-facing error message (no internal details).
        internal_message: Detailed message for internal logging.
    """

    status_code: int = 500
    user_message: str = "An unexpected error occurred. Please try again later."
    internal_message: str = ""

    def __init__(
        self,
        user_message: str | None = None,
        internal_message: str | None = None,
        status_code: int | None = None,
    ):
        if user_message is not None:
            self.user_message = user_message
        if internal_message is not None:
            self.internal_message = internal_message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(self.user_message)


class ValidationError(AgentError):
    """Raised when request input fails validation (400)."""

    status_code = 400
    user_message = "Please provide the required fields to proceed with the assessment."


class AuthenticationError(AgentError):
    """Raised when authentication fails (401)."""

    status_code = 401
    user_message = "Your session has expired. Please sign in again."


class AuthorisationError(AgentError):
    """Raised when user lacks permission for the requested resource (403)."""

    status_code = 403
    user_message = "Your organisation does not have access to the requested assessments."


class UnsupportedJurisdictionError(AgentError):
    """Raised when a requested jurisdiction is not available (422)."""

    status_code = 422
    user_message = (
        "Assessment for the requested jurisdiction is not currently available."
    )


class AgentTimeoutError(AgentError):
    """Raised when agent processing exceeds the timeout threshold (504)."""

    status_code = 504
    user_message = (
        "The assessment is taking longer than expected. "
        "Please try again or simplify your query."
    )


class KnowledgeBaseError(AgentError):
    """Raised when Knowledge Base retrieval fails (502)."""

    status_code = 502
    user_message = (
        "We're experiencing a temporary issue retrieving regulatory data. "
        "Please try again shortly."
    )


class ModelError(AgentError):
    """Raised when Bedrock model invocation fails (502)."""

    status_code = 502
    user_message = (
        "The compliance engine is temporarily unavailable. "
        "Please try again in a few minutes."
    )


class PersistenceError(AgentError):
    """Raised when DynamoDB write operations fail (500)."""

    status_code = 500
    user_message = (
        "Your assessment was completed but we couldn't save it. "
        "Please contact support with your request ID."
    )


class EscalationError(AgentError):
    """Raised when escalation service fails (200 partial success)."""

    status_code = 200
    user_message = (
        "Escalation could not be completed. Your brief has been saved. "
        "Please contact the Consumer Markets team directly for assistance."
    )


# ---------------------------------------------------------------------------
# User-Friendly Error Message Formatter
# ---------------------------------------------------------------------------


def format_user_error(error: AgentError, request_id: str | None = None) -> dict:
    """Format an AgentError into a user-safe response dict.

    Returns a dict suitable for JSON serialisation in API responses.
    NEVER includes stack traces, internal service names, or implementation details.

    Args:
        error: The AgentError instance to format.
        request_id: Optional request ID for user reference.

    Returns:
        Dict with keys: error (bool), message (str), request_id (str or None).
    """
    response: dict[str, Any] = {
        "error": True,
        "message": error.user_message,
        "request_id": request_id,
    }
    return response


# ---------------------------------------------------------------------------
# Structured Logging Helper
# ---------------------------------------------------------------------------


def log_error(
    error: Exception,
    request_id: str,
    component: str,
    **context: Any,
) -> None:
    """Log an error with full structured context for internal observability.

    Emits a JSON-formatted log entry at ERROR level containing all diagnostic
    information needed for debugging and alerting.

    Args:
        error: The exception that occurred.
        request_id: Unique request identifier for correlation.
        component: Name of the component where the error originated.
        **context: Additional key-value pairs to include in the log entry.
    """
    log_entry: dict[str, Any] = {
        "request_id": request_id,
        "component": component,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "stack_trace": traceback.format_exc(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Merge any additional context
    log_entry.update(context)

    logger.error(json.dumps(log_entry))


# ---------------------------------------------------------------------------
# Retry Configuration
# ---------------------------------------------------------------------------

RETRY_CONFIG: dict[str, dict[str, Any]] = {
    "bedrock_invoke": {
        "max_attempts": 3,
        "backoff_base": 1.0,
        "backoff_multiplier": 2.0,
        "retryable_errors": ["ThrottlingException", "ServiceUnavailableException"],
    },
    "dynamodb_write": {
        "max_attempts": 3,
        "backoff_base": 0.5,
        "backoff_multiplier": 2.0,
        "retryable_errors": [
            "ProvisionedThroughputExceededException",
            "InternalServerError",
        ],
    },
    "knowledge_base_retrieve": {
        "max_attempts": 3,
        "backoff_base": 1.0,
        "backoff_multiplier": 2.0,
        "retryable_errors": ["ThrottlingException", "ServiceUnavailableException"],
    },
    "escalation_service": {
        "max_attempts": 2,
        "backoff_base": 2.0,
        "backoff_multiplier": 2.0,
        "retryable_errors": ["ConnectionError", "TimeoutError"],
    },
}


# ---------------------------------------------------------------------------
# Retry Logic with Exponential Backoff
# ---------------------------------------------------------------------------


def retry_with_backoff(
    operation: str,
    func: Callable,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute a function with retry logic and exponential backoff.

    Uses RETRY_CONFIG to determine max attempts, backoff timing, and which
    error types are retryable for the given operation.

    Args:
        operation: Key into RETRY_CONFIG (e.g. "bedrock_invoke", "dynamodb_write").
        func: The callable to execute.
        *args: Positional arguments passed to func.
        **kwargs: Keyword arguments passed to func.

    Returns:
        The return value of func on success.

    Raises:
        ValueError: If operation is not found in RETRY_CONFIG.
        Exception: The last exception raised if all retry attempts are exhausted.
    """
    if operation not in RETRY_CONFIG:
        raise ValueError(
            f"Unknown operation '{operation}'. "
            f"Valid operations: {list(RETRY_CONFIG.keys())}"
        )

    config = RETRY_CONFIG[operation]
    max_attempts: int = config["max_attempts"]
    backoff_base: float = config["backoff_base"]
    backoff_multiplier: float = config["backoff_multiplier"]
    retryable_errors: list[str] = config["retryable_errors"]

    last_exception: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exception = exc
            error_name = type(exc).__name__

            if error_name not in retryable_errors:
                # Non-retryable error — raise immediately
                raise

            if attempt >= max_attempts:
                # All retries exhausted
                logger.warning(
                    json.dumps(
                        {
                            "event": "retry_exhausted",
                            "operation": operation,
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "error_type": error_name,
                            "error_message": str(exc),
                        }
                    )
                )
                raise

            # Calculate backoff delay: base * multiplier^(attempt-1)
            delay = backoff_base * (backoff_multiplier ** (attempt - 1))

            logger.warning(
                json.dumps(
                    {
                        "event": "retry_attempt",
                        "operation": operation,
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "error_type": error_name,
                        "error_message": str(exc),
                        "backoff_seconds": delay,
                    }
                )
            )

            time.sleep(delay)

    # Should not reach here, but satisfy type checker
    if last_exception is not None:
        raise last_exception
    raise RuntimeError(f"Retry logic failed unexpectedly for operation '{operation}'")
