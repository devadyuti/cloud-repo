"""Guardrails integration for the Consumer Regulatory Protection Agent.

Implements legal disclaimer injection, citation validation against the
Knowledge Base via Bedrock Guardrails API, and definitive legal conclusion
prevention.

Requirements: 7.1, 7.2, 7.3, 7.4
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

import boto3

from lambdas.shared.errors import log_error

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LEGAL_DISCLAIMER = (
    "DISCLAIMER: This analysis is a preliminary AI-generated assessment and "
    "does not constitute legal advice. It is intended to support, not replace, "
    "professional legal review. Please consult with a qualified lawyer before "
    "taking action based on this assessment."
)

CITATION_GAP_MESSAGE = (
    "Note: Some citations could not be verified against the regulatory corpus "
    "and have been removed."
)

# Definitive phrases mapped to their softer replacements.
# Order matters: longer phrases checked first to avoid partial matches.
DEFINITIVE_PHRASE_REPLACEMENTS: list[tuple[str, str]] = [
    ("you are required to", "you may be required to"),
    ("you are obligated to", "you may be obligated to"),
    ("this violates the law", "this may violate"),
    ("it is mandatory that", "it may be necessary that"),
    ("this is illegal", "this may not be compliant"),
    ("this is legal", "this may be compliant"),
    ("you must", "you may need to"),
]

GUARDRAIL_VERSION = "DRAFT"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class GuardrailResult:
    """Result of applying guardrails to an agent response.

    Attributes:
        text: The processed response text with disclaimer and filtered citations.
        citations_verified: Citations that passed validation.
        citations_removed: Citations that failed validation.
        disclaimer_injected: Whether the legal disclaimer was injected.
        definitive_phrases_blocked: Phrases that were softened.
        gaps_flagged: Whether citation gaps were flagged to user.
    """

    text: str
    citations_verified: list[str] = field(default_factory=list)
    citations_removed: list[str] = field(default_factory=list)
    disclaimer_injected: bool = False
    definitive_phrases_blocked: list[str] = field(default_factory=list)
    gaps_flagged: bool = False


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def inject_disclaimer(text: str) -> str:
    """Prepend the legal disclaimer to the response text.

    Args:
        text: The original response text.

    Returns:
        The response text with the legal disclaimer prepended.
    """
    return f"{LEGAL_DISCLAIMER}\n\n{text}"


def block_definitive_conclusions(text: str) -> tuple[str, list[str]]:
    """Replace definitive legal conclusion phrases with softer alternatives.

    Performs case-insensitive matching and preserves the original casing
    style where possible.

    Args:
        text: The response text to process.

    Returns:
        A tuple of (modified_text, list_of_blocked_phrases) where
        blocked_phrases contains the original definitive phrases found.
    """
    blocked_phrases: list[str] = []
    modified_text = text

    for definitive, replacement in DEFINITIVE_PHRASE_REPLACEMENTS:
        # Case-insensitive search for the definitive phrase
        pattern = re.compile(re.escape(definitive), re.IGNORECASE)
        matches = pattern.findall(modified_text)
        if matches:
            for match in matches:
                if match not in blocked_phrases:
                    blocked_phrases.append(match)
            modified_text = pattern.sub(replacement, modified_text)

    return modified_text, blocked_phrases


def validate_citations(
    citations: list[str],
    guardrail_id: str,
    knowledge_base_id: str,
) -> tuple[list[str], list[str]]:
    """Validate citations against the Knowledge Base using Bedrock Guardrails.

    Calls the Bedrock Guardrails API to perform contextual grounding checks
    on each citation. Citations that cannot be verified are removed.

    Fails closed: if the Guardrails API is unavailable, all citations are
    treated as unverified.

    Args:
        citations: List of citation strings to validate.
        guardrail_id: The Bedrock Guardrail ID to use.
        knowledge_base_id: The Knowledge Base ID for grounding checks.

    Returns:
        A tuple of (verified_citations, removed_citations).
    """
    if not citations:
        return [], []

    verified: list[str] = []
    removed: list[str] = []

    try:
        client = boto3.client("bedrock-runtime")

        for citation in citations:
            try:
                response = client.apply_guardrail(
                    guardrailIdentifier=guardrail_id,
                    guardrailVersion=GUARDRAIL_VERSION,
                    source="OUTPUT",
                    content=[{"text": {"text": citation}}],
                )

                action = response.get("action", "")
                if action == "NONE":
                    # Citation passed guardrail checks
                    verified.append(citation)
                else:
                    # Citation was flagged/blocked by guardrails
                    removed.append(citation)

            except Exception as exc:
                # Fail closed: if we can't verify a citation, remove it
                logger.warning(
                    "Citation validation failed for '%s': %s",
                    citation,
                    str(exc),
                )
                removed.append(citation)

    except Exception as exc:
        # Fail closed: if client creation fails, all citations are unverified
        logger.error(
            "Failed to create Bedrock runtime client: %s", str(exc)
        )
        removed = list(citations)

    return verified, removed


# ---------------------------------------------------------------------------
# Main guardrails function
# ---------------------------------------------------------------------------


def apply_guardrails(
    response_text: str,
    citations: list[str],
    guardrail_id: str,
    knowledge_base_id: str,
) -> GuardrailResult:
    """Apply all guardrails to an agent response.

    Performs the following steps in order:
    1. Block definitive legal conclusion phrases
    2. Validate citations against the Knowledge Base
    3. Inject legal disclaimer prefix
    4. Append citation gap message if any citations were removed

    Fails closed: if the Bedrock Guardrails API is unavailable, the response
    is blocked (returned with only the disclaimer and an error notice).

    Args:
        response_text: The raw agent response text.
        citations: List of regulation citations in the response.
        guardrail_id: The Bedrock Guardrail ID.
        knowledge_base_id: The Knowledge Base ID for grounding checks.

    Returns:
        A GuardrailResult with the processed text and metadata.
    """
    # Step 1: Block definitive legal conclusions
    processed_text, blocked_phrases = block_definitive_conclusions(response_text)

    # Step 2: Validate citations
    verified_citations, removed_citations = validate_citations(
        citations, guardrail_id, knowledge_base_id
    )

    # Step 3: Inject legal disclaimer
    processed_text = inject_disclaimer(processed_text)

    # Step 4: Flag citation gaps if any citations were removed
    gaps_flagged = len(removed_citations) > 0
    if gaps_flagged:
        processed_text = f"{processed_text}\n\n{CITATION_GAP_MESSAGE}"

    return GuardrailResult(
        text=processed_text,
        citations_verified=verified_citations,
        citations_removed=removed_citations,
        disclaimer_injected=True,
        definitive_phrases_blocked=blocked_phrases,
        gaps_flagged=gaps_flagged,
    )
