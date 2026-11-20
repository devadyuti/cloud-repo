"""Unit tests for the risk scoring logic.

Verifies that the score_risk function correctly determines risk levels
based on concern severities and validates regulation references.

Requirements: 1.4
"""

import pytest

from lambdas.orchestrator.risk_scorer import score_risk
from lambdas.shared.models import ComplianceConcern, RiskAssessment, RiskLevel


def _make_concern(
    severity: str,
    concern_id: str = "c-001",
    regulation_reference: str = "CAP Code 3.33",
    jurisdiction: str = "UK",
) -> ComplianceConcern:
    """Helper to create a ComplianceConcern with minimal boilerplate."""
    return ComplianceConcern(
        concern_id=concern_id,
        description=f"Test concern with {severity} severity",
        regulation_reference=regulation_reference,
        regulation_title=f"Test regulation ({severity})",
        jurisdiction=jurisdiction,
        severity=severity,
    )


class TestScoreRiskBasicScoring:
    """Tests for basic risk level determination."""

    def test_no_concerns_returns_low(self):
        result = score_risk([], "UK")
        assert result.risk_level == RiskLevel.LOW
        assert result.jurisdiction == "UK"
        assert result.concerns == []
        assert result.regulation_citations == []

    def test_single_low_concern_returns_low(self):
        concerns = [_make_concern("low")]
        result = score_risk(concerns, "UK")
        assert result.risk_level == RiskLevel.LOW

    def test_single_medium_concern_returns_medium(self):
        concerns = [_make_concern("medium")]
        result = score_risk(concerns, "EU")
        assert result.risk_level == RiskLevel.MEDIUM

    def test_single_high_concern_returns_high(self):
        concerns = [_make_concern("high")]
        result = score_risk(concerns, "US")
        assert result.risk_level == RiskLevel.HIGH

    def test_single_critical_concern_returns_critical(self):
        concerns = [_make_concern("critical")]
        result = score_risk(concerns, "UK")
        assert result.risk_level == RiskLevel.CRITICAL


class TestScoreRiskSeverityHierarchy:
    """Tests for severity hierarchy (highest wins)."""

    def test_mixed_low_and_medium_returns_medium(self):
        concerns = [
            _make_concern("low", concern_id="c-001"),
            _make_concern("medium", concern_id="c-002"),
        ]
        result = score_risk(concerns, "UK")
        assert result.risk_level == RiskLevel.MEDIUM

    def test_mixed_low_medium_high_returns_high(self):
        concerns = [
            _make_concern("low", concern_id="c-001"),
            _make_concern("medium", concern_id="c-002"),
            _make_concern("high", concern_id="c-003"),
        ]
        result = score_risk(concerns, "EU")
        assert result.risk_level == RiskLevel.HIGH

    def test_any_critical_overrides_all(self):
        concerns = [
            _make_concern("low", concern_id="c-001"),
            _make_concern("medium", concern_id="c-002"),
            _make_concern("high", concern_id="c-003"),
            _make_concern("critical", concern_id="c-004"),
        ]
        result = score_risk(concerns, "US")
        assert result.risk_level == RiskLevel.CRITICAL

    def test_multiple_same_severity(self):
        concerns = [
            _make_concern("high", concern_id="c-001", regulation_reference="Reg A"),
            _make_concern("high", concern_id="c-002", regulation_reference="Reg B"),
        ]
        result = score_risk(concerns, "UK")
        assert result.risk_level == RiskLevel.HIGH


class TestScoreRiskRegulationCitations:
    """Tests for regulation citation collection."""

    def test_citations_collected_from_all_concerns(self):
        concerns = [
            _make_concern("low", concern_id="c-001", regulation_reference="CAP Code 3.33"),
            _make_concern("medium", concern_id="c-002", regulation_reference="FTC Act s.5"),
        ]
        result = score_risk(concerns, "UK")
        assert "CAP Code 3.33" in result.regulation_citations
        assert "FTC Act s.5" in result.regulation_citations

    def test_duplicate_citations_deduplicated(self):
        concerns = [
            _make_concern("low", concern_id="c-001", regulation_reference="CAP Code 3.33"),
            _make_concern("medium", concern_id="c-002", regulation_reference="CAP Code 3.33"),
        ]
        result = score_risk(concerns, "UK")
        assert result.regulation_citations == ["CAP Code 3.33"]

    def test_citation_order_preserved(self):
        concerns = [
            _make_concern("low", concern_id="c-001", regulation_reference="Reg A"),
            _make_concern("low", concern_id="c-002", regulation_reference="Reg B"),
            _make_concern("low", concern_id="c-003", regulation_reference="Reg C"),
        ]
        result = score_risk(concerns, "UK")
        assert result.regulation_citations == ["Reg A", "Reg B", "Reg C"]


class TestScoreRiskValidation:
    """Tests for regulation reference validation."""

    def test_empty_regulation_reference_raises_value_error(self):
        concerns = [_make_concern("low", regulation_reference="")]
        with pytest.raises(ValueError, match="missing a regulation_reference"):
            score_risk(concerns, "UK")

    def test_whitespace_only_regulation_reference_raises_value_error(self):
        concerns = [_make_concern("medium", regulation_reference="   ")]
        with pytest.raises(ValueError, match="missing a regulation_reference"):
            score_risk(concerns, "UK")

    def test_valid_regulation_reference_does_not_raise(self):
        concerns = [_make_concern("high", regulation_reference="CAP Code 3.33")]
        result = score_risk(concerns, "UK")
        assert result.risk_level == RiskLevel.HIGH


class TestScoreRiskOutputStructure:
    """Tests for the RiskAssessment output structure."""

    def test_returns_risk_assessment_dataclass(self):
        result = score_risk([], "UK")
        assert isinstance(result, RiskAssessment)

    def test_jurisdiction_passed_through(self):
        result = score_risk([], "AU")
        assert result.jurisdiction == "AU"

    def test_concerns_list_passed_through(self):
        concerns = [
            _make_concern("low", concern_id="c-001"),
            _make_concern("high", concern_id="c-002"),
        ]
        result = score_risk(concerns, "UK")
        assert result.concerns == concerns
        assert len(result.concerns) == 2

    def test_recommended_actions_non_empty(self):
        result = score_risk([], "UK")
        assert len(result.recommended_actions) > 0

    def test_escalation_recommended_for_high(self):
        concerns = [_make_concern("high")]
        result = score_risk(concerns, "UK")
        assert result.escalation_recommended is True

    def test_escalation_recommended_for_critical(self):
        concerns = [_make_concern("critical")]
        result = score_risk(concerns, "UK")
        assert result.escalation_recommended is True

    def test_escalation_not_recommended_for_medium(self):
        concerns = [_make_concern("medium")]
        result = score_risk(concerns, "UK")
        assert result.escalation_recommended is False

    def test_escalation_not_recommended_for_low(self):
        concerns = [_make_concern("low")]
        result = score_risk(concerns, "UK")
        assert result.escalation_recommended is False

    def test_escalation_not_recommended_for_no_concerns(self):
        result = score_risk([], "UK")
        assert result.escalation_recommended is False
