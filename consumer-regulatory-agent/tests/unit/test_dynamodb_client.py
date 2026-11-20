"""Unit tests for the DynamoDB data access layer.

Uses moto to mock DynamoDB and verify all access patterns work correctly.
"""

import os
from datetime import datetime, timezone

import boto3
import pytest
from moto import mock_aws

from lambdas.shared.dynamodb_client import DynamoDBClient
from lambdas.shared.models import (
    AssessmentResult,
    AssessmentType,
    AuditRecord,
    ComplianceConcern,
    RiskAssessment,
    RiskLevel,
    UserProfile,
)

TABLE_NAME = "TestConsumerRegulatoryAgent"


@pytest.fixture
def dynamodb_table():
    """Create a mocked DynamoDB table with GSI1."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.meta.client.get_waiter("table_exists").wait(TableName=TABLE_NAME)
        yield table


@pytest.fixture
def client(dynamodb_table):
    """Create a DynamoDBClient pointing at the mocked table."""
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    return DynamoDBClient(table_name=TABLE_NAME)


def _make_assessment_result(
    assessment_id: str = "assess-001",
    user_id: str = "user-123",
    created_at: datetime | None = None,
) -> AssessmentResult:
    """Helper to create a sample AssessmentResult."""
    if created_at is None:
        created_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    return AssessmentResult(
        assessment_id=assessment_id,
        query_id="query-001",
        user_id=user_id,
        assessment_type=AssessmentType.CAMPAIGN_COMPLIANCE,
        risk_assessments=[
            RiskAssessment(
                jurisdiction="UK",
                risk_level=RiskLevel.HIGH,
                concerns=[
                    ComplianceConcern(
                        concern_id="concern-001",
                        description="Comparative claim requires substantiation",
                        regulation_reference="CAP Code 3.33",
                        regulation_title="Substantiation of comparative claims",
                        jurisdiction="UK",
                        severity="high",
                        evidence_required="Independent testing data",
                    )
                ],
                regulation_citations=["CAP Code 3.33", "CRA 2015 s.12"],
                recommended_actions=["Obtain substantiation evidence"],
                escalation_recommended=True,
            )
        ],
        disclaimer="DISCLAIMER: This is a preliminary assessment...",
        overall_risk=RiskLevel.HIGH,
        created_at=created_at,
        response_time_ms=4200,
        model_id="anthropic.claude-v3",
        knowledge_base_version="v1.0",
    )


def _make_audit_record(
    user_id: str = "user-123",
    assessment_id: str = "assess-001",
    timestamp: datetime | None = None,
) -> AuditRecord:
    """Helper to create a sample AuditRecord."""
    if timestamp is None:
        timestamp = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    return AuditRecord(
        audit_id="audit-001",
        user_id=user_id,
        organisation_id="org-456",
        assessment_id=assessment_id,
        query_type=AssessmentType.CAMPAIGN_COMPLIANCE,
        jurisdictions=["UK", "EU"],
        risk_levels={"UK": RiskLevel.HIGH, "EU": RiskLevel.MEDIUM},
        response_time_ms=4200,
        model_id="anthropic.claude-v3",
        timestamp=timestamp,
        ttl=1768435800,  # ~7 years from 2025
    )


def _make_user_profile(user_id: str = "user-123") -> UserProfile:
    """Helper to create a sample UserProfile."""
    return UserProfile(
        user_id=user_id,
        organisation_id="org-456",
        email="user@example.com",
        role="compliance_officer",
        permitted_jurisdictions=["UK", "EU"],
        sector="cosmetics",
        notification_preferences={"email": True, "sms": False},
        monitoring_jurisdictions=["UK"],
    )


class TestKeyConstruction:
    """Test key construction helper methods."""

    def test_assessment_pk(self):
        assert DynamoDBClient._assessment_pk("abc") == "ASSESSMENT#abc"

    def test_conversation_pk(self):
        assert DynamoDBClient._conversation_pk("conv-1") == "CONVERSATION#conv-1"

    def test_user_pk(self):
        assert DynamoDBClient._user_pk("user-1") == "USER#user-1"

    def test_escalation_pk(self):
        assert DynamoDBClient._escalation_pk("matter-1") == "ESCALATION#matter-1"


class TestAssessmentAccessPatterns:
    """Test assessment put/get/list operations."""

    def test_put_and_get_assessment(self, client, dynamodb_table):
        result = _make_assessment_result()
        client.put_assessment(result)

        item = client.get_assessment("assess-001")
        assert item is not None
        assert item["assessment_id"] == "assess-001"
        assert item["user_id"] == "user-123"
        assert item["overall_risk"] == "High"
        assert item["assessment_type"] == "campaign_compliance"
        assert item["PK"] == "ASSESSMENT#assess-001"
        assert item["SK"] == "METADATA"

    def test_get_nonexistent_assessment(self, client, dynamodb_table):
        item = client.get_assessment("nonexistent")
        assert item is None

    def test_list_user_assessments_reverse_chronological(self, client, dynamodb_table):
        # Create assessments at different times
        for i, hour in enumerate([8, 10, 12]):
            result = _make_assessment_result(
                assessment_id=f"assess-{i:03d}",
                created_at=datetime(2025, 1, 15, hour, 0, 0, tzinfo=timezone.utc),
            )
            client.put_assessment(result)

        items = client.list_user_assessments("user-123")
        assert len(items) == 3
        # Newest first (hour 12, 10, 8)
        assert items[0]["assessment_id"] == "assess-002"
        assert items[1]["assessment_id"] == "assess-001"
        assert items[2]["assessment_id"] == "assess-000"

    def test_list_user_assessments_with_limit(self, client, dynamodb_table):
        for i in range(5):
            result = _make_assessment_result(
                assessment_id=f"assess-{i:03d}",
                created_at=datetime(2025, 1, 15, i, 0, 0, tzinfo=timezone.utc),
            )
            client.put_assessment(result)

        items = client.list_user_assessments("user-123", limit=2)
        assert len(items) == 2

    def test_list_user_assessments_empty(self, client, dynamodb_table):
        items = client.list_user_assessments("nonexistent-user")
        assert items == []


class TestAuditRecordAccessPatterns:
    """Test audit record put operation (no update method)."""

    def test_put_audit_record(self, client, dynamodb_table):
        record = _make_audit_record()
        client.put_audit_record(record)

        # Verify directly via table scan
        response = dynamodb_table.scan()
        items = [
            i for i in response["Items"] if i["PK"] == "USER#user-123" and "AUDIT#" in i["SK"]
        ]
        assert len(items) == 1
        item = items[0]
        assert item["audit_id"] == "audit-001"
        assert item["risk_levels"] == {"UK": "High", "EU": "Medium"}
        assert item["query_type"] == "campaign_compliance"
        assert item["ttl"] == 1768435800

    def test_no_update_audit_method(self):
        """Verify that no update method exists for audit records (immutability)."""
        assert not hasattr(DynamoDBClient, "update_audit_record")


class TestConversationAccessPatterns:
    """Test conversation message put/get operations."""

    def test_put_and_get_messages_chronological(self, client, dynamodb_table):
        conv_id = "conv-001"
        messages = [
            {
                "message_id": "msg-001",
                "timestamp": datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                "content": "First message",
                "sender": "user",
            },
            {
                "message_id": "msg-002",
                "timestamp": datetime(2025, 1, 15, 10, 5, 0, tzinfo=timezone.utc),
                "content": "Second message",
                "sender": "agent",
            },
            {
                "message_id": "msg-003",
                "timestamp": datetime(2025, 1, 15, 10, 10, 0, tzinfo=timezone.utc),
                "content": "Third message",
                "sender": "user",
            },
        ]

        # Insert in random order
        for msg in [messages[2], messages[0], messages[1]]:
            client.put_conversation_message(conv_id, msg)

        # Retrieve — should be chronological
        result = client.get_conversation_messages(conv_id)
        assert len(result) == 3
        assert result[0]["content"] == "First message"
        assert result[1]["content"] == "Second message"
        assert result[2]["content"] == "Third message"

    def test_get_empty_conversation(self, client, dynamodb_table):
        result = client.get_conversation_messages("nonexistent-conv")
        assert result == []

    def test_message_with_user_id_sets_gsi1(self, client, dynamodb_table):
        msg = {
            "message_id": "msg-001",
            "timestamp": datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            "content": "Hello",
            "sender": "user",
            "user_id": "user-123",
        }
        client.put_conversation_message("conv-001", msg)

        response = dynamodb_table.scan()
        items = [i for i in response["Items"] if i.get("message_id") == "msg-001"]
        assert len(items) == 1
        assert items[0]["GSI1PK"] == "USER#user-123"
        assert "CONVERSATION#" in items[0]["GSI1SK"]


class TestUserPreferencesAccessPatterns:
    """Test user preferences put/get operations."""

    def test_put_and_get_preferences(self, client, dynamodb_table):
        profile = _make_user_profile()
        client.put_user_preferences(profile)

        item = client.get_user_preferences("user-123")
        assert item is not None
        assert item["user_id"] == "user-123"
        assert item["email"] == "user@example.com"
        assert item["sector"] == "cosmetics"
        assert item["permitted_jurisdictions"] == ["UK", "EU"]
        assert item["notification_preferences"] == {"email": True, "sms": False}

    def test_get_nonexistent_preferences(self, client, dynamodb_table):
        item = client.get_user_preferences("nonexistent-user")
        assert item is None

    def test_preferences_overwrite(self, client, dynamodb_table):
        """Putting preferences again overwrites the previous record."""
        profile = _make_user_profile()
        client.put_user_preferences(profile)

        # Update sector
        profile.sector = "electronics"
        client.put_user_preferences(profile)

        item = client.get_user_preferences("user-123")
        assert item["sector"] == "electronics"
