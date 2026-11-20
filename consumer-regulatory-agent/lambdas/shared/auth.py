"""Jurisdiction access control for the Consumer Regulatory Protection Agent.

Provides functions to verify that a user has permission to access the
requested jurisdictions based on their organisation's permitted set.

Requirements: 6.2, 6.3
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lambdas.shared.errors import AuthorisationError
from lambdas.shared.models import UserProfile


@dataclass
class JurisdictionAccessResult:
    """Result of a jurisdiction access control check.

    Attributes:
        granted: Whether access is granted for all requested jurisdictions.
        permitted: Jurisdictions the user CAN access from the request.
        denied: Jurisdictions the user CANNOT access from the request.
        error_message: User-friendly message if access is denied.
    """

    granted: bool
    permitted: list[str] = field(default_factory=list)
    denied: list[str] = field(default_factory=list)
    error_message: str | None = None


def check_jurisdiction_access(
    user: UserProfile,
    requested_jurisdictions: list[str],
) -> JurisdictionAccessResult:
    """Check whether a user has access to the requested jurisdictions.

    Compares each requested jurisdiction against the user's permitted set.
    Access is granted only if ALL requested jurisdictions are permitted.
    Jurisdiction codes are compared case-sensitively (they are always uppercase).

    Args:
        user: The authenticated user's profile.
        requested_jurisdictions: List of jurisdiction codes the user wants to access.

    Returns:
        JurisdictionAccessResult indicating whether access is granted or denied,
        with details of which jurisdictions are permitted and which are denied.
    """
    if not requested_jurisdictions:
        return JurisdictionAccessResult(granted=True, permitted=[], denied=[])

    permitted_set = set(user.permitted_jurisdictions)

    permitted: list[str] = []
    denied: list[str] = []

    for jurisdiction in requested_jurisdictions:
        if jurisdiction in permitted_set:
            permitted.append(jurisdiction)
        else:
            denied.append(jurisdiction)

    if denied:
        denied_list = ", ".join(denied)
        error_message = (
            f"Your organisation does not have access to assessments for: "
            f"{denied_list}. Please contact your administrator to request access."
        )
        return JurisdictionAccessResult(
            granted=False,
            permitted=permitted,
            denied=denied,
            error_message=error_message,
        )

    return JurisdictionAccessResult(granted=True, permitted=permitted, denied=[])


def require_jurisdiction_access(
    user: UserProfile,
    requested_jurisdictions: list[str],
) -> None:
    """Check access and raise AuthorisationError if denied.

    Convenience wrapper around check_jurisdiction_access that raises an
    AuthorisationError with a user-friendly message when access is denied.

    Args:
        user: The authenticated user's profile.
        requested_jurisdictions: List of jurisdiction codes the user wants to access.

    Raises:
        AuthorisationError: If the user does not have access to one or more
            of the requested jurisdictions.
    """
    result = check_jurisdiction_access(user, requested_jurisdictions)
    if not result.granted:
        raise AuthorisationError(user_message=result.error_message)
