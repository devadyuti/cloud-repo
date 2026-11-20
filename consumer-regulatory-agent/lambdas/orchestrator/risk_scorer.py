"""Risk scoring logic for compliance assessments.

Evaluates a list of ComplianceConcern objects and determines the overall
risk level for a given jurisdiction based on severity hierarchy.

Scoring rules:
- Critical if ANY concern has severity "critical"
- High if ANY concern has severity "high"
- Medium if ANY concern has severity "medium"
- Low otherwise (all concerns are "low" severity, or no concerns)

Requirements: 1.4
"""

from __future__ import annotations

from lambdas.shared.models import ComplianceConcern, RiskAssessment, RiskLevel


# Severity hierarchy from highest to lowest
_SEVERITY_TO_RISK: dict[str, RiskLevel] = {
    "critical": RiskLevel.CRITICAL,
    "high": RiskLevel.HIGH,
    "medium": RiskLevel.MEDIUM,
    "low": RiskLevel.LOW,
}

# Priority order for determining overall risk (highest first)
_SEVERITY_PRIORITY: list[str] = ["critical", "high", "medium", "low"]

# Recommended actions per risk level
_RECOMMENDED_ACTIONS: dict[RiskLevel, list[str]] = {
    RiskLevel.CRITICAL: [
        "Immediately halt campaign or activity pending legal review.",
        "Escalate to Consumer Markets legal team for urgent assessment.",
        "Document all compliance concerns for audit trail.",
    ],
    RiskLevel.HIGH: [
        "Escalate to Consumer Markets legal team for detailed review.",
        "Do not proceed without legal sign-off.",
        "Gather substantiation evidence for identified claims.",
    ],
    RiskLevel.MEDIUM: [
        "Review identified concerns with internal compliance team.",
        "Consider obtaining legal advice before proceeding.",
        "Address flagged issues and re-assess before launch.",
    ],
    RiskLevel.LOW: [
        "Proceed with standard compliance monitoring.",
        "Document assessment for audit trail.",
    ],
}


def score_risk(
    concerns: list[ComplianceConcern], jurisdiction: str
) -> RiskAssessment:
    """Score the overall risk level for a jurisdiction based on compliance concerns.

    Evaluates the severity of each concern and returns the highest applicable
    risk level. Validates that each concern has a non-empty regulation reference.

    Args:
        concerns: List of compliance concerns identified during analysis.
        jurisdiction: The jurisdiction being assessed (e.g., "UK", "EU", "US").

    Returns:
        A RiskAssessment containing the computed risk level, concerns,
        regulation citations, and recommended actions.

    Raises:
        ValueError: If any concern has an empty or whitespace-only
            regulation_reference.
    """
    # Validate regulation references
    for concern in concerns:
        if not concern.regulation_reference or not concern.regulation_reference.strip():
            raise ValueError(
                f"ComplianceConcern '{concern.concern_id}' is missing a "
                f"regulation_reference. Each concern must cite at least one regulation."
            )

    # Determine overall risk level based on highest severity present
    risk_level = RiskLevel.LOW
    for severity in _SEVERITY_PRIORITY:
        if any(c.severity == severity for c in concerns):
            risk_level = _SEVERITY_TO_RISK[severity]
            break

    # Collect unique regulation citations from all concerns
    regulation_citations = list(
        dict.fromkeys(c.regulation_reference for c in concerns)
    )

    # Determine recommended actions based on risk level
    recommended_actions = _RECOMMENDED_ACTIONS[risk_level]

    # Escalation is recommended for High or Critical risk
    escalation_recommended = risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    return RiskAssessment(
        jurisdiction=jurisdiction,
        risk_level=risk_level,
        concerns=concerns,
        regulation_citations=regulation_citations,
        recommended_actions=recommended_actions,
        escalation_recommended=escalation_recommended,
    )
