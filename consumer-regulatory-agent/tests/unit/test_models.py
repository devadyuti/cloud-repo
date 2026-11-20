"""Unit tests for the core data models.

Verifies that all dataclasses, enums, and model relationships are correctly
defined and behave as expected.
"""

from datetime import datetime, timezone
from typing import Optional

import pytest

from lambdas.shared.models import (
    AssessmentResult,
    AssessmentType,
    AuditRecord,
    ChecklistItem,
    ChecklistResult,
    ComplianceConcern,
    ComplianceQuery,
    EscalationBrief,
    MatterIntakeResult,
    RegulatoryUpdate,
    RiskAssessment,
    RiskLevel,
    UrgencyLevel,
    UserProfile,
)


class TestRiskLevelEnum:
    """Tests for the RiskLevel enum."""

    def test_values(self):
        assert RiskLevel.LOW.value == "Low"
        assert RiskLevel.MEDIUM.value == "Medium"
        assert RiskLevel.HIGH.value == "High"
        assert RiskLevel.CRITICAL.value == "Critical"

    def test_all_members(self):
        assert len(RiskLevel) == 4

    def test_from_value(self):
        assert RiskLevel("Low") == RiskLevel.LOW
        assert RiskLevel("Critical") == RiskLevel.CRITICAL

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            RiskLevel("Invalid")


class TestUrgencyLevelEnum:
    """Tests for the UrgencyLevel enum."""

    def test_values(self):
        assert UrgencyLevel.IMMEDIATE_ACTION.value == "Immediate Action Required"
        assert UrgencyLevel.UPCOMING_DEADLINE.value == "Upcoming Deadline"
        assert UrgencyLevel.AWARENESS_ONLY.value == "Awareness Only"

    def test_all_members(self):
        assert len(UrgencyLevel) == 3


class TestAssessmentTypeEnum:
    """Tests for the AssessmentType enum."""

    def test_values(self):
        assert AssessmentType.CAMPAIGN_COMPLIANCE.value == "campaign_compliance"
        assert AssessmentType.PRODUCT_CHECKLIST.value == "product_checklist"
        assert AssessmentType.DATA_COMPLIANCE.value == "data_compliance"

    def test_all_members(self):
        assert len(AssessmentType) == 3


class TestComplianceQuery:
    """Tests for the ComplianceQuery dataclass."""

    def test_required_fields(self):
        query = ComplianceQuery(
            query_id="q-001",
            user_id="user-123",
            organisation_id="org-456",
            assessment_type=AssessmentType.CAMPAIGN_COMPLIANCE,
            content="Buy our product, it's 50% better than Brand X!",
            jurisdictions=["UK", "EU"],
        )
        assert query.query_id == "q-001"
        assert query.user_id == "user-123"
        assert query.organisation_id == "org-456"
        assert query.assessment_type == AssessmentType.CAMPAIGN_COMPLIANCE
        assert query.content == "Buy our product, it's 50% better than Brand X!"
        assert query.jurisdictions == ["UK", "EU"]

    def test_optional_fields_default_to_none(self):
        query = ComplianceQuery(
            query_id="q-001",
            user_id="user-123",
            organisation_id="org-456",
            assessment_type=AssessmentType.CAMPAIGN_COMPLIANCE,
            content="Some content",
            jurisdictions=["UK"],
        )
        assert query.product_category is None
        assert query.target_demographics is None
        assert query.created_at is None

    def test_optional_fields_set(self):
        now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        query = ComplianceQuery(
            query_id="q-001",
            user_id="user-123",
            organisation_id="org-456",
            assessment_type=AssessmentType.PRODUCT_CHECKLIST,
            content="Organic face cream",
            jurisdictions=["UK", "EU", "US"],
            product_category="cosmetics",
            target_demographics=["general_adult"],
            created_at=now,
        )
        assert query.product_category == "cosmetics"
        assert query.target_demographics == ["general_adult"]
        assert query.created_at == now


class TestComplianceConcern:
    """Tests for the ComplianceConcern dataclass."""

    def test_required_fields(self):
        concern = ComplianceConcern(
            concern_id="c-001",
            description="Comparative claim requires substantiation",
            regulation_reference="CAP Code 3.33",
            regulation_title="Substantiation of comparative claims",
            jurisdiction="UK",
            severity="high",
        )
        assert concern.concern_id == "c-001"
        assert concern.jurisdiction == "UK"
        assert concern.severity == "high"
        assert concern.evidence_required is None

    def test_with_evidence_required(self):
        concern = ComplianceConcern(
            concern_id="c-002",
            description="Claim needs proof",
            regulation_reference="FTC Act s.5",
            regulation_title="Unfair or deceptive acts",
            jurisdiction="US",
            severity="medium",
            evidence_required="Independent lab testing results",
        )
        assert concern.evidence_required == "Independent lab testing results"


class TestRiskAssessment:
    """Tests for the RiskAssessment dataclass."""

    def test_construction(self):
        assessment = RiskAssessment(
            jurisdiction="UK",
            risk_level=RiskLevel.HIGH,
            concerns=[],
            regulation_citations=["CAP Code 3.33"],
            recommended_actions=["Obtain evidence"],
            escalation_recommended=True,
        )
        assert assessment.jurisdiction == "UK"
        assert assessment.risk_level == RiskLevel.HIGH
        assert assessment.escalation_recommended is True

    def test_with_multiple_concerns(self):
        concerns = [
            ComplianceConcern(
                concern_id=f"c-{i}",
                description=f"Concern {i}",
                regulation_reference=f"Reg {i}",
                regulation_title=f"Title {i}",
                jurisdiction="EU",
                severity="medium",
            )
            for i in range(3)
        ]
        assessment = RiskAssessment(
            jurisdiction="EU",
            risk_level=RiskLevel.MEDIUM,
            concerns=concerns,
            regulation_citations=["Reg 0", "Reg 1", "Reg 2"],
            recommended_actions=["Action 1", "Action 2"],
            escalation_recommended=False,
        )
        assert len(assessment.concerns) == 3
        assert len(assessment.regulation_citations) == 3


class TestAssessmentResult:
    """Tests for the AssessmentResult dataclass."""

    def test_construction(self):
        now = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = AssessmentResult(
            assessment_id="assess-001",
            query_id="q-001",
            user_id="user-123",
            assessment_type=AssessmentType.CAMPAIGN_COMPLIANCE,
            risk_assessments=[],
            disclaimer="DISCLAIMER: Preliminary assessment only.",
            overall_risk=RiskLevel.LOW,
            created_at=now,
            response_time_ms=2500,
            model_id="anthropic.claude-v3",
            knowledge_base_version="v1.0",
        )
        assert result.assessment_id == "assess-001"
        assert result.overall_risk == RiskLevel.LOW
        assert result.response_time_ms == 2500


class TestChecklistItem:
    """Tests for the ChecklistItem dataclass."""

    def test_required_fields(self):
        item = ChecklistItem(
            item_id="item-001",
            requirement_description="Product must display allergen warnings",
            source_regulation="EU Regulation 1169/2011",
            jurisdiction="EU",
            compliance_action="Add allergen labelling to packaging",
            sector_specific=True,
        )
        assert item.item_id == "item-001"
        assert item.sector_specific is True
        assert item.conflicts_with is None

    def test_with_conflicts(self):
        item = ChecklistItem(
            item_id="item-002",
            requirement_description="Display origin country",
            source_regulation="UK Food Regs 2019",
            jurisdiction="UK",
            compliance_action="Add country of origin label",
            sector_specific=True,
            conflicts_with=["EU Regulation 1169/2011 Art.26"],
        )
        assert item.conflicts_with == ["EU Regulation 1169/2011 Art.26"]


class TestChecklistResult:
    """Tests for the ChecklistResult dataclass."""

    def test_construction(self):
        now = datetime(2025, 2, 1, 9, 0, 0, tzinfo=timezone.utc)
        result = ChecklistResult(
            checklist_id="cl-001",
            query_id="q-002",
            product_category="cosmetics",
            jurisdictions=["UK", "EU"],
            items=[],
            cross_jurisdiction_conflicts=[],
            disclaimer="DISCLAIMER: Preliminary assessment.",
            created_at=now,
        )
        assert result.checklist_id == "cl-001"
        assert result.product_category == "cosmetics"
        assert result.jurisdictions == ["UK", "EU"]


class TestEscalationBrief:
    """Tests for the EscalationBrief dataclass."""

    def test_construction(self):
        now = datetime(2025, 1, 15, 11, 0, 0, tzinfo=timezone.utc)
        query = ComplianceQuery(
            query_id="q-001",
            user_id="user-123",
            organisation_id="org-456",
            assessment_type=AssessmentType.CAMPAIGN_COMPLIANCE,
            content="Test content",
            jurisdictions=["UK"],
        )
        assessment = AssessmentResult(
            assessment_id="assess-001",
            query_id="q-001",
            user_id="user-123",
            assessment_type=AssessmentType.CAMPAIGN_COMPLIANCE,
            risk_assessments=[],
            disclaimer="DISCLAIMER",
            overall_risk=RiskLevel.HIGH,
            created_at=now,
            response_time_ms=3000,
            model_id="anthropic.claude-v3",
            knowledge_base_version="v1.0",
        )
        brief = EscalationBrief(
            brief_id="brief-001",
            assessment_id="assess-001",
            original_query=query,
            ai_analysis=assessment,
            regulation_references=["CAP Code 3.33"],
            risk_summary="High risk due to unsubstantiated comparative claims",
            audit_trail=[{"action": "assessment_created", "timestamp": now.isoformat()}],
            created_at=now,
        )
        assert brief.brief_id == "brief-001"
        assert brief.original_query.query_id == "q-001"
        assert brief.ai_analysis.overall_risk == RiskLevel.HIGH
        assert len(brief.audit_trail) == 1


class TestMatterIntakeResult:
    """Tests for the MatterIntakeResult dataclass."""

    def test_success(self):
        result = MatterIntakeResult(
            matter_reference="MAT-2025-001",
            status="created",
            expected_response_timeline="Within 2 business days",
        )
        assert result.matter_reference == "MAT-2025-001"
        assert result.status == "created"
        assert result.error_message is None

    def test_failure(self):
        result = MatterIntakeResult(
            matter_reference="",
            status="failed",
            expected_response_timeline="",
            error_message="Practice management system unavailable",
        )
        assert result.status == "failed"
        assert result.error_message == "Practice management system unavailable"


class TestUserProfile:
    """Tests for the UserProfile dataclass."""

    def test_construction(self):
        profile = UserProfile(
            user_id="user-123",
            organisation_id="org-456",
            email="user@example.com",
            role="compliance_officer",
            permitted_jurisdictions=["UK", "EU"],
            sector="cosmetics",
            notification_preferences={"email": True, "sms": False},
            monitoring_jurisdictions=["UK"],
        )
        assert profile.user_id == "user-123"
        assert profile.permitted_jurisdictions == ["UK", "EU"]
        assert profile.notification_preferences == {"email": True, "sms": False}


class TestRegulatoryUpdate:
    """Tests for the RegulatoryUpdate dataclass."""

    def test_with_deadline(self):
        detected = datetime(2025, 3, 1, 8, 0, 0, tzinfo=timezone.utc)
        deadline = datetime(2025, 4, 15, 0, 0, 0, tzinfo=timezone.utc)
        update = RegulatoryUpdate(
            update_id="upd-001",
            jurisdiction="UK",
            document_title="CMA Guidance Update",
            change_summary="New requirements for subscription traps",
            effective_date=datetime(2025, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
            compliance_deadline=deadline,
            urgency=UrgencyLevel.UPCOMING_DEADLINE,
            affected_sectors=["digital", "leisure"],
            source_url="https://www.gov.uk/cma-cases/example",
            detected_at=detected,
        )
        assert update.urgency == UrgencyLevel.UPCOMING_DEADLINE
        assert update.compliance_deadline == deadline

    def test_without_deadline(self):
        detected = datetime(2025, 3, 1, 8, 0, 0, tzinfo=timezone.utc)
        update = RegulatoryUpdate(
            update_id="upd-002",
            jurisdiction="EU",
            document_title="DSA Guidance Note",
            change_summary="Clarification on platform obligations",
            effective_date=None,
            compliance_deadline=None,
            urgency=UrgencyLevel.AWARENESS_ONLY,
            affected_sectors=["digital"],
            source_url="https://eur-lex.europa.eu/example",
            detected_at=detected,
        )
        assert update.effective_date is None
        assert update.compliance_deadline is None
        assert update.urgency == UrgencyLevel.AWARENESS_ONLY


class TestAuditRecord:
    """Tests for the AuditRecord dataclass."""

    def test_construction(self):
        now = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        record = AuditRecord(
            audit_id="audit-001",
            user_id="user-123",
            organisation_id="org-456",
            assessment_id="assess-001",
            query_type=AssessmentType.CAMPAIGN_COMPLIANCE,
            jurisdictions=["UK", "EU"],
            risk_levels={"UK": RiskLevel.HIGH, "EU": RiskLevel.MEDIUM},
            response_time_ms=4200,
            model_id="anthropic.claude-v3",
            timestamp=now,
            ttl=1768435800,
        )
        assert record.audit_id == "audit-001"
        assert record.risk_levels["UK"] == RiskLevel.HIGH
        assert record.ttl == 1768435800

    def test_risk_levels_dict_with_all_levels(self):
        now = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        record = AuditRecord(
            audit_id="audit-002",
            user_id="user-123",
            organisation_id="org-456",
            assessment_id="assess-002",
            query_type=AssessmentType.PRODUCT_CHECKLIST,
            jurisdictions=["UK", "EU", "US"],
            risk_levels={
                "UK": RiskLevel.LOW,
                "EU": RiskLevel.MEDIUM,
                "US": RiskLevel.CRITICAL,
            },
            response_time_ms=5000,
            model_id="anthropic.claude-v3",
            timestamp=now,
            ttl=1768435800,
        )
        assert len(record.risk_levels) == 3
        assert record.risk_levels["US"] == RiskLevel.CRITICAL
