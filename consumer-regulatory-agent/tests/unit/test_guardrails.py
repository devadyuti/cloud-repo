"""Unit tests for the guardrails integration module.

Verifies legal disclaimer injection, definitive phrase blocking,
citation validation, and fail-closed behavior.

Requirements: 7.1, 7.2, 7.3, 7.4
"""

from unittest.mock import MagicMock, patch

import pytest

from lambdas.orchestrator.guardrails import (
    CITATION_GAP_MESSAGE,
    LEGAL_DISCLAIMER,
    GuardrailResult,
    apply_guardrails,
    block_definitive_conclusions,
    inject_disclaimer,
    validate_citations,
)


# ---------------------------------------------------------------------------
# Tests for inject_disclaimer
# ---------------------------------------------------------------------------


class TestInjectDisclaimer:
    """Tests for the inject_disclaimer helper function."""

    def test_disclaimer_prepended_to_response(self):
        text = "The regulation requires labelling."
        result = inject_disclaimer(text)
        assert result.startswith(LEGAL_DISCLAIMER)
        assert text in result

    def test_disclaimer_separated_by_double_newline(self):
        text = "Some analysis."
        result = inject_disclaimer(text)
        assert result == f"{LEGAL_DISCLAIMER}\n\n{text}"

    def test_disclaimer_on_empty_text(self):
        result = inject_disclaimer("")
        assert result == f"{LEGAL_DISCLAIMER}\n\n"

    def test_disclaimer_on_multiline_text(self):
        text = "Line one.\nLine two.\nLine three."
        result = inject_disclaimer(text)
        assert result.startswith(LEGAL_DISCLAIMER)
        assert text in result


# ---------------------------------------------------------------------------
# Tests for block_definitive_conclusions
# ---------------------------------------------------------------------------


class TestBlockDefinitiveConclusions:
    """Tests for definitive legal conclusion phrase blocking."""

    def test_you_must_replaced(self):
        text = "You must comply with this regulation."
        result, blocked = block_definitive_conclusions(text)
        assert "you may need to" in result
        assert "You must" in blocked

    def test_this_is_legal_replaced(self):
        text = "This is legal under UK law."
        result, blocked = block_definitive_conclusions(text)
        assert "this may be compliant" in result
        assert "This is legal" in blocked

    def test_this_is_illegal_replaced(self):
        text = "This is illegal in the EU."
        result, blocked = block_definitive_conclusions(text)
        assert "this may not be compliant" in result
        assert "This is illegal" in blocked

    def test_you_are_required_to_replaced(self):
        text = "You are required to submit documentation."
        result, blocked = block_definitive_conclusions(text)
        assert "you may be required to" in result
        assert "You are required to" in blocked

    def test_this_violates_the_law_replaced(self):
        text = "This violates the law in multiple jurisdictions."
        result, blocked = block_definitive_conclusions(text)
        assert "this may violate" in result
        assert "This violates the law" in blocked

    def test_you_are_obligated_to_replaced(self):
        text = "You are obligated to disclose this information."
        result, blocked = block_definitive_conclusions(text)
        assert "you may be obligated to" in result
        assert "You are obligated to" in blocked

    def test_it_is_mandatory_that_replaced(self):
        text = "It is mandatory that you register."
        result, blocked = block_definitive_conclusions(text)
        assert "it may be necessary that" in result
        assert "It is mandatory that" in blocked

    def test_case_insensitive_matching(self):
        text = "YOU MUST comply immediately."
        result, blocked = block_definitive_conclusions(text)
        assert "you may need to" in result
        assert "YOU MUST" in blocked

    def test_multiple_phrases_in_same_text(self):
        text = "You must comply. This is illegal. You are required to act."
        result, blocked = block_definitive_conclusions(text)
        assert "you may need to" in result
        assert "this may not be compliant" in result
        assert "you may be required to" in result
        assert len(blocked) == 3

    def test_no_definitive_phrases_returns_unchanged(self):
        text = "This may require further review by a qualified professional."
        result, blocked = block_definitive_conclusions(text)
        assert result == text
        assert blocked == []

    def test_empty_text_returns_empty(self):
        result, blocked = block_definitive_conclusions("")
        assert result == ""
        assert blocked == []


# ---------------------------------------------------------------------------
# Tests for validate_citations
# ---------------------------------------------------------------------------


class TestValidateCitations:
    """Tests for citation validation against Knowledge Base."""

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_valid_citations_pass(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.apply_guardrail.return_value = {"action": "NONE"}

        citations = ["CAP Code 3.33", "FTC Act s.5"]
        verified, removed = validate_citations(citations, "gr-123", "kb-456")

        assert verified == ["CAP Code 3.33", "FTC Act s.5"]
        assert removed == []

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_invalid_citations_removed(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.apply_guardrail.return_value = {"action": "GUARDRAIL_INTERVENED"}

        citations = ["Fake Regulation 99"]
        verified, removed = validate_citations(citations, "gr-123", "kb-456")

        assert verified == []
        assert removed == ["Fake Regulation 99"]

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_mixed_valid_and_invalid_citations(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.apply_guardrail.side_effect = [
            {"action": "NONE"},
            {"action": "GUARDRAIL_INTERVENED"},
            {"action": "NONE"},
        ]

        citations = ["Valid Reg A", "Fake Reg B", "Valid Reg C"]
        verified, removed = validate_citations(citations, "gr-123", "kb-456")

        assert verified == ["Valid Reg A", "Valid Reg C"]
        assert removed == ["Fake Reg B"]

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_api_error_fails_closed_per_citation(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.apply_guardrail.side_effect = Exception("Service unavailable")

        citations = ["Reg A", "Reg B"]
        verified, removed = validate_citations(citations, "gr-123", "kb-456")

        assert verified == []
        assert removed == ["Reg A", "Reg B"]

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_client_creation_failure_fails_closed(self, mock_boto_client):
        mock_boto_client.side_effect = Exception("Cannot create client")

        citations = ["Reg A", "Reg B"]
        verified, removed = validate_citations(citations, "gr-123", "kb-456")

        assert verified == []
        assert removed == ["Reg A", "Reg B"]

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_empty_citations_returns_empty(self, mock_boto_client):
        verified, removed = validate_citations([], "gr-123", "kb-456")
        assert verified == []
        assert removed == []
        mock_boto_client.assert_not_called()

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_guardrail_api_called_with_correct_params(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.apply_guardrail.return_value = {"action": "NONE"}

        validate_citations(["CAP Code 3.33"], "gr-abc", "kb-xyz")

        mock_boto_client.assert_called_once_with("bedrock-runtime")
        mock_client.apply_guardrail.assert_called_once_with(
            guardrailIdentifier="gr-abc",
            guardrailVersion="DRAFT",
            source="OUTPUT",
            content=[{"text": {"text": "CAP Code 3.33"}}],
        )


# ---------------------------------------------------------------------------
# Tests for apply_guardrails (integration of all steps)
# ---------------------------------------------------------------------------


class TestApplyGuardrails:
    """Tests for the main apply_guardrails function."""

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_disclaimer_always_injected(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.apply_guardrail.return_value = {"action": "NONE"}

        result = apply_guardrails(
            "Some analysis.", ["Reg A"], "gr-123", "kb-456"
        )

        assert result.text.startswith(LEGAL_DISCLAIMER)
        assert result.disclaimer_injected is True

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_definitive_phrases_blocked_in_output(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.apply_guardrail.return_value = {"action": "NONE"}

        result = apply_guardrails(
            "You must comply with this.", ["Reg A"], "gr-123", "kb-456"
        )

        assert "you may need to" in result.text
        assert "You must" not in result.text.replace(LEGAL_DISCLAIMER, "")
        assert "You must" in result.definitive_phrases_blocked

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_citation_gap_flagged_when_citations_removed(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.apply_guardrail.return_value = {"action": "GUARDRAIL_INTERVENED"}

        result = apply_guardrails(
            "Analysis text.", ["Fake Reg"], "gr-123", "kb-456"
        )

        assert result.gaps_flagged is True
        assert CITATION_GAP_MESSAGE in result.text
        assert result.citations_removed == ["Fake Reg"]
        assert result.citations_verified == []

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_no_gap_flagged_when_all_citations_valid(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.apply_guardrail.return_value = {"action": "NONE"}

        result = apply_guardrails(
            "Analysis text.", ["Valid Reg"], "gr-123", "kb-456"
        )

        assert result.gaps_flagged is False
        assert CITATION_GAP_MESSAGE not in result.text
        assert result.citations_verified == ["Valid Reg"]
        assert result.citations_removed == []

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_fail_closed_when_api_unavailable(self, mock_boto_client):
        mock_boto_client.side_effect = Exception("Service down")

        result = apply_guardrails(
            "Analysis text.", ["Reg A", "Reg B"], "gr-123", "kb-456"
        )

        # Fail closed: all citations removed
        assert result.citations_verified == []
        assert result.citations_removed == ["Reg A", "Reg B"]
        assert result.gaps_flagged is True
        assert CITATION_GAP_MESSAGE in result.text
        # Disclaimer still injected
        assert result.disclaimer_injected is True
        assert result.text.startswith(LEGAL_DISCLAIMER)

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_returns_guardrail_result_dataclass(self, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.apply_guardrail.return_value = {"action": "NONE"}

        result = apply_guardrails(
            "Text.", ["Reg A"], "gr-123", "kb-456"
        )

        assert isinstance(result, GuardrailResult)

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_no_citations_no_gap_flagged(self, mock_boto_client):
        result = apply_guardrails(
            "Analysis without citations.", [], "gr-123", "kb-456"
        )

        assert result.gaps_flagged is False
        assert result.citations_verified == []
        assert result.citations_removed == []
        assert result.disclaimer_injected is True

    @patch("lambdas.orchestrator.guardrails.boto3.client")
    def test_full_pipeline_with_mixed_inputs(self, mock_boto_client):
        """End-to-end test with definitive phrases and mixed citations."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.apply_guardrail.side_effect = [
            {"action": "NONE"},
            {"action": "GUARDRAIL_INTERVENED"},
        ]

        result = apply_guardrails(
            "You must comply. This is illegal under the act.",
            ["Valid Reg", "Fake Reg"],
            "gr-123",
            "kb-456",
        )

        # Disclaimer injected
        assert result.text.startswith(LEGAL_DISCLAIMER)
        assert result.disclaimer_injected is True

        # Definitive phrases blocked
        assert "you may need to" in result.text
        assert "this may not be compliant" in result.text
        assert len(result.definitive_phrases_blocked) == 2

        # Citations validated
        assert result.citations_verified == ["Valid Reg"]
        assert result.citations_removed == ["Fake Reg"]

        # Gap flagged
        assert result.gaps_flagged is True
        assert CITATION_GAP_MESSAGE in result.text
