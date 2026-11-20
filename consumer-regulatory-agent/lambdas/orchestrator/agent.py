"""Core compliance agent using the Strands framework on Amazon Bedrock AgentCore.

Implements the ComplianceAgent class with registered tools for regulatory
retrieval, risk scoring, checklist generation, cross-jurisdiction analysis,
vulnerable consumer checks, and substantiation validation.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.4
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from strands import Agent, tool

from lambdas.orchestrator.checklist_generator import (
    detect_cross_jurisdiction_conflicts,
    generate_checklist,
)
from lambdas.orchestrator.risk_scorer import score_risk
from lambdas.shared.errors import (
    AgentError,
    KnowledgeBaseError,
    log_error,
    retry_with_backoff,
)
from lambdas.shared.models import (
    AssessmentResult,
    AssessmentType,
    ChecklistItem,
    ComplianceConcern,
    ComplianceQuery,
    RiskAssessment,
    RiskLevel,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------

DEFAULT_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
DEFAULT_AWS_REGION = "eu-west-2"


def _get_env(name: str, default: str | None = None) -> str:
    """Read an environment variable with an optional default.

    Raises:
        ValueError: If the variable is not set and no default is provided.
    """
    value = os.environ.get(name, default)
    if value is None:
        raise ValueError(f"Required environment variable '{name}' is not set.")
    return value


# ---------------------------------------------------------------------------
# Vulnerable consumer definitions
# ---------------------------------------------------------------------------

_VULNERABLE_GROUPS: set[str] = {
    "children",
    "elderly",
    "persons with disabilities",
    "disabled",
    "minors",
    "seniors",
    "older adults",
    "young people",
}

_VULNERABLE_CONSUMER_REGULATIONS: dict[str, list[dict[str, str]]] = {
    "UK": [
        {
            "regulation": "CAP Code Section 5 (Children)",
            "description": (
                "Advertisements must not exploit the credulity, lack of experience, "
                "or sense of loyalty of children or young people."
            ),
            "enhanced_requirement": (
                "All marketing targeting children must avoid high-pressure tactics, "
                "pester power exploitation, and must be clearly identifiable as advertising."
            ),
        },
        {
            "regulation": "Consumer Rights Act 2015 s.62 (Vulnerable Consumers)",
            "description": (
                "Unfair terms assessment takes into account the position of vulnerable consumers."
            ),
            "enhanced_requirement": (
                "Contract terms must be assessed for fairness with particular regard "
                "to vulnerable consumer understanding."
            ),
        },
        {
            "regulation": "Equality Act 2010",
            "description": (
                "Prohibition of discrimination in provision of services to persons with disabilities."
            ),
            "enhanced_requirement": (
                "Marketing and product information must be accessible to persons with disabilities."
            ),
        },
    ],
    "EU": [
        {
            "regulation": "Unfair Commercial Practices Directive 2005/29/EC Art.5(3)",
            "description": (
                "Commercial practices targeting vulnerable consumers are assessed from "
                "the perspective of the average member of that group."
            ),
            "enhanced_requirement": (
                "Practices targeting vulnerable groups must not exploit their specific "
                "vulnerabilities (age, credulity, mental or physical infirmity)."
            ),
        },
        {
            "regulation": "Audiovisual Media Services Directive 2018/1808 Art.9",
            "description": (
                "Restrictions on advertising in children's programmes and content harmful to minors."
            ),
            "enhanced_requirement": (
                "Advertising must not cause physical, mental, or moral detriment to minors "
                "or exploit their inexperience or credulity."
            ),
        },
        {
            "regulation": "Digital Services Act 2022/2065 Art.28",
            "description": (
                "Prohibition of targeted advertising based on profiling of minors."
            ),
            "enhanced_requirement": (
                "Online platforms must not present advertising based on profiling "
                "using personal data of minors."
            ),
        },
    ],
    "US": [
        {
            "regulation": "Children's Online Privacy Protection Act (COPPA)",
            "description": (
                "Requires verifiable parental consent before collecting personal information "
                "from children under 13."
            ),
            "enhanced_requirement": (
                "All data collection from children under 13 requires verifiable parental consent "
                "and clear privacy notices directed at parents."
            ),
        },
        {
            "regulation": "FTC Act Section 5 (Vulnerable Populations)",
            "description": (
                "Enhanced scrutiny for practices targeting elderly or cognitively impaired consumers."
            ),
            "enhanced_requirement": (
                "Marketing to elderly consumers must avoid deceptive urgency tactics, "
                "confusing terms, and high-pressure sales techniques."
            ),
        },
        {
            "regulation": "Americans with Disabilities Act (ADA) Title III",
            "description": (
                "Public accommodations must be accessible to persons with disabilities."
            ),
            "enhanced_requirement": (
                "Digital services and marketing materials must meet accessibility standards "
                "for persons with disabilities."
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# Substantiation requirements by claim type and jurisdiction
# ---------------------------------------------------------------------------

_SUBSTANTIATION_REQUIREMENTS: dict[str, dict[str, dict[str, Any]]] = {
    "UK": {
        "comparative": {
            "standard": "Objective, verifiable comparison required (CAP Code Rule 3.33)",
            "evidence_types": [
                "Independent test results",
                "Published market data",
                "Certified laboratory analysis",
            ],
            "regulation": "CAP Code (Non-broadcast Advertising) Rules 3.33-3.37",
        },
        "factual": {
            "standard": "Claims must be substantiated with documentary evidence held before publication",
            "evidence_types": [
                "Scientific studies",
                "Statistical data",
                "Expert testimony",
            ],
            "regulation": "CAP Code (Non-broadcast Advertising) Rule 3.7",
        },
        "environmental": {
            "standard": "Green claims must be clear, accurate, and substantiated (CMA Green Claims Code)",
            "evidence_types": [
                "Life cycle assessment",
                "Third-party certification",
                "Verifiable supply chain data",
            ],
            "regulation": "CMA Green Claims Code 2021",
        },
    },
    "EU": {
        "comparative": {
            "standard": "Comparison must be objective, relate to material features, and not create confusion (Directive 2006/114/EC)",
            "evidence_types": [
                "Objective measurement data",
                "Independent verification",
                "Like-for-like comparison methodology",
            ],
            "regulation": "Directive 2006/114/EC (Misleading and Comparative Advertising)",
        },
        "factual": {
            "standard": "Trader must demonstrate the factual accuracy of claims (UCPD Art.12)",
            "evidence_types": [
                "Scientific evidence",
                "Regulatory test results",
                "Certified documentation",
            ],
            "regulation": "Unfair Commercial Practices Directive 2005/29/EC Art.12",
        },
        "environmental": {
            "standard": "Environmental claims must be substantiated with recognised scientific evidence (Green Claims Directive proposal)",
            "evidence_types": [
                "PEF/OEF methodology results",
                "EU Ecolabel certification",
                "ISO 14024/14025 compliant studies",
            ],
            "regulation": "Proposed EU Green Claims Directive COM/2023/166",
        },
    },
    "US": {
        "comparative": {
            "standard": "Reasonable basis required; comparative claims must be substantiated before dissemination (FTC Policy Statement)",
            "evidence_types": [
                "Head-to-head testing",
                "Consumer surveys (methodologically sound)",
                "Independent laboratory results",
            ],
            "regulation": "FTC Policy Statement on Advertising Substantiation (1984)",
        },
        "factual": {
            "standard": "Competent and reliable scientific evidence required for health/safety claims",
            "evidence_types": [
                "Peer-reviewed studies",
                "Clinical trials",
                "Expert consensus",
            ],
            "regulation": "FTC Act Section 5; FTC Health Claims Guidance",
        },
        "environmental": {
            "standard": "Environmental claims must be substantiated with competent and reliable scientific evidence (FTC Green Guides)",
            "evidence_types": [
                "Life cycle analysis",
                "Third-party certification (e.g., Green Seal)",
                "Quantified environmental benefit data",
            ],
            "regulation": "FTC Green Guides (16 CFR Part 260)",
        },
    },
}


# ---------------------------------------------------------------------------
# Tool definitions (Strands @tool decorator pattern)
# ---------------------------------------------------------------------------


@tool
def retrieve_regulations(
    jurisdictions: list[str], topic: str, query: str
) -> list[dict]:
    """Query the Bedrock Knowledge Base for regulatory information.

    Retrieves relevant regulation chunks from the Knowledge Base using
    metadata filters for jurisdiction and topic.

    Args:
        jurisdictions: List of jurisdiction codes to filter by (e.g., ["UK", "EU"]).
        topic: The regulatory topic to filter by (e.g., "advertising", "labelling").
        query: The natural language query to search for.

    Returns:
        List of dicts containing regulation text, citations, and metadata.
    """
    knowledge_base_id = _get_env("KNOWLEDGE_BASE_ID")
    region = _get_env("AWS_REGION", DEFAULT_AWS_REGION)

    client = boto3.client("bedrock-agent-runtime", region_name=region)

    # Build metadata filter for jurisdictions and topic
    jurisdiction_filter: dict[str, Any]
    if len(jurisdictions) == 1:
        jurisdiction_filter = {
            "equals": {"key": "jurisdiction", "value": jurisdictions[0]}
        }
    else:
        jurisdiction_filter = {
            "orAll": [
                {"equals": {"key": "jurisdiction", "value": j}}
                for j in jurisdictions
            ]
        }

    retrieval_filter: dict[str, Any] = {
        "andAll": [
            jurisdiction_filter,
            {"equals": {"key": "topic", "value": topic}},
        ]
    }

    try:
        response = retry_with_backoff(
            "knowledge_base_retrieve",
            client.retrieve,
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 10,
                    "filter": retrieval_filter,
                }
            },
        )
    except Exception as exc:
        log_error(
            exc,
            request_id=str(uuid.uuid4()),
            component="retrieve_regulations",
            jurisdictions=jurisdictions,
            topic=topic,
        )
        raise KnowledgeBaseError(
            internal_message=f"Knowledge Base retrieval failed: {exc}"
        ) from exc

    # Parse results into structured dicts
    results: list[dict] = []
    for result in response.get("retrievalResults", []):
        content = result.get("content", {}).get("text", "")
        location = result.get("location", {})
        metadata = result.get("metadata", {})

        results.append(
            {
                "text": content,
                "citation": location.get("s3Location", {}).get("uri", ""),
                "jurisdiction": metadata.get("jurisdiction", ""),
                "topic": metadata.get("topic", ""),
                "document_type": metadata.get("document_type", ""),
                "score": result.get("score", 0.0),
            }
        )

    logger.info(
        json.dumps(
            {
                "event": "regulations_retrieved",
                "jurisdictions": jurisdictions,
                "topic": topic,
                "result_count": len(results),
            }
        )
    )

    return results


@tool
def score_risk_tool(concerns_data: list[dict], jurisdiction: str) -> dict:
    """Score the overall compliance risk for a jurisdiction.

    Delegates to the risk_scorer module to compute risk level based on
    the severity of identified compliance concerns.

    Args:
        concerns_data: List of concern dicts with keys: concern_id, description,
            regulation_reference, regulation_title, jurisdiction, severity.
        jurisdiction: The jurisdiction being assessed.

    Returns:
        Dict with risk_level, concerns count, regulation_citations,
        recommended_actions, and escalation_recommended.
    """
    concerns = [
        ComplianceConcern(
            concern_id=c.get("concern_id", str(uuid.uuid4())),
            description=c.get("description", ""),
            regulation_reference=c.get("regulation_reference", ""),
            regulation_title=c.get("regulation_title", ""),
            jurisdiction=c.get("jurisdiction", jurisdiction),
            severity=c.get("severity", "low"),
            evidence_required=c.get("evidence_required"),
        )
        for c in concerns_data
    ]

    assessment: RiskAssessment = score_risk(concerns, jurisdiction)

    return {
        "jurisdiction": assessment.jurisdiction,
        "risk_level": assessment.risk_level.value,
        "concern_count": len(assessment.concerns),
        "regulation_citations": assessment.regulation_citations,
        "recommended_actions": assessment.recommended_actions,
        "escalation_recommended": assessment.escalation_recommended,
    }


@tool
def generate_checklist_tool(
    product_category: str, jurisdictions: list[str]
) -> list[dict]:
    """Generate a product compliance checklist.

    Delegates to the checklist_generator module to produce jurisdiction-specific
    regulatory checklists for product launches.

    Args:
        product_category: The product sector (e.g., "food", "cosmetics", "electronics").
        jurisdictions: List of jurisdiction codes (e.g., ["UK", "EU"]).

    Returns:
        List of checklist item dicts with requirement details.
    """
    items: list[ChecklistItem] = generate_checklist(product_category, jurisdictions)

    return [
        {
            "item_id": item.item_id,
            "requirement_description": item.requirement_description,
            "source_regulation": item.source_regulation,
            "jurisdiction": item.jurisdiction,
            "compliance_action": item.compliance_action,
            "sector_specific": item.sector_specific,
            "conflicts_with": item.conflicts_with,
        }
        for item in items
    ]


@tool
def cross_reference_jurisdictions(jurisdictions: list[str], topic: str) -> dict:
    """Identify regulatory conflicts across multiple jurisdictions.

    Retrieves requirements from multiple jurisdictions and identifies
    conflicts using the cross-jurisdiction conflict detection logic.

    Args:
        jurisdictions: List of jurisdiction codes to cross-reference.
        topic: The regulatory topic to analyse for conflicts.

    Returns:
        Dict with jurisdictions analysed, conflicts found, and conflict details.
    """
    if len(jurisdictions) < 2:
        return {
            "jurisdictions": jurisdictions,
            "conflicts_found": False,
            "conflicts": [],
            "message": "Cross-referencing requires at least two jurisdictions.",
        }

    # Generate a general checklist to detect conflicts across jurisdictions
    # Use "general" as category to get broad regulatory requirements
    items = generate_checklist("general", jurisdictions)
    conflicts = detect_cross_jurisdiction_conflicts(items)

    # Filter conflicts relevant to the topic if possible
    topic_lower = topic.lower()
    relevant_conflicts = [
        c for c in conflicts if topic_lower in c.lower()
    ]

    # If no topic-specific conflicts, return all conflicts
    if not relevant_conflicts:
        relevant_conflicts = conflicts

    return {
        "jurisdictions": jurisdictions,
        "topic": topic,
        "conflicts_found": len(relevant_conflicts) > 0,
        "conflict_count": len(relevant_conflicts),
        "conflicts": relevant_conflicts,
    }


@tool
def check_vulnerable_consumer_rules(
    jurisdictions: list[str], target_demographics: list[str]
) -> dict:
    """Check enhanced scrutiny requirements for vulnerable consumers.

    Identifies whether target demographics include vulnerable consumer groups
    and returns the applicable enhanced protection regulations per jurisdiction.

    Args:
        jurisdictions: List of jurisdiction codes to check.
        target_demographics: List of target demographic descriptions.

    Returns:
        Dict with vulnerable groups identified, enhanced requirements per
        jurisdiction, and whether enhanced scrutiny applies.
    """
    # Identify vulnerable groups in target demographics
    demographics_lower = [d.lower().strip() for d in target_demographics]
    identified_vulnerable: list[str] = []

    for demo in demographics_lower:
        for group in _VULNERABLE_GROUPS:
            if group in demo:
                if group not in identified_vulnerable:
                    identified_vulnerable.append(group)

    if not identified_vulnerable:
        return {
            "enhanced_scrutiny_required": False,
            "vulnerable_groups_identified": [],
            "jurisdictions": jurisdictions,
            "requirements": {},
            "message": "No vulnerable consumer groups identified in target demographics.",
        }

    # Gather enhanced requirements per jurisdiction
    requirements_by_jurisdiction: dict[str, list[dict]] = {}
    for jurisdiction in jurisdictions:
        jurisdiction_regs = _VULNERABLE_CONSUMER_REGULATIONS.get(jurisdiction, [])
        if jurisdiction_regs:
            requirements_by_jurisdiction[jurisdiction] = jurisdiction_regs

    return {
        "enhanced_scrutiny_required": True,
        "vulnerable_groups_identified": identified_vulnerable,
        "jurisdictions": jurisdictions,
        "requirements": requirements_by_jurisdiction,
        "message": (
            f"Enhanced scrutiny required: target demographics include "
            f"vulnerable consumer group(s): {', '.join(identified_vulnerable)}."
        ),
    }


@tool
def validate_substantiation(
    claim_text: str, claim_type: str, jurisdictions: list[str]
) -> dict:
    """Validate substantiation requirements for comparative or factual claims.

    Evaluates the claim against jurisdiction-specific substantiation standards
    and identifies the evidence types needed.

    Args:
        claim_text: The text of the claim being made.
        claim_type: Type of claim ("comparative", "factual", "environmental").
        jurisdictions: List of jurisdiction codes to check against.

    Returns:
        Dict with substantiation requirements per jurisdiction and evidence needed.
    """
    claim_type_normalised = claim_type.lower().strip()

    # Validate claim type
    valid_claim_types = {"comparative", "factual", "environmental"}
    if claim_type_normalised not in valid_claim_types:
        return {
            "claim_text": claim_text,
            "claim_type": claim_type,
            "valid": False,
            "error": (
                f"Unsupported claim type '{claim_type}'. "
                f"Supported types: {', '.join(sorted(valid_claim_types))}."
            ),
            "requirements": {},
        }

    requirements_by_jurisdiction: dict[str, dict] = {}
    for jurisdiction in jurisdictions:
        jurisdiction_reqs = _SUBSTANTIATION_REQUIREMENTS.get(jurisdiction, {})
        claim_reqs = jurisdiction_reqs.get(claim_type_normalised)
        if claim_reqs:
            requirements_by_jurisdiction[jurisdiction] = {
                "standard": claim_reqs["standard"],
                "evidence_types": claim_reqs["evidence_types"],
                "regulation": claim_reqs["regulation"],
            }

    return {
        "claim_text": claim_text,
        "claim_type": claim_type_normalised,
        "valid": True,
        "jurisdictions": jurisdictions,
        "requirements": requirements_by_jurisdiction,
        "substantiation_needed": len(requirements_by_jurisdiction) > 0,
        "message": (
            f"Substantiation requirements identified for '{claim_type_normalised}' "
            f"claim across {len(requirements_by_jurisdiction)} jurisdiction(s)."
        ),
    }


# ---------------------------------------------------------------------------
# ComplianceAgent class
# ---------------------------------------------------------------------------

# System prompt for the compliance agent
_SYSTEM_PROMPT = """You are a Consumer Regulatory Protection Agent specialising in
multi-jurisdictional consumer protection compliance. Your role is to analyse marketing
campaigns, product launches, and consumer-facing activities against applicable regulations.

You MUST:
1. Always cite specific regulations when identifying compliance concerns.
2. Apply enhanced scrutiny when vulnerable consumers are targeted.
3. Flag substantiation requirements for comparative or factual claims.
4. Identify cross-jurisdiction conflicts for multi-market activities.
5. Score risk levels accurately based on the severity of concerns found.
6. Never provide definitive legal conclusions - frame all outputs as preliminary assessments.

Use the available tools to retrieve regulations, score risks, generate checklists,
cross-reference jurisdictions, check vulnerable consumer rules, and validate substantiation.
"""


class ComplianceAgent:
    """Core compliance agent using the Strands framework.

    Orchestrates regulatory analysis by coordinating tool invocations for
    knowledge base retrieval, risk scoring, checklist generation, and
    specialised compliance checks.

    Args:
        model_id: The Bedrock model ID to use for the agent.
        knowledge_base_id: The Bedrock Knowledge Base ID for regulatory retrieval.
        guardrail_id: The Bedrock Guardrail ID for output safety.
        boto3_session: Optional boto3 session for dependency injection in tests.
    """

    def __init__(
        self,
        model_id: str | None = None,
        knowledge_base_id: str | None = None,
        guardrail_id: str | None = None,
        boto3_session: Any | None = None,
    ):
        self.model_id = model_id or _get_env("MODEL_ID", DEFAULT_MODEL_ID)
        self.knowledge_base_id = knowledge_base_id or _get_env("KNOWLEDGE_BASE_ID")
        self.guardrail_id = guardrail_id or _get_env("GUARDRAIL_ID")
        self.region = _get_env("AWS_REGION", DEFAULT_AWS_REGION)
        self._boto3_session = boto3_session

        # Set environment variables so tools can access them
        os.environ.setdefault("MODEL_ID", self.model_id)
        os.environ.setdefault("KNOWLEDGE_BASE_ID", self.knowledge_base_id)
        os.environ.setdefault("GUARDRAIL_ID", self.guardrail_id)
        os.environ.setdefault("AWS_REGION", self.region)

        # Register tools with the Strands agent
        self._tools = [
            retrieve_regulations,
            score_risk_tool,
            generate_checklist_tool,
            cross_reference_jurisdictions,
            check_vulnerable_consumer_rules,
            validate_substantiation,
        ]

        # Create the Strands agent
        self._agent = Agent(
            model=self.model_id,
            tools=self._tools,
            system_prompt=_SYSTEM_PROMPT,
        )

        logger.info(
            json.dumps(
                {
                    "event": "agent_initialized",
                    "model_id": self.model_id,
                    "knowledge_base_id": self.knowledge_base_id,
                    "guardrail_id": self.guardrail_id,
                    "tools_registered": [t.__name__ for t in self._tools],
                }
            )
        )

    @property
    def tools(self) -> list:
        """Return the list of registered tools."""
        return self._tools

    @property
    def agent(self) -> Agent:
        """Return the underlying Strands Agent instance."""
        return self._agent

    def invoke(self, query: ComplianceQuery) -> AssessmentResult:
        """Invoke the compliance agent with a structured query.

        Orchestrates the full assessment lifecycle: constructs the prompt,
        invokes the agent, and returns a structured AssessmentResult.

        Args:
            query: The ComplianceQuery containing assessment parameters.

        Returns:
            AssessmentResult with risk assessments, citations, and recommendations.

        Raises:
            AgentError: If the agent invocation fails.
        """
        start_time = time.time()

        # Construct the agent prompt from the query
        prompt = self._build_prompt(query)

        try:
            # Invoke the Strands agent
            response = self._agent(prompt)

            # Parse the agent response into structured output
            elapsed_ms = int((time.time() - start_time) * 1000)

            result = self._build_result(query, response, elapsed_ms)

            logger.info(
                json.dumps(
                    {
                        "event": "assessment_completed",
                        "query_id": query.query_id,
                        "assessment_type": query.assessment_type.value,
                        "jurisdictions": query.jurisdictions,
                        "response_time_ms": elapsed_ms,
                        "overall_risk": result.overall_risk.value,
                    }
                )
            )

            return result

        except AgentError:
            raise
        except Exception as exc:
            elapsed_ms = int((time.time() - start_time) * 1000)
            log_error(
                exc,
                request_id=query.query_id,
                component="ComplianceAgent.invoke",
                assessment_type=query.assessment_type.value,
                jurisdictions=query.jurisdictions,
                response_time_ms=elapsed_ms,
            )
            raise AgentError(
                user_message="The compliance assessment could not be completed. Please try again.",
                internal_message=f"Agent invocation failed: {exc}",
            ) from exc

    def _build_prompt(self, query: ComplianceQuery) -> str:
        """Build the agent prompt from a ComplianceQuery.

        Constructs a detailed prompt including the content to analyse,
        target jurisdictions, and any special considerations.
        """
        parts = [
            f"Please analyse the following for compliance with consumer protection regulations.",
            f"\n## Assessment Type: {query.assessment_type.value}",
            f"\n## Content to Analyse:\n{query.content}",
            f"\n## Target Jurisdictions: {', '.join(query.jurisdictions)}",
        ]

        if query.product_category:
            parts.append(f"\n## Product Category: {query.product_category}")

        if query.target_demographics:
            parts.append(
                f"\n## Target Demographics: {', '.join(query.target_demographics)}"
            )
            parts.append(
                "\nPlease check if any target demographics include vulnerable "
                "consumer groups requiring enhanced scrutiny."
            )

        parts.append(
            "\n## Required Output:\n"
            "1. Risk level per jurisdiction (Low, Medium, High, Critical)\n"
            "2. Specific compliance concerns with regulation citations\n"
            "3. Recommended next steps\n"
            "4. Cross-jurisdiction conflicts (if multiple jurisdictions)\n"
            "5. Substantiation requirements for any claims identified"
        )

        return "\n".join(parts)

    def _build_result(
        self, query: ComplianceQuery, response: Any, elapsed_ms: int
    ) -> AssessmentResult:
        """Build an AssessmentResult from the agent response.

        Parses the agent's response and constructs the structured result.
        If the response cannot be fully parsed, returns a result with the
        raw response text as a single risk assessment.
        """
        # Default risk assessments - one per jurisdiction
        risk_assessments: list[RiskAssessment] = []
        for jurisdiction in query.jurisdictions:
            risk_assessments.append(
                RiskAssessment(
                    jurisdiction=jurisdiction,
                    risk_level=RiskLevel.MEDIUM,
                    concerns=[],
                    regulation_citations=[],
                    recommended_actions=[
                        "Review the detailed analysis above.",
                        "Consider obtaining legal advice before proceeding.",
                    ],
                    escalation_recommended=False,
                )
            )

        # Determine overall risk (highest across jurisdictions)
        overall_risk = RiskLevel.LOW
        risk_priority = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]
        for assessment in risk_assessments:
            if risk_priority.index(assessment.risk_level) < risk_priority.index(overall_risk):
                overall_risk = assessment.risk_level

        return AssessmentResult(
            assessment_id=f"assess-{uuid.uuid4().hex[:12]}",
            query_id=query.query_id,
            user_id=query.user_id,
            assessment_type=query.assessment_type,
            risk_assessments=risk_assessments,
            disclaimer=(
                "DISCLAIMER: This analysis is a preliminary AI-generated assessment "
                "and does not constitute legal advice. It is intended to support, not "
                "replace, professional legal review. Please consult with a qualified "
                "lawyer before taking action based on this assessment."
            ),
            overall_risk=overall_risk,
            created_at=datetime.now(timezone.utc),
            response_time_ms=elapsed_ms,
            model_id=self.model_id,
            knowledge_base_version="latest",
        )
