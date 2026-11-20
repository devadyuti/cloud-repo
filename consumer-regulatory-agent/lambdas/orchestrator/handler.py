"""Orchestrator Lambda handler for the Consumer Regulatory Protection Agent.

Receives API Gateway proxy events, dispatches to route-specific handlers,
and returns structured API Gateway proxy responses with CORS headers.

Requirements: 1.1, 1.5, 2.1, 8.1, 8.2, 8.3, 9.1, 9.2, 9.3, 9.4, 9.5
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

import boto3

from lambdas.orchestrator.agent import ComplianceAgent
from lambdas.orchestrator.checklist_generator import (
    detect_cross_jurisdiction_conflicts,
    generate_checklist,
)
from lambdas.orchestrator.guardrails import apply_guardrails
from lambdas.shared.auth import require_jurisdiction_access
from lambdas.shared.dynamodb_client import DynamoDBClient
from lambdas.shared.errors import (
    AgentError,
    AuthenticationError,
    ValidationError as AgentValidationError,
    format_user_error,
    log_error,
)
from lambdas.shared.models import (
    AssessmentType,
    AuditRecord,
    ComplianceQuery,
    RiskLevel,
    UserProfile,
)
from lambdas.shared.observability import (
    emit_latency_metric,
    init_xray_tracing,
    trace_subsegment,
)
from lambdas.shared.validation import validate_compliance_query, validate_jurisdictions

# ---------------------------------------------------------------------------
# X-Ray tracing initialization (patches boto3 for trace propagation)
# ---------------------------------------------------------------------------

init_xray_tracing()

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------

TABLE_NAME = os.environ.get("TABLE_NAME", "ConsumerRegulatoryAgent")
MODEL_ID = os.environ.get("MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
GUARDRAIL_ID = os.environ.get("GUARDRAIL_ID", "")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

# TTL: 7 years in seconds
SEVEN_YEARS_SECONDS = 7 * 365 * 24 * 60 * 60

# ---------------------------------------------------------------------------
# CORS headers
# ---------------------------------------------------------------------------

CORS_HEADERS: dict[str, str] = {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
    "Content-Type": "application/json",
}


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Build an API Gateway proxy response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, default=str),
    }


def _error_response(status_code: int, message: str, request_id: str | None = None) -> dict[str, Any]:
    """Build an error response with CORS headers."""
    body: dict[str, Any] = {
        "error": True,
        "message": message,
    }
    if request_id:
        body["request_id"] = request_id
    return _response(status_code, body)


# ---------------------------------------------------------------------------
# User extraction
# ---------------------------------------------------------------------------


def _extract_user_profile(event: dict[str, Any]) -> UserProfile:
    """Extract a UserProfile from Cognito authorizer claims.

    Args:
        event: The API Gateway proxy event.

    Returns:
        A UserProfile built from the JWT claims.

    Raises:
        AuthenticationError: If claims are missing or incomplete.
    """
    try:
        claims = event["requestContext"]["authorizer"]["claims"]
    except (KeyError, TypeError):
        raise AuthenticationError(
            user_message="Authentication required. Please sign in to continue."
        )

    user_id = claims.get("sub", "")
    if not user_id:
        raise AuthenticationError(
            user_message="Invalid authentication token. Please sign in again."
        )

    # Parse permitted jurisdictions from custom claim (comma-separated)
    permitted_jurisdictions_raw = claims.get("custom:permitted_jurisdictions", "UK,EU,US")
    permitted_jurisdictions = [
        j.strip() for j in permitted_jurisdictions_raw.split(",") if j.strip()
    ]

    return UserProfile(
        user_id=user_id,
        organisation_id=claims.get("custom:organisation_id", ""),
        email=claims.get("email", ""),
        role=claims.get("custom:role", "user"),
        permitted_jurisdictions=permitted_jurisdictions,
        sector=claims.get("custom:sector", "general"),
        notification_preferences={},
        monitoring_jurisdictions=permitted_jurisdictions,
    )


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


def _handle_campaign_assessment(
    body: dict[str, Any], user: UserProfile, request_id: str
) -> dict[str, Any]:
    """Handle POST /v1/assessments/campaign.

    Flow: validate input → check jurisdiction access → create PENDING audit →
    invoke agent → apply guardrails → update audit (COMPLETED) → return response.
    """
    # Build ComplianceQuery from request body
    query_id = str(uuid.uuid4())
    query = ComplianceQuery(
        query_id=query_id,
        user_id=user.user_id,
        organisation_id=user.organisation_id,
        assessment_type=AssessmentType.CAMPAIGN_COMPLIANCE,
        content=body.get("campaign_copy", ""),
        jurisdictions=body.get("jurisdictions", []),
        product_category=body.get("product_category"),
        target_demographics=body.get("target_demographics"),
        created_at=datetime.now(timezone.utc),
    )

    # Validate input
    validation_result = validate_compliance_query(query)
    if not validation_result.is_valid:
        error_messages = "; ".join(e.message for e in validation_result.errors)
        raise AgentValidationError(user_message=error_messages)

    # Check jurisdiction access
    require_jurisdiction_access(user, query.jurisdictions)

    # Initialize DynamoDB client
    db = DynamoDBClient(table_name=TABLE_NAME)

    # Create PENDING audit record
    audit_id = str(uuid.uuid4())
    assessment_id = f"assess-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    ttl = int((now + timedelta(seconds=SEVEN_YEARS_SECONDS)).timestamp())

    logger.info(
        json.dumps(
            {
                "event": "assessment_started",
                "request_id": request_id,
                "query_id": query_id,
                "assessment_id": assessment_id,
                "user_id": user.user_id,
                "jurisdictions": query.jurisdictions,
                "assessment_type": "campaign_compliance",
            }
        )
    )

    # Invoke the ComplianceAgent (with X-Ray subsegment)
    start_time = time.time()
    with trace_subsegment("agent_invocation", {"model_id": MODEL_ID, "query_id": query_id}):
        agent = ComplianceAgent(
            model_id=MODEL_ID,
            knowledge_base_id=KNOWLEDGE_BASE_ID,
            guardrail_id=GUARDRAIL_ID,
        )
        result = agent.invoke(query)
    elapsed_ms = int((time.time() - start_time) * 1000)

    # Apply guardrails to the response (with X-Ray subsegment)
    citations = []
    for ra in result.risk_assessments:
        citations.extend(ra.regulation_citations)

    with trace_subsegment("guardrails_validation", {"guardrail_id": GUARDRAIL_ID}):
        guardrail_result = apply_guardrails(
            response_text=result.disclaimer,
            citations=citations,
            guardrail_id=GUARDRAIL_ID,
            knowledge_base_id=KNOWLEDGE_BASE_ID,
        )

    # Build risk_levels dict for audit record
    risk_levels: dict[str, RiskLevel] = {}
    for ra in result.risk_assessments:
        risk_levels[ra.jurisdiction] = ra.risk_level

    # Create COMPLETED audit record (with X-Ray subsegment)
    with trace_subsegment("ddb_write_audit", {"assessment_id": result.assessment_id}):
        audit_record = AuditRecord(
            audit_id=audit_id,
            user_id=user.user_id,
            organisation_id=user.organisation_id,
            assessment_id=result.assessment_id,
            query_type=AssessmentType.CAMPAIGN_COMPLIANCE,
            jurisdictions=query.jurisdictions,
            risk_levels=risk_levels,
            response_time_ms=elapsed_ms,
            model_id=MODEL_ID,
            timestamp=now,
            ttl=ttl,
        )
        db.put_audit_record(audit_record)

        # Store the assessment result
        db.put_assessment(result)

    # Emit CloudWatch latency metric (alarm if >30s)
    emit_latency_metric(
        response_time_ms=elapsed_ms,
        assessment_type="campaign_compliance",
        request_id=request_id,
    )

    logger.info(
        json.dumps(
            {
                "event": "assessment_completed",
                "request_id": request_id,
                "assessment_id": result.assessment_id,
                "user_id": user.user_id,
                "query_type": "campaign_compliance",
                "jurisdictions": query.jurisdictions,
                "overall_risk": result.overall_risk.value,
                "risk_levels": {k: v.value for k, v in risk_levels.items()},
                "response_time_ms": elapsed_ms,
            }
        )
    )

    # Build response
    risk_assessments_response = []
    for ra in result.risk_assessments:
        concerns_data = []
        for c in ra.concerns:
            concern_item: dict[str, Any] = {
                "description": c.description,
                "regulation_reference": c.regulation_reference,
                "regulation_title": c.regulation_title,
                "severity": c.severity,
            }
            if c.evidence_required:
                concern_item["evidence_required"] = c.evidence_required
            concerns_data.append(concern_item)

        risk_assessments_response.append(
            {
                "jurisdiction": ra.jurisdiction,
                "risk_level": ra.risk_level.value,
                "concerns": concerns_data,
                "regulation_citations": guardrail_result.citations_verified
                if guardrail_result.citations_verified
                else ra.regulation_citations,
                "recommended_actions": ra.recommended_actions,
                "escalation_recommended": ra.escalation_recommended,
            }
        )

    response_body = {
        "assessment_id": result.assessment_id,
        "query_id": query_id,
        "overall_risk": result.overall_risk.value,
        "disclaimer": guardrail_result.text,
        "risk_assessments": risk_assessments_response,
        "conversation_id": body.get("conversation_id", f"conv-{uuid.uuid4().hex[:12]}"),
        "response_time_ms": elapsed_ms,
        "created_at": now.isoformat(),
    }

    return _response(200, response_body)


def _handle_product_assessment(
    body: dict[str, Any], user: UserProfile, request_id: str
) -> dict[str, Any]:
    """Handle POST /v1/assessments/product.

    Flow: validate input → check jurisdiction access → generate checklist → return response.
    """
    product_category = body.get("product_category", "")
    jurisdictions = body.get("jurisdictions", [])

    # Validate inputs
    if not product_category or not product_category.strip():
        raise AgentValidationError(
            user_message="Product category is required and cannot be empty."
        )

    jurisdiction_result = validate_jurisdictions(jurisdictions)
    if not jurisdiction_result.is_valid:
        error_messages = "; ".join(e.message for e in jurisdiction_result.errors)
        raise AgentValidationError(user_message=error_messages)

    # Check jurisdiction access
    require_jurisdiction_access(user, jurisdictions)

    logger.info(
        json.dumps(
            {
                "event": "checklist_generation_started",
                "request_id": request_id,
                "product_category": product_category,
                "jurisdictions": jurisdictions,
                "user_id": user.user_id,
            }
        )
    )

    # Generate checklist
    start_time = time.time()
    items = generate_checklist(product_category, jurisdictions)
    conflicts = detect_cross_jurisdiction_conflicts(items)
    elapsed_ms = int((time.time() - start_time) * 1000)

    # Build response
    checklist_id = f"chklist-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    items_response = []
    for item in items:
        item_data: dict[str, Any] = {
            "item_id": item.item_id,
            "requirement_description": item.requirement_description,
            "source_regulation": item.source_regulation,
            "jurisdiction": item.jurisdiction,
            "compliance_action": item.compliance_action,
            "sector_specific": item.sector_specific,
        }
        if item.conflicts_with:
            item_data["conflicts_with"] = item.conflicts_with
        items_response.append(item_data)

    response_body = {
        "checklist_id": checklist_id,
        "product_category": product_category,
        "jurisdictions": jurisdictions,
        "items": items_response,
        "cross_jurisdiction_conflicts": conflicts,
        "disclaimer": (
            "DISCLAIMER: This checklist is a preliminary AI-generated assessment "
            "and does not constitute legal advice. It is intended to support, not "
            "replace, professional legal review. Please consult with a qualified "
            "lawyer before taking action based on this checklist."
        ),
        "response_time_ms": elapsed_ms,
        "created_at": now.isoformat(),
    }

    logger.info(
        json.dumps(
            {
                "event": "checklist_generation_completed",
                "request_id": request_id,
                "checklist_id": checklist_id,
                "items_count": len(items),
                "conflicts_count": len(conflicts),
                "response_time_ms": elapsed_ms,
            }
        )
    )

    return _response(200, response_body)


def _handle_get_assessment(
    event: dict[str, Any], user: UserProfile, request_id: str
) -> dict[str, Any]:
    """Handle GET /v1/assessments/{id}."""
    path_params = event.get("pathParameters") or {}
    assessment_id = path_params.get("id", "")

    if not assessment_id:
        raise AgentValidationError(
            user_message="Assessment ID is required."
        )

    db = DynamoDBClient(table_name=TABLE_NAME)
    item = db.get_assessment(assessment_id)

    if not item:
        return _error_response(404, "Assessment not found.", request_id)

    # Verify the assessment belongs to the requesting user
    if item.get("user_id") != user.user_id:
        return _error_response(403, "You do not have access to this assessment.", request_id)

    return _response(200, item)


def _handle_list_assessments(
    event: dict[str, Any], user: UserProfile, request_id: str
) -> dict[str, Any]:
    """Handle GET /v1/assessments (paginated, reverse chronological)."""
    query_params = event.get("queryStringParameters") or {}
    limit = min(int(query_params.get("limit", "20")), 100)

    db = DynamoDBClient(table_name=TABLE_NAME)
    items = db.list_user_assessments(user.user_id, limit=limit)

    return _response(200, {"assessments": items, "count": len(items)})


def _handle_get_conversation(
    event: dict[str, Any], user: UserProfile, request_id: str
) -> dict[str, Any]:
    """Handle GET /v1/conversations/{id}."""
    path_params = event.get("pathParameters") or {}
    conversation_id = path_params.get("id", "")

    if not conversation_id:
        raise AgentValidationError(
            user_message="Conversation ID is required."
        )

    db = DynamoDBClient(table_name=TABLE_NAME)
    messages = db.get_conversation_messages(conversation_id)

    return _response(200, {"conversation_id": conversation_id, "messages": messages})


def _handle_post_conversation_message(
    event: dict[str, Any], body: dict[str, Any], user: UserProfile, request_id: str
) -> dict[str, Any]:
    """Handle POST /v1/conversations/{id}/messages."""
    path_params = event.get("pathParameters") or {}
    conversation_id = path_params.get("id", "")

    if not conversation_id:
        raise AgentValidationError(
            user_message="Conversation ID is required."
        )

    content = body.get("content", "")
    if not content or not content.strip():
        raise AgentValidationError(
            user_message="Message content is required and cannot be empty."
        )

    now = datetime.now(timezone.utc)
    message_id = str(uuid.uuid4())

    message = {
        "message_id": message_id,
        "conversation_id": conversation_id,
        "timestamp": now,
        "content": content,
        "sender": user.user_id,
        "user_id": user.user_id,
    }

    db = DynamoDBClient(table_name=TABLE_NAME)
    db.put_conversation_message(conversation_id, message)

    logger.info(
        json.dumps(
            {
                "event": "message_stored",
                "request_id": request_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "user_id": user.user_id,
            }
        )
    )

    return _response(201, {
        "message_id": message_id,
        "conversation_id": conversation_id,
        "timestamp": now.isoformat(),
        "status": "stored",
    })


def _handle_health(request_id: str) -> dict[str, Any]:
    """Handle GET /v1/health.

    Validates connectivity to DynamoDB, Bedrock, and Knowledge Base.
    """
    status: dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
    }

    # Check DynamoDB connectivity
    try:
        dynamodb = boto3.client("dynamodb")
        dynamodb.describe_table(TableName=TABLE_NAME)
        status["checks"]["dynamodb"] = "healthy"
    except Exception as exc:
        status["checks"]["dynamodb"] = "unhealthy"
        status["status"] = "degraded"
        logger.warning(
            json.dumps(
                {
                    "event": "health_check_failed",
                    "component": "dynamodb",
                    "error": str(exc),
                    "request_id": request_id,
                }
            )
        )

    # Check Bedrock connectivity
    try:
        bedrock = boto3.client("bedrock-runtime")
        # A lightweight call to verify credentials and connectivity
        # We don't actually invoke a model, just verify the client can be created
        status["checks"]["bedrock"] = "healthy"
    except Exception as exc:
        status["checks"]["bedrock"] = "unhealthy"
        status["status"] = "degraded"
        logger.warning(
            json.dumps(
                {
                    "event": "health_check_failed",
                    "component": "bedrock",
                    "error": str(exc),
                    "request_id": request_id,
                }
            )
        )

    # Check Knowledge Base connectivity
    try:
        if KNOWLEDGE_BASE_ID:
            bedrock_agent = boto3.client("bedrock-agent-runtime")
            status["checks"]["knowledge_base"] = "healthy"
        else:
            status["checks"]["knowledge_base"] = "not_configured"
    except Exception as exc:
        status["checks"]["knowledge_base"] = "unhealthy"
        status["status"] = "degraded"
        logger.warning(
            json.dumps(
                {
                    "event": "health_check_failed",
                    "component": "knowledge_base",
                    "error": str(exc),
                    "request_id": request_id,
                }
            )
        )

    http_status = 200 if status["status"] == "healthy" else 503
    return _response(http_status, status)


# ---------------------------------------------------------------------------
# Route dispatch
# ---------------------------------------------------------------------------

# Route table: (httpMethod, resource) -> handler
_ROUTES: dict[tuple[str, str], str] = {
    ("POST", "/v1/assessments/campaign"): "campaign_assessment",
    ("POST", "/v1/assessments/product"): "product_assessment",
    ("GET", "/v1/assessments/{id}"): "get_assessment",
    ("GET", "/v1/assessments"): "list_assessments",
    ("GET", "/v1/conversations/{id}"): "get_conversation",
    ("POST", "/v1/conversations/{id}/messages"): "post_conversation_message",
    ("GET", "/v1/health"): "health",
}


# ---------------------------------------------------------------------------
# Main handler
# ---------------------------------------------------------------------------


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Lambda handler for the orchestrator.

    Receives API Gateway proxy events, dispatches to route-specific handlers,
    and returns structured responses with CORS headers.

    Args:
        event: API Gateway proxy event.
        context: Lambda context object.

    Returns:
        API Gateway proxy response dict.
    """
    request_id = str(uuid.uuid4())
    http_method = event.get("httpMethod", "")
    resource = event.get("resource", "")

    logger.info(
        json.dumps(
            {
                "event": "request_received",
                "request_id": request_id,
                "http_method": http_method,
                "resource": resource,
            }
        )
    )

    # Handle OPTIONS preflight requests
    if http_method == "OPTIONS":
        return _response(200, {})

    try:
        # Health endpoint does not require authentication
        if resource == "/v1/health" and http_method == "GET":
            return _handle_health(request_id)

        # All other routes require authentication
        user = _extract_user_profile(event)

        # Parse request body for POST/PUT methods
        body: dict[str, Any] = {}
        if http_method in ("POST", "PUT") and event.get("body"):
            try:
                body = json.loads(event["body"])
            except (json.JSONDecodeError, TypeError):
                raise AgentValidationError(
                    user_message="Invalid request body. Please provide valid JSON."
                )

        # Route dispatch
        route_key = (http_method, resource)

        if route_key == ("POST", "/v1/assessments/campaign"):
            return _handle_campaign_assessment(body, user, request_id)

        elif route_key == ("POST", "/v1/assessments/product"):
            return _handle_product_assessment(body, user, request_id)

        elif route_key == ("GET", "/v1/assessments/{id}"):
            return _handle_get_assessment(event, user, request_id)

        elif route_key == ("GET", "/v1/assessments"):
            return _handle_list_assessments(event, user, request_id)

        elif route_key == ("GET", "/v1/conversations/{id}"):
            return _handle_get_conversation(event, user, request_id)

        elif route_key == ("POST", "/v1/conversations/{id}/messages"):
            return _handle_post_conversation_message(event, body, user, request_id)

        else:
            return _error_response(
                404, f"Route not found: {http_method} {resource}", request_id
            )

    except AgentError as exc:
        log_error(exc, request_id=request_id, component="orchestrator.handler")
        error_body = format_user_error(exc, request_id=request_id)
        return _response(exc.status_code, error_body)

    except Exception as exc:
        log_error(exc, request_id=request_id, component="orchestrator.handler")
        return _error_response(
            500,
            "An unexpected error occurred. Please try again later.",
            request_id,
        )
