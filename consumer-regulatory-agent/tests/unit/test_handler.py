"""Unit tests for the orchestrator Lambda handler.

Tests route dispatch, error handling, CORS headers, and individual
route handler logic.

Requirements: 1.1, 1.5, 2.1, 8.1, 8.2, 8.3, 9.5
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Set environment variables before importing handler
os.environ.setdefault("TABLE_NAME", "TestTable")
os.environ.setdefault("MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
os.environ.setdefault("KNOWLEDGE_BASE_ID", "test-kb-id")
os.environ.setdefault("GUARDRAIL_ID", "test-guardrail-id")

from lambdas.orchestrator.handler import (
    CORS_HEADERS,
    _error_response,
    _extract_user_profile,
    _response,
    handler,
)
from lambdas.shared.errors import AuthenticationError, AuthorisationError
from lambdas.shared.models import UserProfile


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _make_event(
    method: str = "GET",
    resource: str = "/v1/health",
    body: dict | None = None,
    path_params: dict | None = None,
    query_params: dict | None = None,
    claims: dict | None = None,
) -> dict:
    """Build a minimal API Gateway proxy event."""
    event = {
        "httpMethod": method,
        "resource": resource,
        "pathParameters": path_params,
        "queryStringParameters": query_params,
        "body": json.dumps(body) if body else None,
        "requestContext": {},
    }
    if claims is not None:
        event["requestContext"]["authorizer"] = {"claims": claims}
    return event


def _default_claims() -> dict:
    """Return default Cognito claims for a test user."""
    return {
        "sub": "user-123",
        "email": "test@example.com",
        "custom:organisation_id": "org-456",
        "custom:permitted_jurisdictions": "UK,EU,US",
        "custom:role": "compliance_officer",
        "custom:sector": "retail",
    }


# ---------------------------------------------------------------------------
# Response helper tests
# ---------------------------------------------------------------------------


class TestResponseHelpers:
    """Tests for _response and _error_response helpers."""

    def test_response_includes_cors_headers(self):
        result = _response(200, {"key": "value"})
        assert result["statusCode"] == 200
        assert "Access-Control-Allow-Origin" in result["headers"]
        assert "Access-Control-Allow-Headers" in result["headers"]
        assert "Access-Control-Allow-Methods" in result["headers"]

    def test_response_body_is_json_string(self):
        result = _response(200, {"key": "value"})
        body = json.loads(result["body"])
        assert body["key"] == "value"

    def test_error_response_includes_error_flag(self):
        result = _error_response(400, "Bad request", "req-123")
        body = json.loads(result["body"])
        assert body["error"] is True
        assert body["message"] == "Bad request"
        assert body["request_id"] == "req-123"

    def test_error_response_without_request_id(self):
        result = _error_response(500, "Server error")
        body = json.loads(result["body"])
        assert "request_id" not in body or body.get("request_id") is None


# ---------------------------------------------------------------------------
# User extraction tests
# ---------------------------------------------------------------------------


class TestExtractUserProfile:
    """Tests for _extract_user_profile."""

    def test_extracts_user_from_valid_claims(self):
        event = _make_event(claims=_default_claims())
        user = _extract_user_profile(event)

        assert user.user_id == "user-123"
        assert user.organisation_id == "org-456"
        assert user.email == "test@example.com"
        assert user.role == "compliance_officer"
        assert user.permitted_jurisdictions == ["UK", "EU", "US"]
        assert user.sector == "retail"

    def test_raises_authentication_error_when_no_authorizer(self):
        event = {"requestContext": {}}
        with pytest.raises(AuthenticationError):
            _extract_user_profile(event)

    def test_raises_authentication_error_when_no_sub(self):
        event = _make_event(claims={"email": "test@example.com"})
        with pytest.raises(AuthenticationError):
            _extract_user_profile(event)

    def test_defaults_for_missing_custom_claims(self):
        event = _make_event(claims={"sub": "user-999"})
        user = _extract_user_profile(event)

        assert user.user_id == "user-999"
        assert user.role == "user"
        assert user.sector == "general"
        assert user.permitted_jurisdictions == ["UK", "EU", "US"]


# ---------------------------------------------------------------------------
# Route dispatch tests
# ---------------------------------------------------------------------------


class TestRouteDispatch:
    """Tests for the main handler route dispatch."""

    def test_options_returns_200(self):
        event = _make_event(method="OPTIONS", resource="/v1/assessments/campaign")
        result = handler(event, None)
        assert result["statusCode"] == 200

    def test_unknown_route_returns_404(self):
        event = _make_event(
            method="GET",
            resource="/v1/unknown",
            claims=_default_claims(),
        )
        result = handler(event, None)
        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert "Route not found" in body["message"]

    def test_unauthenticated_non_health_returns_401(self):
        event = _make_event(method="GET", resource="/v1/assessments")
        result = handler(event, None)
        assert result["statusCode"] == 401

    @patch("lambdas.orchestrator.handler.boto3")
    def test_health_endpoint_no_auth_required(self, mock_boto3):
        """Health endpoint should work without authentication."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_table.return_value = {"Table": {"TableName": "TestTable"}}

        event = _make_event(method="GET", resource="/v1/health")
        result = handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "healthy"
        assert "checks" in body
        assert "timestamp" in body


# ---------------------------------------------------------------------------
# Health endpoint tests
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """Tests for GET /v1/health."""

    @patch("lambdas.orchestrator.handler.boto3")
    def test_healthy_when_all_services_available(self, mock_boto3):
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_table.return_value = {"Table": {}}

        event = _make_event(method="GET", resource="/v1/health")
        result = handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "healthy"
        assert body["checks"]["dynamodb"] == "healthy"
        assert body["checks"]["bedrock"] == "healthy"

    @patch("lambdas.orchestrator.handler.boto3")
    def test_degraded_when_dynamodb_unavailable(self, mock_boto3):
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.describe_table.side_effect = Exception("Connection refused")

        event = _make_event(method="GET", resource="/v1/health")
        result = handler(event, None)

        assert result["statusCode"] == 503
        body = json.loads(result["body"])
        assert body["status"] == "degraded"
        assert body["checks"]["dynamodb"] == "unhealthy"


# ---------------------------------------------------------------------------
# Campaign assessment tests
# ---------------------------------------------------------------------------


class TestCampaignAssessment:
    """Tests for POST /v1/assessments/campaign."""

    def test_validation_error_empty_campaign_copy(self):
        event = _make_event(
            method="POST",
            resource="/v1/assessments/campaign",
            body={"campaign_copy": "", "jurisdictions": ["UK"]},
            claims=_default_claims(),
        )
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_validation_error_empty_jurisdictions(self):
        event = _make_event(
            method="POST",
            resource="/v1/assessments/campaign",
            body={"campaign_copy": "Buy our product!", "jurisdictions": []},
            claims=_default_claims(),
        )
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_validation_error_unsupported_jurisdiction(self):
        event = _make_event(
            method="POST",
            resource="/v1/assessments/campaign",
            body={"campaign_copy": "Buy our product!", "jurisdictions": ["JP"]},
            claims=_default_claims(),
        )
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_jurisdiction_access_denied(self):
        claims = _default_claims()
        claims["custom:permitted_jurisdictions"] = "UK"

        event = _make_event(
            method="POST",
            resource="/v1/assessments/campaign",
            body={"campaign_copy": "Buy our product!", "jurisdictions": ["EU"]},
            claims=claims,
        )
        result = handler(event, None)
        assert result["statusCode"] == 403

    def test_invalid_json_body(self):
        event = _make_event(
            method="POST",
            resource="/v1/assessments/campaign",
            claims=_default_claims(),
        )
        event["body"] = "not valid json {"
        result = handler(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "Invalid request body" in body["message"]

    @patch("lambdas.orchestrator.handler.DynamoDBClient")
    @patch("lambdas.orchestrator.handler.apply_guardrails")
    @patch("lambdas.orchestrator.handler.ComplianceAgent")
    def test_successful_campaign_assessment(
        self, mock_agent_cls, mock_guardrails, mock_db_cls
    ):
        """Test the full campaign assessment flow with mocked dependencies."""
        from lambdas.shared.models import (
            AssessmentResult,
            AssessmentType,
            RiskAssessment,
            RiskLevel,
        )
        from lambdas.orchestrator.guardrails import GuardrailResult

        # Mock agent
        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_agent.invoke.return_value = AssessmentResult(
            assessment_id="assess-test123",
            query_id="query-123",
            user_id="user-123",
            assessment_type=AssessmentType.CAMPAIGN_COMPLIANCE,
            risk_assessments=[
                RiskAssessment(
                    jurisdiction="UK",
                    risk_level=RiskLevel.MEDIUM,
                    concerns=[],
                    regulation_citations=["CAP Code 3.1"],
                    recommended_actions=["Review claims"],
                    escalation_recommended=False,
                )
            ],
            disclaimer="Test disclaimer",
            overall_risk=RiskLevel.MEDIUM,
            created_at=datetime.now(timezone.utc),
            response_time_ms=1500,
            model_id="test-model",
            knowledge_base_version="latest",
        )

        # Mock guardrails
        mock_guardrails.return_value = GuardrailResult(
            text="DISCLAIMER: ...\n\nTest disclaimer",
            citations_verified=["CAP Code 3.1"],
            citations_removed=[],
            disclaimer_injected=True,
            definitive_phrases_blocked=[],
            gaps_flagged=False,
        )

        # Mock DynamoDB
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db

        event = _make_event(
            method="POST",
            resource="/v1/assessments/campaign",
            body={
                "campaign_copy": "Get 50% more value than Brand X!",
                "jurisdictions": ["UK"],
                "product_category": "cosmetics",
            },
            claims=_default_claims(),
        )

        result = handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["assessment_id"] == "assess-test123"
        assert body["overall_risk"] == "Medium"
        assert "risk_assessments" in body
        assert len(body["risk_assessments"]) == 1
        assert body["risk_assessments"][0]["jurisdiction"] == "UK"
        assert "disclaimer" in body
        assert "response_time_ms" in body
        assert "created_at" in body

        # Verify audit record was created
        mock_db.put_audit_record.assert_called_once()
        mock_db.put_assessment.assert_called_once()


# ---------------------------------------------------------------------------
# Product assessment tests
# ---------------------------------------------------------------------------


class TestProductAssessment:
    """Tests for POST /v1/assessments/product."""

    def test_validation_error_empty_product_category(self):
        event = _make_event(
            method="POST",
            resource="/v1/assessments/product",
            body={"product_category": "", "jurisdictions": ["UK"]},
            claims=_default_claims(),
        )
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_validation_error_empty_jurisdictions(self):
        event = _make_event(
            method="POST",
            resource="/v1/assessments/product",
            body={"product_category": "food", "jurisdictions": []},
            claims=_default_claims(),
        )
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_jurisdiction_access_denied(self):
        claims = _default_claims()
        claims["custom:permitted_jurisdictions"] = "UK"

        event = _make_event(
            method="POST",
            resource="/v1/assessments/product",
            body={"product_category": "food", "jurisdictions": ["EU"]},
            claims=claims,
        )
        result = handler(event, None)
        assert result["statusCode"] == 403

    def test_successful_product_checklist(self):
        event = _make_event(
            method="POST",
            resource="/v1/assessments/product",
            body={"product_category": "food", "jurisdictions": ["UK"]},
            claims=_default_claims(),
        )
        result = handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["product_category"] == "food"
        assert body["jurisdictions"] == ["UK"]
        assert "items" in body
        assert len(body["items"]) > 0
        assert "disclaimer" in body
        assert "DISCLAIMER" in body["disclaimer"]
        assert "checklist_id" in body

    def test_product_checklist_with_multiple_jurisdictions(self):
        event = _make_event(
            method="POST",
            resource="/v1/assessments/product",
            body={"product_category": "electronics", "jurisdictions": ["UK", "EU"]},
            claims=_default_claims(),
        )
        result = handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "cross_jurisdiction_conflicts" in body
        assert len(body["cross_jurisdiction_conflicts"]) > 0


# ---------------------------------------------------------------------------
# GET assessments tests
# ---------------------------------------------------------------------------


class TestGetAssessments:
    """Tests for GET /v1/assessments and GET /v1/assessments/{id}."""

    @patch("lambdas.orchestrator.handler.DynamoDBClient")
    def test_list_assessments_returns_user_assessments(self, mock_db_cls):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.list_user_assessments.return_value = [
            {"assessment_id": "assess-1", "created_at": "2025-01-01T00:00:00Z"},
            {"assessment_id": "assess-2", "created_at": "2025-01-02T00:00:00Z"},
        ]

        event = _make_event(
            method="GET",
            resource="/v1/assessments",
            claims=_default_claims(),
        )
        result = handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["count"] == 2
        assert len(body["assessments"]) == 2

    @patch("lambdas.orchestrator.handler.DynamoDBClient")
    def test_list_assessments_respects_limit(self, mock_db_cls):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.list_user_assessments.return_value = []

        event = _make_event(
            method="GET",
            resource="/v1/assessments",
            query_params={"limit": "5"},
            claims=_default_claims(),
        )
        handler(event, None)

        mock_db.list_user_assessments.assert_called_once_with("user-123", limit=5)

    @patch("lambdas.orchestrator.handler.DynamoDBClient")
    def test_list_assessments_caps_limit_at_100(self, mock_db_cls):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.list_user_assessments.return_value = []

        event = _make_event(
            method="GET",
            resource="/v1/assessments",
            query_params={"limit": "500"},
            claims=_default_claims(),
        )
        handler(event, None)

        mock_db.list_user_assessments.assert_called_once_with("user-123", limit=100)

    @patch("lambdas.orchestrator.handler.DynamoDBClient")
    def test_get_assessment_by_id(self, mock_db_cls):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get_assessment.return_value = {
            "assessment_id": "assess-abc",
            "user_id": "user-123",
            "overall_risk": "Medium",
        }

        event = _make_event(
            method="GET",
            resource="/v1/assessments/{id}",
            path_params={"id": "assess-abc"},
            claims=_default_claims(),
        )
        result = handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["assessment_id"] == "assess-abc"

    @patch("lambdas.orchestrator.handler.DynamoDBClient")
    def test_get_assessment_not_found(self, mock_db_cls):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get_assessment.return_value = None

        event = _make_event(
            method="GET",
            resource="/v1/assessments/{id}",
            path_params={"id": "nonexistent"},
            claims=_default_claims(),
        )
        result = handler(event, None)

        assert result["statusCode"] == 404

    @patch("lambdas.orchestrator.handler.DynamoDBClient")
    def test_get_assessment_access_denied_other_user(self, mock_db_cls):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get_assessment.return_value = {
            "assessment_id": "assess-abc",
            "user_id": "other-user",
            "overall_risk": "Medium",
        }

        event = _make_event(
            method="GET",
            resource="/v1/assessments/{id}",
            path_params={"id": "assess-abc"},
            claims=_default_claims(),
        )
        result = handler(event, None)

        assert result["statusCode"] == 403


# ---------------------------------------------------------------------------
# Conversation tests
# ---------------------------------------------------------------------------


class TestConversations:
    """Tests for conversation endpoints."""

    @patch("lambdas.orchestrator.handler.DynamoDBClient")
    def test_get_conversation_messages(self, mock_db_cls):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db
        mock_db.get_conversation_messages.return_value = [
            {"message_id": "msg-1", "content": "Hello", "sender": "user-123"},
        ]

        event = _make_event(
            method="GET",
            resource="/v1/conversations/{id}",
            path_params={"id": "conv-abc"},
            claims=_default_claims(),
        )
        result = handler(event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["conversation_id"] == "conv-abc"
        assert len(body["messages"]) == 1

    @patch("lambdas.orchestrator.handler.DynamoDBClient")
    def test_post_conversation_message(self, mock_db_cls):
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db

        event = _make_event(
            method="POST",
            resource="/v1/conversations/{id}/messages",
            path_params={"id": "conv-abc"},
            body={"content": "What about EU regulations?"},
            claims=_default_claims(),
        )
        result = handler(event, None)

        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert body["conversation_id"] == "conv-abc"
        assert body["status"] == "stored"
        assert "message_id" in body
        assert "timestamp" in body

        mock_db.put_conversation_message.assert_called_once()

    def test_post_conversation_message_empty_content(self):
        event = _make_event(
            method="POST",
            resource="/v1/conversations/{id}/messages",
            path_params={"id": "conv-abc"},
            body={"content": ""},
            claims=_default_claims(),
        )
        result = handler(event, None)
        assert result["statusCode"] == 400

    def test_get_conversation_missing_id(self):
        event = _make_event(
            method="GET",
            resource="/v1/conversations/{id}",
            path_params={"id": ""},
            claims=_default_claims(),
        )
        result = handler(event, None)
        assert result["statusCode"] == 400


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for global error handling in the handler."""

    def test_agent_error_returns_proper_status_code(self):
        """AgentError subclasses should return their status_code."""
        event = _make_event(
            method="POST",
            resource="/v1/assessments/campaign",
            body={"campaign_copy": "", "jurisdictions": ["UK"]},
            claims=_default_claims(),
        )
        result = handler(event, None)
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["error"] is True
        assert "request_id" in body

    @patch("lambdas.orchestrator.handler._extract_user_profile")
    def test_unexpected_exception_returns_500(self, mock_extract):
        """Unexpected exceptions should return 500 with generic message."""
        mock_extract.side_effect = RuntimeError("Unexpected failure")

        event = _make_event(
            method="GET",
            resource="/v1/assessments",
            claims=_default_claims(),
        )
        result = handler(event, None)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["error"] is True
        assert "unexpected error" in body["message"].lower()
        # Should NOT contain internal details
        assert "RuntimeError" not in body["message"]
        assert "Unexpected failure" not in body["message"]

    def test_all_responses_have_cors_headers(self):
        """Every response should include CORS headers."""
        # Test 404
        event = _make_event(
            method="GET",
            resource="/v1/nonexistent",
            claims=_default_claims(),
        )
        result = handler(event, None)
        assert "Access-Control-Allow-Origin" in result["headers"]

        # Test 400
        event = _make_event(
            method="POST",
            resource="/v1/assessments/campaign",
            body={"campaign_copy": "", "jurisdictions": []},
            claims=_default_claims(),
        )
        result = handler(event, None)
        assert "Access-Control-Allow-Origin" in result["headers"]
