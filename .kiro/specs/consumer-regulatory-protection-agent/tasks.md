# Implementation Plan: Consumer Regulatory Protection Agent

## Overview

This plan implements a Consumer Regulatory Protection Agent on Amazon Bedrock AgentCore using the Strands framework. The implementation follows the priority backlog (P1: Core Compliance Engine, P2: Data & Privacy Crossover, P3: Monitoring & Alerts, P4: Escalation Integration) and builds incrementally from infrastructure through core agent logic, API layer, and frontend.

Backend is Python 3.12 (Lambda, CDK, Hypothesis tests). Frontend is Next.js with TypeScript on AWS Amplify. Infrastructure is AWS CDK (Python).

## Tasks

- [x] 1. Set up project structure and CDK foundation
  - [x] 1.1 Initialize CDK project with Python and create directory structure
    - Create CDK app entry point (`app.py`) and main stack file (`consumer_regulatory_agent_stack.py`)
    - Create directory layout: `cdk/`, `lambdas/`, `lambdas/shared/`, `lambdas/orchestrator/`, `lambdas/async_processor/`, `lambdas/ingestion/`, `frontend/`, `tests/`
    - Add `requirements.txt` for CDK dependencies (`aws-cdk-lib`, `constructs`)
    - Add `pyproject.toml` or `setup.py` for the project
    - _Requirements: 11.1_

  - [x] 1.2 Define VPC construct with private subnets and VPC endpoints
    - Create VPC with 2 AZs, private subnets only (no public subnets needed for Lambda)
    - Add Interface VPC endpoints: `bedrock-runtime`, `bedrock-agent-runtime`, `logs`
    - Add Gateway VPC endpoints: `dynamodb`, `s3`
    - Configure security groups for VPC endpoint access
    - _Requirements: 11.4_

  - [x] 1.3 Define DynamoDB single-table construct with GSI
    - Create `ConsumerRegulatoryAgent` table with PAY_PER_REQUEST billing
    - Define PK (String), SK (String) as composite keys
    - Add GSI1 with GSI1PK and GSI1SK for user-scoped queries
    - Configure KMS customer-managed key encryption
    - Set TTL attribute for audit record expiry (7-year retention)
    - _Requirements: 8.1, 8.4, 11.5_

  - [x] 1.4 Define S3 bucket for regulatory corpus
    - Create S3 bucket with KMS encryption, versioning enabled
    - Configure bucket policy restricting access to Lambda execution roles and Bedrock service
    - Create prefix structure: `uk/`, `eu/`, `us/`
    - _Requirements: 10.1, 11.5_

  - [x] 1.5 Define Cognito User Pool with SAML 2.0 federation
    - Create Cognito User Pool with password policies and MFA configuration
    - Configure SAML 2.0 identity provider placeholder (metadata URL parameterized)
    - Create App Client for Next.js frontend with OAuth 2.0 flows
    - Define custom attributes for `organisation_id`, `permitted_jurisdictions`, `role`
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 1.6 Write CDK assertion tests for infrastructure constructs
    - Verify all expected resources synthesize correctly (Lambda, API GW, DDB, Cognito, VPC endpoints)
    - Verify Lambda runtime is Python 3.12
    - Verify KMS encryption on DynamoDB and S3
    - Verify VPC endpoints for Bedrock services
    - Verify IAM policies follow least-privilege
    - _Requirements: 11.1, 11.2, 11.4, 11.5_

- [x] 2. Checkpoint - Ensure CDK synth succeeds and tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Implement shared data models and utilities
  - [x] 3.1 Create core data model classes
    - Implement all dataclasses from design: `ComplianceQuery`, `ComplianceConcern`, `RiskAssessment`, `AssessmentResult`, `ChecklistItem`, `ChecklistResult`, `EscalationBrief`, `MatterIntakeResult`, `UserProfile`, `RegulatoryUpdate`, `AuditRecord`
    - Implement enums: `RiskLevel`, `UrgencyLevel`, `AssessmentType`
    - Place in `lambdas/shared/models.py`
    - _Requirements: 1.4, 1.5, 2.5, 4.2, 5.2, 8.1_

  - [x] 3.2 Implement input validation module
    - Create `lambdas/shared/validation.py` with validation functions
    - Validate `ComplianceQuery`: reject empty/whitespace campaign_copy, reject empty jurisdictions list
    - Validate jurisdiction codes against supported set (UK, EU, US)
    - Return structured validation errors identifying specific missing fields
    - _Requirements: 1.6, 1.7, 2.6_

  - [ ]* 3.3 Write property test for input validation (Property 3)
    - **Property 3: Input validation rejects invalid queries**
    - Use Hypothesis to generate random strings (empty, whitespace, valid) and random jurisdiction lists
    - Verify that empty/whitespace campaign_copy always returns validation error
    - Verify that empty jurisdictions list always returns validation error
    - **Validates: Requirements 1.6**

  - [x] 3.4 Implement DynamoDB data access layer
    - Create `lambdas/shared/dynamodb_client.py` with single-table access patterns
    - Implement key construction for all entity types (ASSESSMENT#, CONVERSATION#, USER#, ESCALATION#)
    - Implement `put_assessment`, `get_assessment`, `list_user_assessments` (reverse chronological via GSI1)
    - Implement `put_audit_record` (immutable — no update method)
    - Implement `put_conversation_message`, `get_conversation_messages` (chronological order)
    - Implement `put_user_preferences`, `get_user_preferences`
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ]* 3.5 Write property tests for persistence layer (Properties 8, 16, 17)
    - **Property 8: User preferences round-trip** — Store and retrieve UserProfile, verify all fields preserved
    - **Property 16: Conversation history ordering** — Random message sequences return in chronological order
    - **Property 17: Assessment history reverse chronological ordering** — Random assessments return newest first, stable ordering
    - Use Hypothesis strategies for random UserProfile configs, message sequences, and assessment sets
    - **Validates: Requirements 4.4, 8.2, 8.3**

  - [x] 3.6 Implement error handling utilities
    - Create `lambdas/shared/errors.py` with custom exception classes
    - Implement user-friendly error message formatter (no stack traces, no internal service names)
    - Implement structured logging helper (full context: request ID, component, error type, stack trace)
    - Implement retry logic with exponential backoff per design RETRY_CONFIG
    - _Requirements: 9.4_

  - [ ]* 3.7 Write property test for error handling (Property 18)
    - **Property 18: Error response user-friendliness**
    - Generate random error types and contexts
    - Verify user-facing messages never contain stack traces, internal service names, or implementation details
    - Verify log entries contain full error context
    - **Validates: Requirements 9.4**

- [x] 4. Checkpoint - Ensure shared module tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement core compliance agent (P1)
  - [x] 5.1 Implement risk scoring logic
    - Create `lambdas/orchestrator/risk_scorer.py`
    - Implement `score_risk` function: takes list of ComplianceConcern + jurisdiction, returns RiskLevel
    - Scoring rules: Critical if any critical concern, High if any high concern, Medium if any medium, Low otherwise
    - Ensure at least one regulation reference per concern in output
    - _Requirements: 1.4_

  - [ ]* 5.2 Write property test for risk scoring (Property 1)
    - **Property 1: Risk scoring correctness**
    - Generate random lists of ComplianceConcern with varying severities
    - Verify risk level is consistent with scoring rules
    - Verify at least one regulation reference per concern
    - **Validates: Requirements 1.4**

  - [x] 5.3 Implement checklist generator
    - Create `lambdas/orchestrator/checklist_generator.py`
    - Implement `generate_checklist` function: takes product_category + jurisdictions, returns list[ChecklistItem]
    - Ensure every ChecklistItem has: requirement_description, source_regulation, jurisdiction, compliance_action
    - Implement sector-specific logic for food, cosmetics, electronics
    - Implement cross-jurisdiction conflict detection
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ]* 5.4 Write property tests for checklist (Properties 4, 5)
    - **Property 4: Cross-jurisdiction conflict detection** — When known conflicts exist across jurisdictions, they are identified and reported
    - **Property 5: Checklist item structural completeness** — Every ChecklistItem has all four required fields non-empty
    - **Validates: Requirements 2.4, 2.5**

  - [x] 5.5 Implement AgentCore agent with Strands framework
    - Create `lambdas/orchestrator/agent.py` with `ComplianceAgent` class
    - Register tools: `retrieve_regulations`, `score_risk`, `generate_checklist`, `cross_reference_jurisdictions`, `check_vulnerable_consumer_rules`, `validate_substantiation`
    - Configure agent with model ID (Claude), Knowledge Base ID, and Guardrail ID (from environment variables)
    - Implement `retrieve_regulations` tool: query Knowledge Base with jurisdiction and topic metadata filters
    - Implement `cross_reference_jurisdictions` tool for multi-jurisdiction conflict detection
    - Implement `check_vulnerable_consumer_rules` tool for enhanced scrutiny
    - Implement `validate_substantiation` tool for comparative claims
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.4_

  - [x] 5.6 Implement guardrails integration
    - Create `lambdas/orchestrator/guardrails.py`
    - Implement `apply_guardrails` function: calls Bedrock Guardrails API on agent response
    - Inject legal disclaimer prefix on every response
    - Validate citations against Knowledge Base (contextual grounding check)
    - Remove unverified citations and flag gaps to user
    - Block definitive legal conclusion phrases
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 5.7 Write property tests for guardrails (Properties 12, 13, 14)
    - **Property 12: Legal disclaimer injection** — Every response contains the legal disclaimer
    - **Property 13: Citation integrity** — Citations not in Knowledge Base are removed, gap flagged
    - **Property 14: Definitive legal conclusion prevention** — No definitive phrases in output
    - Use Hypothesis to generate random response texts with/without definitive phrases and random citation sets
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

  - [x] 5.8 Implement jurisdiction access control
    - Create `lambdas/shared/auth.py`
    - Implement `check_jurisdiction_access`: verify requested jurisdictions are in user's `permitted_jurisdictions`
    - Return 403 with user-friendly message for unauthorized jurisdiction access
    - _Requirements: 6.2, 6.3_

  - [ ]* 5.9 Write property test for access control (Property 11)
    - **Property 11: Jurisdiction-based access control enforcement**
    - Generate random user profiles with permitted_jurisdictions and random access attempts
    - Verify access granted iff jurisdiction in permitted list
    - Verify unauthorized access returns authorisation error
    - **Validates: Requirements 6.3**

- [x] 6. Checkpoint - Ensure core agent logic tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement API Gateway and Lambda orchestrator
  - [x] 7.1 Define API Gateway REST API in CDK
    - Create REST API with Cognito authorizer
    - Define all routes from design: `/v1/assessments/campaign`, `/v1/assessments/product`, `/v1/assessments/data`, `/v1/assessments/{id}`, `/v1/assessments`, `/v1/escalations`, `/v1/escalations/{id}`, `/v1/conversations/{id}`, `/v1/conversations/{id}/messages`, `/v1/monitoring/alerts`, `/v1/monitoring/preferences`, `/v1/health`
    - Configure CORS for Amplify frontend domain
    - Add request validation models
    - _Requirements: 11.1, 11.2_

  - [x] 7.2 Implement orchestrator Lambda handler
    - Create `lambdas/orchestrator/handler.py` with route dispatch
    - Implement `POST /v1/assessments/campaign` handler: validate input → create audit record (PENDING) → invoke agent → apply guardrails → update audit record (COMPLETED) → return response
    - Implement `POST /v1/assessments/product` handler for checklist generation
    - Implement `GET /v1/assessments/{id}` and `GET /v1/assessments` (paginated, reverse chronological)
    - Implement `GET /v1/conversations/{id}` and `POST /v1/conversations/{id}/messages`
    - Implement `GET /v1/health` endpoint (validate connectivity to Bedrock, DDB, KB)
    - _Requirements: 1.1, 1.5, 2.1, 8.1, 8.2, 8.3, 9.5_

  - [ ]* 7.3 Write property test for assessment output (Property 2)
    - **Property 2: Assessment output structural completeness**
    - Generate valid ComplianceQuery inputs with non-empty campaign_copy and jurisdictions
    - Verify response contains: risk level per jurisdiction, at least one citation per jurisdiction, concerns or "no concerns" indicator, recommended next steps
    - **Validates: Requirements 1.5**

  - [x] 7.4 Implement audit trail persistence
    - Wire audit record creation into orchestrator flow
    - Create immutable audit records with: full query, full response, risk assessment per jurisdiction, timestamp, user ID, model ID
    - Configure TTL for 7-year retention (epoch seconds)
    - _Requirements: 8.1, 8.4_

  - [ ]* 7.5 Write property test for audit completeness (Property 15)
    - **Property 15: Audit record persistence completeness**
    - For any processed query, verify audit record exists with all required fields
    - Verify immutability (no update method exposed)
    - **Validates: Requirements 8.1**

  - [x] 7.6 Implement observability (structured logging and X-Ray tracing)
    - Add AWS X-Ray SDK instrumentation to Lambda handler
    - Emit structured JSON logs: request ID, user ID, query type, jurisdictions, response time, risk levels
    - Add CloudWatch metric for latency threshold (>30s alarm)
    - Propagate trace IDs across API Gateway → Lambda → Bedrock → DDB
    - _Requirements: 9.1, 9.2, 9.3, 9.4_

  - [x] 7.7 Define Lambda functions in CDK with VPC and IAM
    - Create orchestrator Lambda (Python 3.12, VPC, 512MB memory, 60s timeout)
    - Create async processor Lambda (Python 3.12, VPC, 256MB memory, 300s timeout)
    - Create ingestion Lambda (Python 3.12, VPC, 256MB memory, 300s timeout)
    - Configure least-privilege IAM roles: Bedrock invoke, DDB read/write, KB retrieve, S3 read, CloudWatch logs
    - Package shared layer with common dependencies
    - _Requirements: 11.3, 11.4, 11.5_

- [ ] 8. Checkpoint - Ensure API and orchestrator tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement data & privacy crossover (P2)
  - [ ] 9.1 Implement data compliance assessment handler
    - Implement `POST /v1/assessments/data` handler in orchestrator
    - Assess against both consumer protection and data privacy regulations
    - Evaluate consent mechanisms against "clear and prominent" standards
    - Identify obligations beyond data privacy law alone
    - Present consolidated view of overlapping requirements
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 9.2 Write property test for missing consent detection (Property 6)
    - **Property 6: Missing consent mechanism detection**
    - Generate data collection queries without consent mechanism descriptions
    - Verify system flags absence as gap and returns non-empty consent requirements per jurisdiction
    - **Validates: Requirements 3.5**

- [ ] 10. Implement monitoring & alerts (P3)
  - [ ] 10.1 Implement monitoring service
    - Create `lambdas/async_processor/monitoring.py` with `MonitoringService` class
    - Implement `check_regulatory_updates`: detect changes in monitored jurisdictions
    - Implement `generate_impact_summary`: produce sector-relevant impact summaries
    - Implement `categorise_urgency`: apply deadline rules (≤30d → Immediate, ≤90d → Upcoming, else → Awareness)
    - Implement `send_notification`: deliver alerts via configured channel
    - _Requirements: 4.1, 4.2, 4.3, 4.5_

  - [ ]* 10.2 Write property test for urgency categorisation (Property 7)
    - **Property 7: Urgency categorisation follows deadline rules**
    - Generate random RegulatoryUpdate with various compliance_deadline dates
    - Verify: ≤30 days → "Immediate Action Required", ≤90 days → "Upcoming Deadline", >90 days or no deadline → "Awareness Only"
    - **Validates: Requirements 4.2**

  - [ ] 10.3 Implement monitoring preferences API
    - Implement `PUT /v1/monitoring/preferences` handler: store user sector, jurisdictions, notification prefs
    - Implement `GET /v1/monitoring/alerts` handler: retrieve user's alerts
    - _Requirements: 4.4_

  - [ ] 10.4 Define EventBridge scheduler and SQS queue in CDK
    - Create EventBridge rule to trigger async processor Lambda on schedule (daily)
    - Create SQS queue for monitoring events with DLQ
    - Wire async processor Lambda to SQS trigger
    - _Requirements: 4.1, 4.5_

- [ ] 11. Implement escalation integration (P4)
  - [ ] 11.1 Implement escalation service
    - Create `lambdas/orchestrator/escalation.py` with `EscalationService` class
    - Implement `package_brief`: assemble original query, AI analysis, regulation references, risk summary, audit trail
    - Implement `create_matter_intake`: create matter in practice management system (with circuit breaker)
    - Implement `get_escalation_status`: retrieve matter status
    - Implement circuit breaker pattern (5 failures in 60s → open, 30s cooldown → half-open)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ]* 11.2 Write property tests for escalation (Properties 9, 10)
    - **Property 9: Escalation option presence** — High/Critical risk → escalation option present; Low/Medium only → not presented
    - **Property 10: Escalation brief completeness** — Brief contains original query, full assessment, all citations, risk summary, non-empty audit trail
    - **Validates: Requirements 5.1, 5.2, 5.6**

  - [ ] 11.3 Implement escalation API endpoints
    - Implement `POST /v1/escalations` handler: validate assessment has High/Critical risk, package brief, create matter intake
    - Implement `GET /v1/escalations/{id}` handler: retrieve escalation status
    - Handle escalation service failures gracefully (retain brief, offer alternatives)
    - _Requirements: 5.3, 5.4, 5.5_

- [ ] 12. Checkpoint - Ensure P2-P4 feature tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Implement Knowledge Base configuration and ingestion
  - [ ] 13.1 Define Bedrock Knowledge Base in CDK
    - Create Knowledge Base with Amazon Titan Embeddings V2
    - Configure OpenSearch Serverless collection as vector store
    - Set hierarchical chunking strategy (parent: 1500 tokens, child: 300 tokens)
    - Define metadata filtering schema: jurisdiction, document_type, effective_date, sector
    - Connect S3 regulatory corpus bucket as data source
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

  - [ ] 13.2 Implement ingestion Lambda
    - Create `lambdas/ingestion/handler.py`
    - Support PDF, HTML, and plain text document formats
    - Extract and attach metadata on ingestion: source_url, jurisdiction, document_type, effective_date, last_updated
    - Trigger Knowledge Base sync after upload
    - Log failures with source identifier and reason, alert knowledge manager via SNS
    - _Requirements: 10.1, 10.2, 10.3, 10.5_

  - [ ]* 13.3 Write property test for document metadata (Property 19)
    - **Property 19: Document metadata completeness on ingestion**
    - Generate random document metadata sets
    - Verify all required fields (source_url, jurisdiction, document_type, effective_date, last_updated) are non-null and non-empty
    - **Validates: Requirements 10.2**

  - [ ] 13.4 Define Bedrock Guardrails in CDK
    - Create Guardrails configuration with content filter (HIGH threshold)
    - Add word filter for definitive legal conclusion phrases
    - Enable contextual grounding check (0.7 threshold)
    - Configure managed word list (profanity filter)
    - Set custom response with legal disclaimer prefix
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 14. Implement Next.js frontend
  - [ ] 14.1 Initialize Next.js App Router project with TypeScript
    - Create Next.js project in `frontend/` directory with App Router
    - Configure TypeScript, ESLint, Tailwind CSS
    - Set up Amplify deployment configuration (`amplify.yml`)
    - Configure environment variables for API endpoint and Cognito
    - _Requirements: 11.1_

  - [ ] 14.2 Implement authentication flow with Cognito
    - Install and configure `@aws-amplify/auth` for Cognito integration
    - Implement SSO login page with SAML 2.0 redirect
    - Create auth context provider with session management
    - Implement token refresh and session expiry handling
    - Protect all routes except login with auth middleware
    - _Requirements: 6.1, 6.2, 6.4_

  - [ ] 14.3 Implement dashboard and assessment pages
    - Create `/` dashboard: recent assessments, active alerts summary
    - Create `/assess/campaign` page: campaign copy input, jurisdiction selector, submit flow, results display
    - Create `/assess/product` page: product category input, jurisdiction selector, checklist display
    - Create `/assess/data` page: data collection description input, consent mechanism fields, results display
    - Display risk levels with colour coding (Low=green, Medium=amber, High=orange, Critical=red)
    - Show regulation citations with expandable details
    - _Requirements: 1.1, 1.5, 2.1, 2.5, 3.1_

  - [ ] 14.4 Implement history, escalation, and settings pages
    - Create `/history` page: paginated assessment list (reverse chronological), filter by type/jurisdiction
    - Create `/escalation/[id]` page: escalation status, matter reference, timeline
    - Create `/settings` page: monitoring preferences (sector, jurisdictions, notification channel)
    - Create conversation view within assessment detail for follow-up queries
    - _Requirements: 4.4, 5.4, 8.3_

  - [ ] 14.5 Implement API client and error handling
    - Create typed API client for all backend endpoints
    - Implement loading states, error boundaries, and retry logic
    - Display user-friendly error messages (no technical details)
    - Handle 401 (redirect to login), 403 (jurisdiction access denied), 504 (timeout with retry suggestion)
    - _Requirements: 6.4, 9.4_

- [ ] 15. Checkpoint - Ensure frontend builds and CDK synth succeeds
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Wire CDK stack outputs and final integration
  - [ ] 16.1 Complete CDK stack with all resource connections
    - Wire API Gateway → Lambda integrations with proper IAM
    - Connect Lambda to VPC with security groups
    - Add CDK stack outputs: API endpoint URL, Cognito domain, Amplify app URL
    - Configure Lambda environment variables (table name, KB ID, guardrail ID, model ID)
    - _Requirements: 11.2, 11.6_

  - [ ] 16.2 Add CDK stack for Amplify frontend deployment
    - Define Amplify app resource pointing to frontend directory
    - Configure build settings and environment variables
    - Set up custom domain (if applicable)
    - _Requirements: 11.1_

  - [ ]* 16.3 Write integration tests for end-to-end assessment flow
    - Test campaign compliance: submit query → receive structured assessment with citations
    - Test product checklist: submit product → receive jurisdiction-specific checklist
    - Test escalation: high-risk assessment → escalation → matter intake confirmation
    - Test auth flow: unauthenticated request → 401, unauthorized jurisdiction → 403
    - _Requirements: 1.1, 2.1, 5.3, 6.3_

- [ ] 17. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at each major milestone
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Priority order: P1 (tasks 5) → P2 (task 9) → P3 (task 10) → P4 (task 11)
- Infrastructure (tasks 1, 7.1, 7.7, 13, 16) can be developed in parallel with application logic
