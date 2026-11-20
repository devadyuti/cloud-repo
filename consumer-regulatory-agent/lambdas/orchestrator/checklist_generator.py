"""Checklist generation logic for product launch compliance.

Produces jurisdiction-specific regulatory checklists for product launches,
including sector-specific requirements for food, cosmetics, and electronics,
and cross-jurisdiction conflict detection for multi-market launches.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
"""

from __future__ import annotations

from lambdas.shared.models import ChecklistItem
from lambdas.shared.validation import SUPPORTED_JURISDICTIONS


# ---------------------------------------------------------------------------
# Sector-specific regulatory requirements by jurisdiction
# ---------------------------------------------------------------------------

_FOOD_REQUIREMENTS: dict[str, list[dict[str, str]]] = {
    "UK": [
        {
            "description": "All pre-packed food must display allergen information in bold within the ingredients list.",
            "regulation": "Food Information Regulations 2014 (UK FIR)",
            "action": "Ensure all 14 major allergens are highlighted in bold on product packaging.",
        },
        {
            "description": "Nutritional information must be provided per 100g/ml and optionally per portion.",
            "regulation": "Food Information Regulations 2014 (UK FIR)",
            "action": "Include back-of-pack nutrition declaration with energy, fat, saturates, carbohydrate, sugars, protein, and salt.",
        },
        {
            "description": "Health and nutrition claims must be authorised and substantiated.",
            "regulation": "Nutrition and Health Claims (England) Regulations 2007",
            "action": "Verify all health claims appear on the GB Nutrition and Health Claims Register.",
        },
        {
            "description": "Food labelling must include name, ingredients list, net quantity, and use-by/best-before date.",
            "regulation": "Food Information Regulations 2014 (UK FIR)",
            "action": "Review all mandatory label fields against UK FIR Schedule 1 requirements.",
        },
    ],
    "EU": [
        {
            "description": "Allergen information must be emphasised in the ingredients list through typeset distinction.",
            "regulation": "EU Regulation 1169/2011 (Food Information to Consumers)",
            "action": "Ensure allergens are distinguished from rest of ingredients list (e.g., bold, underline, or colour).",
        },
        {
            "description": "Nutritional declaration is mandatory on all pre-packed foods.",
            "regulation": "EU Regulation 1169/2011 (Food Information to Consumers)",
            "action": "Provide mandatory nutrition declaration per 100g/ml in tabular format.",
        },
        {
            "description": "Health claims must be authorised under the EU Register of nutrition and health claims.",
            "regulation": "EU Regulation 1924/2006 (Nutrition and Health Claims)",
            "action": "Cross-reference all product claims against the EU Register of authorised health claims.",
        },
        {
            "description": "Country of origin labelling required for primary ingredients where origin differs from product origin.",
            "regulation": "EU Regulation 2018/775 (Origin of Primary Ingredient)",
            "action": "Declare origin of primary ingredient if different from stated product origin.",
        },
    ],
    "US": [
        {
            "description": "Major food allergens must be declared on the label using common names.",
            "regulation": "Food Allergen Labeling and Consumer Protection Act (FALCPA)",
            "action": "List all major allergens (milk, eggs, fish, shellfish, tree nuts, peanuts, wheat, soybeans, sesame) using common names.",
        },
        {
            "description": "Nutrition Facts panel required on all packaged food products.",
            "regulation": "21 CFR 101 (FDA Nutrition Labeling)",
            "action": "Include Nutrition Facts panel with updated format per FDA requirements.",
        },
        {
            "description": "Health claims must meet FDA significant scientific agreement standard or be qualified.",
            "regulation": "21 CFR 101.14 (FDA Health Claims)",
            "action": "Ensure health claims meet SSA standard or include appropriate qualifying language.",
        },
        {
            "description": "Food labelling must include statement of identity, net contents, and manufacturer details.",
            "regulation": "21 CFR 101 (FDA Food Labeling)",
            "action": "Verify label includes product identity, net quantity, and responsible firm name and address.",
        },
    ],
}

_COSMETICS_REQUIREMENTS: dict[str, list[dict[str, str]]] = {
    "UK": [
        {
            "description": "Full ingredient listing required using INCI nomenclature in descending order of weight.",
            "regulation": "UK Cosmetics Regulation (retained EU 1223/2009)",
            "action": "List all ingredients using INCI names in descending order of concentration.",
        },
        {
            "description": "Cosmetic Product Safety Report must be completed before placing product on market.",
            "regulation": "UK Cosmetics Regulation (retained EU 1223/2009)",
            "action": "Commission a qualified safety assessor to complete the Cosmetic Product Safety Report.",
        },
        {
            "description": "Product labelling must include function, precautions, and batch number.",
            "regulation": "UK Cosmetics Regulation (retained EU 1223/2009)",
            "action": "Ensure label includes product function, warnings/precautions, batch code, and PAO symbol.",
        },
        {
            "description": "Claims such as 'organic' or 'natural' must be substantiated and not misleading.",
            "regulation": "CAP Code (Non-broadcast Advertising) Rule 12",
            "action": "Substantiate all organic/natural claims with certification or compositional evidence.",
        },
    ],
    "EU": [
        {
            "description": "Full INCI ingredient listing required in descending order of weight.",
            "regulation": "EU Regulation 1223/2009 (Cosmetics Regulation)",
            "action": "Provide complete INCI ingredient list in descending concentration order on packaging.",
        },
        {
            "description": "Safety assessment by a qualified person is mandatory before market placement.",
            "regulation": "EU Regulation 1223/2009 (Cosmetics Regulation) Article 10",
            "action": "Obtain Cosmetic Product Safety Report from a qualified safety assessor.",
        },
        {
            "description": "Product notification via CPNP (Cosmetic Products Notification Portal) required.",
            "regulation": "EU Regulation 1223/2009 (Cosmetics Regulation) Article 13",
            "action": "Submit product notification through CPNP before placing on EU market.",
        },
        {
            "description": "Claims must comply with common criteria for cosmetic claims and not be misleading.",
            "regulation": "EU Regulation 655/2013 (Cosmetic Claims)",
            "action": "Review all product claims against the six common criteria (legal compliance, truthfulness, evidential support, honesty, fairness, informed decision-making).",
        },
    ],
    "US": [
        {
            "description": "Ingredient declaration required in descending order of predominance.",
            "regulation": "21 CFR 701.3 (FDA Cosmetic Labeling)",
            "action": "List ingredients in descending order of predominance using accepted names.",
        },
        {
            "description": "Products making drug claims (e.g., anti-aging, sunscreen) are regulated as drugs.",
            "regulation": "FD&C Act Section 201(g) (Drug Definition)",
            "action": "Review all product claims to determine if any trigger drug classification requiring FDA approval.",
        },
        {
            "description": "Label must include product identity, net contents, and distributor information.",
            "regulation": "21 CFR 701 (FDA Cosmetic Labeling)",
            "action": "Ensure label displays product name, net quantity, and name/address of manufacturer or distributor.",
        },
        {
            "description": "Organic claims must comply with USDA National Organic Program standards.",
            "regulation": "7 CFR 205 (USDA National Organic Program)",
            "action": "Obtain USDA organic certification if claiming 'organic' or verify compliance with NOP labelling tiers.",
        },
    ],
}

_ELECTRONICS_REQUIREMENTS: dict[str, list[dict[str, str]]] = {
    "UK": [
        {
            "description": "UKCA marking required for electronics placed on the GB market.",
            "regulation": "Product Safety and Metrology etc. (Amendment) Regulations 2021",
            "action": "Obtain UKCA conformity assessment and affix UKCA mark to product and documentation.",
        },
        {
            "description": "Electromagnetic compatibility (EMC) requirements must be met.",
            "regulation": "Electromagnetic Compatibility Regulations 2016 (SI 2016/1091)",
            "action": "Conduct EMC testing and prepare technical documentation demonstrating compliance.",
        },
        {
            "description": "Product recall procedures must be in place for unsafe products.",
            "regulation": "General Product Safety Regulations 2005",
            "action": "Establish product recall procedures and register with OPSS product safety database.",
        },
        {
            "description": "Electrical safety standards must be met for consumer electronics.",
            "regulation": "Electrical Equipment (Safety) Regulations 2016",
            "action": "Ensure product meets applicable BS EN safety standards and maintain technical file.",
        },
    ],
    "EU": [
        {
            "description": "CE marking required for electronics placed on the EU market.",
            "regulation": "EU Decision 768/2008 (CE Marking Framework)",
            "action": "Complete EU conformity assessment procedures and affix CE mark to product.",
        },
        {
            "description": "EMC Directive compliance required for all electronic equipment.",
            "regulation": "EU Directive 2014/30/EU (EMC Directive)",
            "action": "Perform EMC testing per harmonised standards and prepare EU Declaration of Conformity.",
        },
        {
            "description": "Product safety requirements under the General Product Safety Directive.",
            "regulation": "EU Directive 2001/95/EC (General Product Safety Directive)",
            "action": "Ensure product meets general safety requirement and maintain traceability documentation.",
        },
        {
            "description": "Digital Services Act obligations for connected devices and online marketplaces.",
            "regulation": "EU Regulation 2022/2065 (Digital Services Act)",
            "action": "Assess DSA obligations for connected product features and online sales channels.",
        },
    ],
    "US": [
        {
            "description": "FCC certification required for electronic devices that emit radio frequency energy.",
            "regulation": "47 CFR Part 15 (FCC Rules for Unintentional Radiators)",
            "action": "Obtain FCC certification or verification and include FCC ID on product label.",
        },
        {
            "description": "Product safety standards must be met per applicable UL or CPSC requirements.",
            "regulation": "Consumer Product Safety Act (CPSA)",
            "action": "Test product against applicable UL safety standards and file General Certificate of Conformity.",
        },
        {
            "description": "Product recall reporting obligations to CPSC for substantial product hazards.",
            "regulation": "Consumer Product Safety Act Section 15(b)",
            "action": "Establish procedures for reporting substantial product hazards to CPSC within 24 hours.",
        },
        {
            "description": "Energy efficiency labelling required for applicable consumer electronics.",
            "regulation": "Energy Policy and Conservation Act (EPCA) / FTC EnergyGuide",
            "action": "Determine if product requires EnergyGuide label and comply with FTC labelling rules.",
        },
    ],
}

_GENERAL_REQUIREMENTS: dict[str, list[dict[str, str]]] = {
    "UK": [
        {
            "description": "Consumer rights to refund, repair, or replacement for faulty goods.",
            "regulation": "Consumer Rights Act 2015",
            "action": "Ensure returns policy and product quality meet Consumer Rights Act standards.",
        },
        {
            "description": "Advertising must be legal, decent, honest, and truthful.",
            "regulation": "CAP Code (Non-broadcast Advertising)",
            "action": "Review all advertising materials against CAP Code principles and sector-specific rules.",
        },
        {
            "description": "Pricing must be transparent with no hidden charges or misleading price reductions.",
            "regulation": "Consumer Protection from Unfair Trading Regulations 2008",
            "action": "Verify pricing displays are clear, with genuine reference prices for any discounts.",
        },
    ],
    "EU": [
        {
            "description": "Consumers have 14-day withdrawal right for distance and off-premises contracts.",
            "regulation": "EU Directive 2011/83/EU (Consumer Rights Directive)",
            "action": "Implement 14-day cooling-off period and provide withdrawal form for online sales.",
        },
        {
            "description": "Omnibus Directive requirements for price transparency and fake reviews.",
            "regulation": "EU Directive 2019/2161 (Omnibus Directive)",
            "action": "Display lowest price in prior 30 days for any price reduction and verify review authenticity.",
        },
        {
            "description": "Digital Services Act transparency obligations for online platforms.",
            "regulation": "EU Regulation 2022/2065 (Digital Services Act)",
            "action": "Assess DSA obligations including transparency reporting and illegal content procedures.",
        },
    ],
    "US": [
        {
            "description": "Prohibition of unfair or deceptive acts or practices in commerce.",
            "regulation": "FTC Act Section 5",
            "action": "Review all consumer-facing practices against FTC unfairness and deception standards.",
        },
        {
            "description": "State consumer protection laws may impose additional requirements.",
            "regulation": "State Consumer Protection Statutes (e.g., California CLRA, New York GBL §349)",
            "action": "Identify applicable state consumer protection laws for target markets and assess compliance.",
        },
        {
            "description": "Advertising substantiation required for all objective product claims.",
            "regulation": "FTC Policy Statement on Advertising Substantiation",
            "action": "Maintain reasonable basis (competent and reliable evidence) for all advertising claims.",
        },
    ],
}

# ---------------------------------------------------------------------------
# Cross-jurisdiction conflict definitions
# ---------------------------------------------------------------------------

# Known regulatory conflicts between jurisdictions.
# Each entry: (jurisdiction_a, jurisdiction_b, description)
_KNOWN_CONFLICTS: list[tuple[str, str, str]] = [
    (
        "EU",
        "US",
        "EU requires prior-30-day lowest price disclosure for reductions (Omnibus Directive) "
        "which has no equivalent US federal requirement; dual-market pricing displays may conflict.",
    ),
    (
        "EU",
        "US",
        "EU mandates 14-day withdrawal right for distance sales (Consumer Rights Directive) "
        "while US has no federal cooling-off period for online purchases; return policies must accommodate both.",
    ),
    (
        "EU",
        "UK",
        "EU requires CPNP notification for cosmetics while UK requires SCPN notification; "
        "separate notifications needed for each market.",
    ),
    (
        "EU",
        "UK",
        "EU requires CE marking while UK requires UKCA marking for electronics; "
        "products sold in both markets need dual conformity assessment.",
    ),
    (
        "UK",
        "US",
        "UK CAP Code restricts comparative advertising claims more strictly than US FTC guidance; "
        "comparative claims valid in US may not be permissible in UK.",
    ),
    (
        "EU",
        "US",
        "EU Digital Services Act imposes platform transparency obligations with no direct US federal equivalent; "
        "online marketplace compliance strategies may differ significantly.",
    ),
]


# ---------------------------------------------------------------------------
# Sector mapping
# ---------------------------------------------------------------------------

_SECTOR_REQUIREMENTS: dict[str, dict[str, list[dict[str, str]]]] = {
    "food": _FOOD_REQUIREMENTS,
    "cosmetics": _COSMETICS_REQUIREMENTS,
    "electronics": _ELECTRONICS_REQUIREMENTS,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_checklist(
    product_category: str, jurisdictions: list[str]
) -> list[ChecklistItem]:
    """Generate a product compliance checklist for the given category and jurisdictions.

    Produces a comprehensive pre-launch compliance checklist covering general
    consumer protection requirements and sector-specific regulations for each
    selected jurisdiction.

    Args:
        product_category: The product sector (e.g., "food", "cosmetics", "electronics").
            Case-insensitive. Falls back to general requirements if not a recognised sector.
        jurisdictions: List of jurisdiction codes (e.g., ["UK", "EU", "US"]).

    Returns:
        List of ChecklistItem objects covering all applicable requirements.

    Raises:
        ValueError: If product_category is empty/whitespace or jurisdictions list is empty.
    """
    # Validate inputs
    if not product_category or not product_category.strip():
        raise ValueError(
            "product_category is required and cannot be empty or whitespace."
        )

    if not jurisdictions:
        raise ValueError(
            "At least one jurisdiction must be provided."
        )

    # Normalise category for lookup
    category_normalised = product_category.strip().lower()

    # Filter to supported jurisdictions (gracefully skip unsupported ones)
    valid_jurisdictions = [j for j in jurisdictions if j in SUPPORTED_JURISDICTIONS]

    items: list[ChecklistItem] = []
    index = 0

    # Generate sector-specific items if category is recognised
    sector_reqs = _SECTOR_REQUIREMENTS.get(category_normalised)
    if sector_reqs:
        for jurisdiction in valid_jurisdictions:
            jurisdiction_reqs = sector_reqs.get(jurisdiction, [])
            for req in jurisdiction_reqs:
                index += 1
                items.append(
                    ChecklistItem(
                        item_id=f"chk-{jurisdiction.lower()}-{index:03d}",
                        requirement_description=req["description"],
                        source_regulation=req["regulation"],
                        jurisdiction=jurisdiction,
                        compliance_action=req["action"],
                        sector_specific=True,
                    )
                )

    # Always include general requirements for each jurisdiction
    for jurisdiction in valid_jurisdictions:
        general_reqs = _GENERAL_REQUIREMENTS.get(jurisdiction, [])
        for req in general_reqs:
            index += 1
            items.append(
                ChecklistItem(
                    item_id=f"chk-{jurisdiction.lower()}-{index:03d}",
                    requirement_description=req["description"],
                    source_regulation=req["regulation"],
                    jurisdiction=jurisdiction,
                    compliance_action=req["action"],
                    sector_specific=False,
                )
            )

    # Detect and annotate cross-jurisdiction conflicts
    if len(valid_jurisdictions) > 1:
        conflicts = detect_cross_jurisdiction_conflicts(items)
        # Annotate items that are involved in conflicts
        _annotate_conflicts(items, valid_jurisdictions)

    return items


def detect_cross_jurisdiction_conflicts(items: list[ChecklistItem]) -> list[str]:
    """Identify regulatory conflicts across jurisdictions in the checklist.

    Examines the jurisdictions present in the checklist items and returns
    descriptions of known regulatory conflicts between those jurisdictions.

    Args:
        items: List of ChecklistItem objects to analyse for conflicts.

    Returns:
        List of conflict description strings identifying cross-jurisdiction
        regulatory conflicts.
    """
    if not items:
        return []

    # Determine which jurisdictions are represented
    present_jurisdictions = {item.jurisdiction for item in items}

    conflicts: list[str] = []
    for jur_a, jur_b, description in _KNOWN_CONFLICTS:
        if jur_a in present_jurisdictions and jur_b in present_jurisdictions:
            conflicts.append(description)

    return conflicts


def _annotate_conflicts(
    items: list[ChecklistItem], jurisdictions: list[str]
) -> None:
    """Annotate checklist items with cross-jurisdiction conflict references.

    Populates the `conflicts_with` field on items that are involved in
    known regulatory conflicts with items in other jurisdictions.

    Args:
        items: List of ChecklistItem objects to annotate (modified in place).
        jurisdictions: List of jurisdictions present in the checklist.
    """
    if len(jurisdictions) < 2:
        return

    jurisdiction_set = set(jurisdictions)

    for item in items:
        conflicting_jurisdictions: list[str] = []
        for jur_a, jur_b, _description in _KNOWN_CONFLICTS:
            if jur_a not in jurisdiction_set or jur_b not in jurisdiction_set:
                continue

            # Check if this item's regulation is referenced in the conflict
            if item.jurisdiction == jur_a or item.jurisdiction == jur_b:
                # Determine the other jurisdiction in the conflict pair
                other = jur_b if item.jurisdiction == jur_a else jur_a
                if other not in conflicting_jurisdictions:
                    conflicting_jurisdictions.append(other)

        if conflicting_jurisdictions:
            item.conflicts_with = conflicting_jurisdictions
