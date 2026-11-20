"""DynamoDB single-table data access layer for the Consumer Regulatory Protection Agent.

Implements access patterns for assessments, audit records, conversations,
and user preferences using composite keys and GSI1 for user-scoped queries.

Requirements: 8.1, 8.2, 8.3, 8.4
"""

from __future__ import annotations

import os
from datetime import datetime
from enum import Enum
from typing import Optional

import boto3
from boto3.dynamodb.conditions import Key

from lambdas.shared.models import (
    AssessmentResult,
    AssessmentType,
    AuditRecord,
    RiskLevel,
    UserProfile,
)


class DynamoDBClient:
    """Single-table DynamoDB client for all entity access patterns.

    Uses composite primary keys (PK/SK) and GSI1 for user-scoped
    reverse chronological queries.
    """

    GSI1_NAME = "GSI1"

    def __init__(
        self,
        table_name: str | None = None,
    ) -> None:
        self._table_name = table_name or os.environ.get(
            "TABLE_NAME", "ConsumerRegulatoryAgent"
        )
        dynamodb = boto3.resource("dynamodb")
        self._table = dynamodb.Table(self._table_name)

    # ------------------------------------------------------------------
    # Key construction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _assessment_pk(assessment_id: str) -> str:
        return f"ASSESSMENT#{assessment_id}"

    @staticmethod
    def _conversation_pk(conversation_id: str) -> str:
        return f"CONVERSATION#{conversation_id}"

    @staticmethod
    def _user_pk(user_id: str) -> str:
        return f"USER#{user_id}"

    @staticmethod
    def _escalation_pk(matter_id: str) -> str:
        return f"ESCALATION#{matter_id}"

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _datetime_to_iso(dt: datetime) -> str:
        """Convert a datetime to ISO 8601 string for storage."""
        return dt.isoformat()

    @staticmethod
    def _serialize_risk_levels(risk_levels: dict[str, RiskLevel]) -> dict[str, str]:
        """Serialize RiskLevel dict to plain string values."""
        return {k: v.value for k, v in risk_levels.items()}

    # ------------------------------------------------------------------
    # Assessment access patterns
    # ------------------------------------------------------------------

    def put_assessment(self, result: AssessmentResult) -> None:
        """Store a completed assessment result.

        PK: ASSESSMENT#{assessmentId}
        SK: METADATA
        GSI1PK: USER#{userId}
        GSI1SK: ASSESSMENT#{timestamp}
        """
        timestamp_iso = self._datetime_to_iso(result.created_at)

        # Serialize risk_assessments list
        risk_assessments_data = []
        for ra in result.risk_assessments:
            concerns_data = []
            for c in ra.concerns:
                concern_item = {
                    "concern_id": c.concern_id,
                    "description": c.description,
                    "regulation_reference": c.regulation_reference,
                    "regulation_title": c.regulation_title,
                    "jurisdiction": c.jurisdiction,
                    "severity": c.severity,
                }
                if c.evidence_required:
                    concern_item["evidence_required"] = c.evidence_required
                concerns_data.append(concern_item)

            risk_assessments_data.append(
                {
                    "jurisdiction": ra.jurisdiction,
                    "risk_level": ra.risk_level.value,
                    "concerns": concerns_data,
                    "regulation_citations": ra.regulation_citations,
                    "recommended_actions": ra.recommended_actions,
                    "escalation_recommended": ra.escalation_recommended,
                }
            )

        item = {
            "PK": self._assessment_pk(result.assessment_id),
            "SK": "METADATA",
            "GSI1PK": self._user_pk(result.user_id),
            "GSI1SK": f"ASSESSMENT#{timestamp_iso}",
            "assessment_id": result.assessment_id,
            "query_id": result.query_id,
            "user_id": result.user_id,
            "assessment_type": result.assessment_type.value,
            "risk_assessments": risk_assessments_data,
            "disclaimer": result.disclaimer,
            "overall_risk": result.overall_risk.value,
            "created_at": timestamp_iso,
            "response_time_ms": result.response_time_ms,
            "model_id": result.model_id,
            "knowledge_base_version": result.knowledge_base_version,
        }

        self._table.put_item(Item=item)

    def get_assessment(self, assessment_id: str) -> Optional[dict]:
        """Retrieve an assessment by its ID.

        Returns None if the assessment does not exist.
        """
        response = self._table.get_item(
            Key={
                "PK": self._assessment_pk(assessment_id),
                "SK": "METADATA",
            }
        )
        return response.get("Item")

    def list_user_assessments(self, user_id: str, limit: int = 20) -> list[dict]:
        """List assessments for a user in reverse chronological order.

        Uses GSI1 with ScanIndexForward=False to return newest first.
        Requirement 8.3: Assessment history in reverse chronological order.
        """
        response = self._table.query(
            IndexName=self.GSI1_NAME,
            KeyConditionExpression=(
                Key("GSI1PK").eq(self._user_pk(user_id))
                & Key("GSI1SK").begins_with("ASSESSMENT#")
            ),
            ScanIndexForward=False,
            Limit=limit,
        )
        return response.get("Items", [])

    # ------------------------------------------------------------------
    # Audit record access patterns (IMMUTABLE - no update method)
    # ------------------------------------------------------------------

    def put_audit_record(self, record: AuditRecord) -> None:
        """Store an immutable audit record.

        PK: USER#{userId}
        SK: AUDIT#{timestamp}#{assessmentId}

        Requirement 8.1: Audit records are immutable — no update method exists.
        Requirement 8.4: TTL for 7-year retention.
        """
        timestamp_iso = self._datetime_to_iso(record.timestamp)

        item = {
            "PK": self._user_pk(record.user_id),
            "SK": f"AUDIT#{timestamp_iso}#{record.assessment_id}",
            "audit_id": record.audit_id,
            "user_id": record.user_id,
            "organisation_id": record.organisation_id,
            "assessment_id": record.assessment_id,
            "query_type": record.query_type.value,
            "jurisdictions": record.jurisdictions,
            "risk_levels": self._serialize_risk_levels(record.risk_levels),
            "response_time_ms": record.response_time_ms,
            "model_id": record.model_id,
            "timestamp": timestamp_iso,
            "ttl": record.ttl,
        }

        self._table.put_item(Item=item)

    # ------------------------------------------------------------------
    # Conversation access patterns
    # ------------------------------------------------------------------

    def put_conversation_message(
        self, conversation_id: str, message: dict
    ) -> None:
        """Store a conversation message.

        PK: CONVERSATION#{conversationId}
        SK: MSG#{timestamp}#{messageId}

        The message dict must contain at minimum:
        - message_id: str
        - timestamp: datetime or ISO string
        - content: str
        - sender: str
        """
        timestamp = message.get("timestamp")
        if isinstance(timestamp, datetime):
            timestamp_iso = self._datetime_to_iso(timestamp)
        else:
            timestamp_iso = str(timestamp)

        message_id = message["message_id"]

        item = {
            "PK": self._conversation_pk(conversation_id),
            "SK": f"MSG#{timestamp_iso}#{message_id}",
            "conversation_id": conversation_id,
            "message_id": message_id,
            "timestamp": timestamp_iso,
            "content": message["content"],
            "sender": message["sender"],
        }

        # Include optional GSI1 keys if user_id is provided
        if "user_id" in message:
            item["GSI1PK"] = self._user_pk(message["user_id"])
            item["GSI1SK"] = f"CONVERSATION#{timestamp_iso}"

        # Preserve any additional fields from the message
        for key, value in message.items():
            if key not in ("message_id", "timestamp", "content", "sender", "user_id"):
                if isinstance(value, datetime):
                    item[key] = self._datetime_to_iso(value)
                elif isinstance(value, Enum):
                    item[key] = value.value
                else:
                    item[key] = value

        self._table.put_item(Item=item)

    def get_conversation_messages(self, conversation_id: str) -> list[dict]:
        """Retrieve all messages for a conversation in chronological order.

        Uses ScanIndexForward=True for oldest-first ordering.
        Requirement 8.2: Conversation history in chronological order.
        """
        response = self._table.query(
            KeyConditionExpression=(
                Key("PK").eq(self._conversation_pk(conversation_id))
                & Key("SK").begins_with("MSG#")
            ),
            ScanIndexForward=True,
        )
        return response.get("Items", [])

    # ------------------------------------------------------------------
    # User preferences access patterns
    # ------------------------------------------------------------------

    def put_user_preferences(self, profile: UserProfile) -> None:
        """Store user preferences.

        PK: USER#{userId}
        SK: PREFERENCES
        """
        item = {
            "PK": self._user_pk(profile.user_id),
            "SK": "PREFERENCES",
            "user_id": profile.user_id,
            "organisation_id": profile.organisation_id,
            "email": profile.email,
            "role": profile.role,
            "permitted_jurisdictions": profile.permitted_jurisdictions,
            "sector": profile.sector,
            "notification_preferences": profile.notification_preferences,
            "monitoring_jurisdictions": profile.monitoring_jurisdictions,
        }

        self._table.put_item(Item=item)

    def get_user_preferences(self, user_id: str) -> Optional[dict]:
        """Retrieve user preferences by user ID.

        Returns None if no preferences exist for the user.
        """
        response = self._table.get_item(
            Key={
                "PK": self._user_pk(user_id),
                "SK": "PREFERENCES",
            }
        )
        return response.get("Item")
