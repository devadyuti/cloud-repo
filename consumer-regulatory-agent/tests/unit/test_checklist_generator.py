"""Unit tests for the checklist generation logic.

Verifies that generate_checklist produces correct, complete checklist items
with sector-specific logic and cross-jurisdiction conflict detection.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

import pytest

from lambdas.orchestrator.checklist_generator import (
    detect_cross_jurisdiction_conflicts,
    generate_checklist,
)
from lambdas.shared.models import ChecklistItem


class TestGenerateChecklistValidation:
    """Tests for input validation."""

    def test_empty_product_category_raises_value_error(self):
        with pytest.raises(ValueError, match="product_category is required"):
            generate_checklist("", ["UK"])

    def test_whitespace_product_category_raises_value_error(self):
        with pytest.raises(ValueError, match="product_category is required"):
            generate_checklist("   ", ["EU"])

    def test_empty_jurisdictions_raises_value_error(self):
        with pytest.raises(ValueError, match="At least one jurisdiction"):
            generate_checklist("food", [])

    def test_unsupported_jurisdiction_handled_gracefully(self):
        # Unsupported jurisdictions are skipped; if all are unsupported, returns empty
        result = generate_checklist("food", ["AU", "NZ"])
        assert result == []

    def test_mixed_supported_and_unsupported_jurisdictions(self):
        result = generate_checklist("food", ["UK", "AU"])
        # Should only contain UK items
        assert all(item.jurisdiction == "UK" for item in result)
        assert len(result) > 0


class TestGenerateChecklistStructure:
    """Tests for checklist item structural completeness (Requirement 2.5)."""

    def test_every_item_has_non_empty_requirement_description(self):
        items = generate_checklist("food", ["UK", "EU", "US"])
        for item in items:
            assert item.requirement_description
            assert item.requirement_description.strip()

    def test_every_item_has_non_empty_source_regulation(self):
        items = generate_checklist("cosmetics", ["UK", "EU", "US"])
        for item in items:
            assert item.source_regulation
            assert item.source_regulation.strip()

    def test_every_item_has_valid_jurisdiction(self):
        items = generate_checklist("electronics", ["UK", "EU"])
        for item in items:
            assert item.jurisdiction in {"UK", "EU", "US"}

    def test_every_item_has_non_empty_compliance_action(self):
        items = generate_checklist("food", ["US"])
        for item in items:
            assert item.compliance_action
            assert item.compliance_action.strip()

    def test_every_item_has_unique_id(self):
        items = generate_checklist("food", ["UK", "EU", "US"])
        ids = [item.item_id for item in items]
        assert len(ids) == len(set(ids))

    def test_item_id_format(self):
        items = generate_checklist("food", ["UK"])
        for item in items:
            assert item.item_id.startswith("chk-")

    def test_returns_checklist_item_instances(self):
        items = generate_checklist("food", ["UK"])
        for item in items:
            assert isinstance(item, ChecklistItem)


class TestGenerateChecklistSectorSpecific:
    """Tests for sector-specific logic (Requirements 2.2, 2.3)."""

    def test_food_includes_allergen_requirements(self):
        items = generate_checklist("food", ["UK"])
        descriptions = [item.requirement_description.lower() for item in items]
        assert any("allergen" in d for d in descriptions)

    def test_food_includes_nutritional_information(self):
        items = generate_checklist("food", ["UK"])
        descriptions = [item.requirement_description.lower() for item in items]
        assert any("nutri" in d for d in descriptions)

    def test_food_includes_health_claims(self):
        items = generate_checklist("food", ["EU"])
        descriptions = [item.requirement_description.lower() for item in items]
        assert any("health claim" in d for d in descriptions)

    def test_cosmetics_includes_ingredient_listing(self):
        items = generate_checklist("cosmetics", ["UK"])
        descriptions = [item.requirement_description.lower() for item in items]
        assert any("ingredient" in d for d in descriptions)

    def test_cosmetics_includes_safety_assessment(self):
        items = generate_checklist("cosmetics", ["EU"])
        descriptions = [item.requirement_description.lower() for item in items]
        assert any("safety" in d for d in descriptions)

    def test_cosmetics_includes_organic_natural_claims(self):
        items = generate_checklist("cosmetics", ["UK"])
        descriptions = [item.requirement_description.lower() for item in items]
        assert any("organic" in d or "natural" in d for d in descriptions)

    def test_electronics_includes_ce_marking_for_eu(self):
        items = generate_checklist("electronics", ["EU"])
        sector_items = [i for i in items if i.sector_specific]
        descriptions = [item.requirement_description.lower() for item in sector_items]
        assert any("ce marking" in d for d in descriptions)

    def test_electronics_includes_ukca_marking_for_uk(self):
        items = generate_checklist("electronics", ["UK"])
        sector_items = [i for i in items if i.sector_specific]
        descriptions = [item.requirement_description.lower() for item in sector_items]
        assert any("ukca" in d for d in descriptions)

    def test_electronics_includes_emc_compliance(self):
        items = generate_checklist("electronics", ["UK"])
        descriptions = [item.requirement_description.lower() for item in items]
        assert any("emc" in d or "electromagnetic" in d for d in descriptions)

    def test_electronics_includes_product_recalls(self):
        items = generate_checklist("electronics", ["UK"])
        descriptions = [item.requirement_description.lower() for item in items]
        assert any("recall" in d for d in descriptions)

    def test_sector_specific_items_flagged_correctly(self):
        items = generate_checklist("food", ["UK"])
        sector_items = [i for i in items if i.sector_specific]
        general_items = [i for i in items if not i.sector_specific]
        assert len(sector_items) > 0
        assert len(general_items) > 0

    def test_category_is_case_insensitive(self):
        items_lower = generate_checklist("food", ["UK"])
        items_upper = generate_checklist("FOOD", ["UK"])
        items_mixed = generate_checklist("Food", ["UK"])
        assert len(items_lower) == len(items_upper) == len(items_mixed)

    def test_eu_electronics_includes_digital_services_act(self):
        items = generate_checklist("electronics", ["EU"])
        regulations = [item.source_regulation.lower() for item in items]
        assert any("digital services act" in r for r in regulations)


class TestGenerateChecklistGeneral:
    """Tests for general requirements (always included)."""

    def test_general_requirements_included_for_known_sector(self):
        items = generate_checklist("food", ["UK"])
        general_items = [i for i in items if not i.sector_specific]
        assert len(general_items) > 0

    def test_general_requirements_included_for_unknown_sector(self):
        items = generate_checklist("toys", ["UK"])
        # Unknown sector still gets general requirements
        assert len(items) > 0
        assert all(not item.sector_specific for item in items)

    def test_uk_includes_consumer_rights_act(self):
        items = generate_checklist("general", ["UK"])
        regulations = [item.source_regulation for item in items]
        assert any("Consumer Rights Act" in r for r in regulations)

    def test_uk_includes_cap_code(self):
        items = generate_checklist("general", ["UK"])
        regulations = [item.source_regulation for item in items]
        assert any("CAP Code" in r for r in regulations)

    def test_eu_includes_omnibus_directive(self):
        items = generate_checklist("general", ["EU"])
        regulations = [item.source_regulation for item in items]
        assert any("Omnibus" in r for r in regulations)

    def test_eu_includes_digital_services_act(self):
        items = generate_checklist("general", ["EU"])
        regulations = [item.source_regulation for item in items]
        assert any("Digital Services Act" in r for r in regulations)

    def test_us_includes_ftc_act(self):
        items = generate_checklist("general", ["US"])
        regulations = [item.source_regulation for item in items]
        assert any("FTC Act" in r for r in regulations)

    def test_us_includes_state_consumer_protection(self):
        items = generate_checklist("general", ["US"])
        regulations = [item.source_regulation for item in items]
        assert any("State Consumer Protection" in r for r in regulations)


class TestCrossJurisdictionConflicts:
    """Tests for cross-jurisdiction conflict detection (Requirement 2.4)."""

    def test_single_jurisdiction_no_conflicts(self):
        items = generate_checklist("food", ["UK"])
        conflicts = detect_cross_jurisdiction_conflicts(items)
        assert conflicts == []

    def test_eu_us_detects_conflicts(self):
        items = generate_checklist("food", ["EU", "US"])
        conflicts = detect_cross_jurisdiction_conflicts(items)
        assert len(conflicts) > 0

    def test_eu_uk_detects_conflicts(self):
        items = generate_checklist("electronics", ["EU", "UK"])
        conflicts = detect_cross_jurisdiction_conflicts(items)
        assert len(conflicts) > 0

    def test_all_jurisdictions_detects_multiple_conflicts(self):
        items = generate_checklist("food", ["UK", "EU", "US"])
        conflicts = detect_cross_jurisdiction_conflicts(items)
        assert len(conflicts) > 1

    def test_conflicts_are_strings(self):
        items = generate_checklist("food", ["UK", "EU", "US"])
        conflicts = detect_cross_jurisdiction_conflicts(items)
        for conflict in conflicts:
            assert isinstance(conflict, str)
            assert len(conflict) > 0

    def test_empty_items_returns_no_conflicts(self):
        conflicts = detect_cross_jurisdiction_conflicts([])
        assert conflicts == []

    def test_multi_jurisdiction_items_have_conflicts_with_populated(self):
        items = generate_checklist("electronics", ["EU", "UK"])
        items_with_conflicts = [i for i in items if i.conflicts_with]
        assert len(items_with_conflicts) > 0

    def test_conflicts_with_contains_other_jurisdiction(self):
        items = generate_checklist("food", ["EU", "US"])
        for item in items:
            if item.conflicts_with:
                # conflicts_with should reference the OTHER jurisdiction
                assert item.jurisdiction not in item.conflicts_with

    def test_uk_us_detects_conflicts(self):
        items = generate_checklist("food", ["UK", "US"])
        conflicts = detect_cross_jurisdiction_conflicts(items)
        assert len(conflicts) > 0
