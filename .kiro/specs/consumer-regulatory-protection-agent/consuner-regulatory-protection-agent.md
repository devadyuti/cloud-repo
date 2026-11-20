
# Consumer Regulatory Compliance Advisor Agent

## Scope

Build a Bedrock AgentCore agent that enables Consumer Markets legal practice clients to check marketing campaigns, product claims, and consumer-facing activities against multi-jurisdictional consumer protection regulations. The agent ingests regulatory knowledge bases (UK Consumer Rights Act, EU Consumer Protection Cooperation Regulation, FTC Act, ACCC guidelines), provides compliance risk assessments, and generates jurisdiction-specific action items for remediation.

## User Stories

### Story 1: Marketing Campaign Compliance Check
**As a** brand marketing director at a retail company,
**I want to** submit my draft marketing campaign copy and target markets,
**So that** I can receive an instant preliminary compliance risk assessment before engaging lawyers for detailed review.

**Acceptance Criteria (EARS):**
- When the user submits campaign copy and selects target jurisdictions, the system shall analyse the content against applicable consumer protection regulations for each jurisdiction.
- Where the campaign contains comparative claims, the system shall flag requirements for substantiation evidence under each jurisdiction's advertising standards.
- If the campaign targets vulnerable consumers (children, elderly), the system shall apply enhanced scrutiny rules and flag additional regulatory requirements.
- The system shall generate a risk score (Low/Medium/High/Critical) per jurisdiction with specific regulation references.
- The system shall provide a structured output with: risk level, applicable regulations, specific concerns, and recommended next steps (including when to escalate to human lawyers).

### Story 2: Product Launch Regulatory Checklist
**As a** product compliance manager at a consumer goods company,
**I want to** input my product category, target markets, and product claims,
**So that** I can receive a jurisdiction-specific regulatory checklist before launch.

**Acceptance Criteria (EARS):**
- When the user provides product category and target jurisdictions, the system shall generate a comprehensive pre-launch compliance checklist.
- Where the product involves food, cosmetics, or electronics, the system shall include sector-specific labelling and safety requirements.
- If the product is being launched in the EU, the system shall include Digital Services Act and Omnibus Directive requirements where applicable.
- The system shall cross-reference requirements across jurisdictions and highlight conflicts or additional burdens for multi-market launches.

### Story 3: Consumer Data Collection Compliance
**As a** digital marketing lead running loyalty programmes,
**I want to** validate my consumer data collection practices against privacy and consumer protection regulations,
**So that** I can ensure our loyalty programme complies with both data privacy and consumer protection law.

**Acceptance Criteria (EARS):**
- When the user describes their data collection mechanism and jurisdictions, the system shall assess compliance against both consumer protection and data privacy regulations.
- Where consent mechanisms are described, the system shall evaluate whether they meet the "clear and prominent" standards required by consumer protection law (distinct from GDPR consent).
- The system shall identify where consumer protection law imposes additional requirements beyond data privacy law.

### Story 4: Regulatory Change Monitoring
**As a** in-house legal counsel at a leisure sector company,
**I want to** receive alerts when consumer protection regulations change in my operating jurisdictions,
**So that** I can proactively assess impact on our business operations.

**Acceptance Criteria (EARS):**
- When a regulatory update is detected in a monitored jurisdiction, the system shall generate an impact summary relevant to the user's sector and operations.
- The system shall categorise changes by urgency: immediate action required, upcoming deadline, or awareness only.
- Where a change affects multiple jurisdictions, the system shall provide a consolidated cross-jurisdictional impact view.

### Story 5: Escalation to Human Lawyers
**As a** client user of the compliance advisor,
**I want to** seamlessly escalate complex queries to the firm's Consumer Markets legal team,
**So that** I can get human expert review when the AI identifies high-risk or ambiguous scenarios.

**Acceptance Criteria (EARS):**
- When the risk assessment returns "High" or "Critical", the system shall offer one-click escalation to the Consumer Markets legal team.
- The system shall package the query context, AI analysis, and relevant regulation references into a structured brief for the receiving lawyer.
- If the user confirms escalation, the system shall create a matter intake with all context attached.

## Priority Backlog

1. **P1 - Core Compliance Engine**: Stories 1 & 2 - Campaign check and product launch checklist (foundational RAG + agent orchestration)
2. **P2 - Data & Privacy Crossover**: Story 3 - Consumer data compliance (extends knowledge base, adds privacy regulation corpus)
3. **P3 - Monitoring & Alerts**: Story 4 - Regulatory change monitoring (adds event-driven architecture, scheduled ingestion)
4. **P4 - Escalation Integration**: Story 5 - Practice management system integration (adds API integration with matter management)

## Technical Constraints

- Agent orchestration via Amazon Bedrock AgentCore
- RAG via Amazon Bedrock Knowledge Bases over regulatory corpus
- Foundation model: Anthropic Claude (latest available on Bedrock)
- Guardrails via Amazon Bedrock Guardrails for legal disclaimer injection and hallucination prevention
- Backend: Serverless (API Gateway + Lambda, Python 3.12)
- Frontend: Next.js (App Router) deployed on AWS Amplify
- Authentication: Amazon Cognito with enterprise SSO federation (SAML 2.0)
- Data layer: DynamoDB for conversation history, audit trail, and user preferences
- Observability: CloudWatch Logs + X-Ray tracing for all agent invocations
- Infrastructure as Code: AWS CDK (Python)
- Testing: Unit tests (pytest), integration tests against Bedrock endpoints, E2E tests (Playwright)
- Security: IAM least-privilege, encryption at rest (KMS), TLS in transit, VPC endpoints for Bedrock access

## Data Sources (Bedrock Knowledge Base Corpus)

All sources are publicly available under Open Government Licence v3.0 or open access.

### P1 - Core (Demo Ready)
- CAP Code (Non-broadcast, 22 sections): https://www.asa.org.uk/codes-and-rulings/advertising-codes/non-broadcast-code.html
- ASA Rulings (published weekly): https://www.asa.org.uk/codes-and-rulings/rulings.html
- Consumer Rights Act 2015 (full text): https://www.legislation.gov.uk/ukpga/2015/15/contents
- CMA Consumer Enforcement Guidance (CMA58, PDF): https://www.gov.uk/government/publications/consumer-protection-enforcement-guidance-cma58

### P2 - Extended
- Digital Markets, Competition and Consumers Act 2024: https://www.legislation.gov.uk/ukpga/2024/13/contents
- Consumer Protection from Unfair Trading Regulations 2008: https://www.legislation.gov.uk/uksi/2008/1277/contents
- CMA Cases (consumer protection): https://www.gov.uk/cma-cases?case_type=consumer-enforcement

### P3 - Multi-jurisdictional
- EU Omnibus Directive 2019/2161: https://eur-lex.europa.eu/eli/dir/2019/2161/oj
- EU Digital Services Act: https://eur-lex.europa.eu/eli/reg/2022/2065/oj
- FTC Act Section 5 guidance: https://www.ftc.gov/legal-library/browse/statutes/federal-trade-commission-act
