"""Unit tests for jurisdiction access control.

Tests the check_jurisdiction_access and require_jurisdiction_access functions
to verify correct enforcement of organisation-level jurisdiction permissions.
"""

import pytest

from lambdas.shared.auth import (
    JurisdictionAccessResult,
    check_jurisdiction_access,
    require_jurisdiction_access,
)
from lambdas.shared.errors import AuthorisationError
from lambdas.shared.models import UserProfile


def _make_user(permitted_jurisdictions: list[str]) -> UserProfile:
    """Create a UserProfile with the given permitted jurisdictions."""
    return UserProfile(
        user_id="user-001",
        organisation_id="org-001",
        email="test@example.com",
        role="compliance_officer",
        permitted_jurisdictions=permitted_jurisdictions,
        sector="retail",
        notification_preferences={"email": True},
        monitoring_jurisdictions=permitted_jurisdictions,
    )


class TestCheckJurisdictionAccess:
    """Tests for check_jurisdiction_access function."""

    def test_access_granted_all_jurisdictions_permitted(self):
        user = _make_user(["UK", "EU", "US"])
        result = check_jurisdiction_access(user, ["UK", "EU"])

        assert result.granted is True
        assert result.permitted == ["UK", "EU"]
        assert result.denied == []
        assert result.error_message is None

    def test_access_granted_single_jurisdiction(self):
        user = _make_user(["UK", "EU"])
        result = check_jurisdiction_access(user, ["UK"])

        assert result.granted is True
        assert result.permitted == ["UK"]
        assert result.denied == []

    def test_access_denied_some_jurisdictions_not_permitted(self):
        user = _make_user(["UK"])
        result = check_jurisdiction_access(user, ["UK", "EU", "US"])

        assert result.granted is False
        assert result.permitted == ["UK"]
        assert result.denied == ["EU", "US"]
        assert result.error_message is not None

    def test_access_denied_no_jurisdictions_permitted(self):
        user = _make_user(["UK"])
        result = check_jurisdiction_access(user, ["EU", "US"])

        assert result.granted is False
        assert result.permitted == []
        assert result.denied == ["EU", "US"]
        assert result.error_message is not None

    def test_empty_requested_jurisdictions_grants_access(self):
        user = _make_user(["UK", "EU"])
        result = check_jurisdiction_access(user, [])

        assert result.granted is True
        assert result.permitted == []
        assert result.denied == []
        assert result.error_message is None

    def test_empty_permitted_jurisdictions_denies_all(self):
        user = _make_user([])
        result = check_jurisdiction_access(user, ["UK", "EU"])

        assert result.granted is False
        assert result.permitted == []
        assert result.denied == ["UK", "EU"]
        assert result.error_message is not None

    def test_error_message_includes_denied_jurisdictions(self):
        user = _make_user(["UK"])
        result = check_jurisdiction_access(user, ["EU", "US"])

        assert "EU" in result.error_message
        assert "US" in result.error_message
        assert "contact your administrator" in result.error_message

    def test_case_sensitive_comparison(self):
        user = _make_user(["UK", "EU"])
        result = check_jurisdiction_access(user, ["uk", "eu"])

        assert result.granted is False
        assert result.denied == ["uk", "eu"]

    def test_all_requested_match_all_permitted(self):
        user = _make_user(["UK", "EU", "US"])
        result = check_jurisdiction_access(user, ["UK", "EU", "US"])

        assert result.granted is True
        assert result.permitted == ["UK", "EU", "US"]
        assert result.denied == []


class TestRequireJurisdictionAccess:
    """Tests for require_jurisdiction_access helper function."""

    def test_does_not_raise_when_access_granted(self):
        user = _make_user(["UK", "EU"])
        # Should not raise
        require_jurisdiction_access(user, ["UK"])

    def test_raises_authorisation_error_when_denied(self):
        user = _make_user(["UK"])
        with pytest.raises(AuthorisationError) as exc_info:
            require_jurisdiction_access(user, ["EU"])

        assert exc_info.value.status_code == 403

    def test_error_message_contains_denied_jurisdictions(self):
        user = _make_user(["UK"])
        with pytest.raises(AuthorisationError) as exc_info:
            require_jurisdiction_access(user, ["EU", "US"])

        assert "EU" in exc_info.value.user_message
        assert "US" in exc_info.value.user_message

    def test_empty_requested_does_not_raise(self):
        user = _make_user(["UK"])
        # Should not raise
        require_jurisdiction_access(user, [])

    def test_empty_permitted_raises_for_any_request(self):
        user = _make_user([])
        with pytest.raises(AuthorisationError):
            require_jurisdiction_access(user, ["UK"])


class TestJurisdictionAccessResultDataclass:
    """Tests for the JurisdictionAccessResult dataclass."""

    def test_default_values(self):
        result = JurisdictionAccessResult(granted=True)
        assert result.granted is True
        assert result.permitted == []
        assert result.denied == []
        assert result.error_message is None

    def test_all_fields_set(self):
        result = JurisdictionAccessResult(
            granted=False,
            permitted=["UK"],
            denied=["EU"],
            error_message="Access denied",
        )
        assert result.granted is False
        assert result.permitted == ["UK"]
        assert result.denied == ["EU"]
        assert result.error_message == "Access denied"
