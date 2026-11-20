"""Input validation module for the Consumer Regulatory Protection Agent.

Provides structured validation for compliance queries, ensuring required fields
are present and jurisdiction codes are within the supported set.

Validates: Requirements 1.6, 1.7, 2.6
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lambdas.shared.models import ComplianceQuery


# Supported jurisdiction codes
SUPPORTED_JURISDICTIONS: set[str] = {"UK", "EU", "US"}


@dataclass
class ValidationError:
    """A single validation error identifying a specific field issue."""

    field: str
    message: str


@dataclass
class ValidationResult:
    """Result of a validation operation containing any errors found."""

    errors: list[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Returns True if no validation errors were found."""
        return len(self.errors) == 0


def validate_jurisdictions(jurisdictions: list[str]) -> ValidationResult:
    """Validate a list of jurisdiction codes against the supported set.

    Checks that the list is non-empty and all codes are in SUPPORTED_JURISDICTIONS.

    Args:
        jurisdictions: List of jurisdiction code strings to validate.

    Returns:
        ValidationResult with errors for empty list or unsupported codes.
    """
    errors: list[ValidationError] = []

    if not jurisdictions:
        errors.append(
            ValidationError(
                field="jurisdictions",
                message="At least one jurisdiction must be selected.",
            )
        )
        return ValidationResult(errors=errors)

    unsupported = [j for j in jurisdictions if j not in SUPPORTED_JURISDICTIONS]
    if unsupported:
        available = ", ".join(sorted(SUPPORTED_JURISDICTIONS))
        errors.append(
            ValidationError(
                field="jurisdictions",
                message=(
                    f"Unsupported jurisdiction(s): {', '.join(unsupported)}. "
                    f"Available jurisdictions: {available}."
                ),
            )
        )

    return ValidationResult(errors=errors)


def validate_compliance_query(query: ComplianceQuery) -> ValidationResult:
    """Validate a ComplianceQuery for required fields and supported values.

    Checks:
    - campaign_copy (content) is not empty or whitespace-only
    - jurisdictions list is not empty
    - all jurisdiction codes are in the supported set

    Args:
        query: The ComplianceQuery to validate.

    Returns:
        ValidationResult with all validation errors found.
    """
    errors: list[ValidationError] = []

    # Validate campaign copy / content is not empty or whitespace
    if not query.content or not query.content.strip():
        errors.append(
            ValidationError(
                field="campaign_copy",
                message="Campaign copy is required and cannot be empty or whitespace.",
            )
        )

    # Validate jurisdictions
    jurisdiction_result = validate_jurisdictions(query.jurisdictions)
    errors.extend(jurisdiction_result.errors)

    return ValidationResult(errors=errors)
