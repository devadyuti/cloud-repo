"""Core data models for the Consumer Regulatory Protection Agent.

Implements all dataclasses and enums used across the system for compliance
assessments, checklists, escalations, monitoring, and audit records.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RiskLevel(Enum):
    """Risk severity levels for compliance assessments."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class UrgencyLevel(Enum):
    """Urgency categorisation for regulatory updates."""

    IMMEDIATE_ACTION = "Immediate Action Required"
    UPCOMING_DEADLINE = "Upcoming Deadline"
    AWARENESS_ONLY = "Awareness Only"


class AssessmentType(Enum):
    """Types of compliance assessments supported."""

    CAMPAIGN_COMPLIANCE = "campaign_compliance"
    PRODUCT_CHECKLIST = "product_checklist"
    DATA_COMPLIANCE = "data_compliance"


@dataclass
class ComplianceQuery:
    """Represents a user's compliance assessment request."""

    query_id: str
    user_id: str
    organisation_id: str
    assessment_type: AssessmentType
    content: str  # Campaign copy, product description, or data collection description
    jurisdictions: list[str]
    product_category: Optional[str] = None
    target_demographics: Optional[list[str]] = field(default=None)
    created_at: Optional[datetime] = field(default=None)


@dataclass
class ComplianceConcern:
    """A specific compliance concern identified during assessment."""

    concern_id: str
    description: str
    regulation_reference: str
    regulation_title: str
    jurisdiction: str
    severity: str  # "low", "medium", "high", "critical"
    evidence_required: Optional[str] = None


@dataclass
class RiskAssessment:
    """Risk assessment for a single jurisdiction."""

    jurisdiction: str
    risk_level: RiskLevel
    concerns: list[ComplianceConcern]
    regulation_citations: list[str]
    recommended_actions: list[str]
    escalation_recommended: bool


@dataclass
class AssessmentResult:
    """Complete result of a compliance assessment."""

    assessment_id: str
    query_id: str
    user_id: str
    assessment_type: AssessmentType
    risk_assessments: list[RiskAssessment]
    disclaimer: str
    overall_risk: RiskLevel
    created_at: datetime
    response_time_ms: int
    model_id: str
    knowledge_base_version: str


@dataclass
class ChecklistItem:
    """A single item in a product compliance checklist."""

    item_id: str
    requirement_description: str
    source_regulation: str
    jurisdiction: str
    compliance_action: str
    sector_specific: bool
    conflicts_with: Optional[list[str]] = field(default=None)


@dataclass
class ChecklistResult:
    """Complete result of a product compliance checklist generation."""

    checklist_id: str
    query_id: str
    product_category: str
    jurisdictions: list[str]
    items: list[ChecklistItem]
    cross_jurisdiction_conflicts: list[str]
    disclaimer: str
    created_at: datetime


@dataclass
class EscalationBrief:
    """Brief assembled for escalation to human lawyers."""

    brief_id: str
    assessment_id: str
    original_query: ComplianceQuery
    ai_analysis: AssessmentResult
    regulation_references: list[str]
    risk_summary: str
    audit_trail: list[dict]
    created_at: datetime


@dataclass
class MatterIntakeResult:
    """Result of creating a matter intake in the practice management system."""

    matter_reference: str
    status: str  # "created", "failed"
    expected_response_timeline: str
    error_message: Optional[str] = None


@dataclass
class UserProfile:
    """User profile with organisation context and preferences."""

    user_id: str
    organisation_id: str
    email: str
    role: str
    permitted_jurisdictions: list[str]
    sector: str
    notification_preferences: dict
    monitoring_jurisdictions: list[str]


@dataclass
class RegulatoryUpdate:
    """A detected regulatory change requiring user notification."""

    update_id: str
    jurisdiction: str
    document_title: str
    change_summary: str
    effective_date: Optional[datetime]
    compliance_deadline: Optional[datetime]
    urgency: UrgencyLevel
    affected_sectors: list[str]
    source_url: str
    detected_at: datetime


@dataclass
class AuditRecord:
    """Immutable audit record for compliance assessment traceability."""

    audit_id: str
    user_id: str
    organisation_id: str
    assessment_id: str
    query_type: AssessmentType
    jurisdictions: list[str]
    risk_levels: dict[str, RiskLevel]
    response_time_ms: int
    model_id: str
    timestamp: datetime
    ttl: int  # 7 years in epoch seconds
