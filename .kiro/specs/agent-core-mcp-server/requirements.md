# Requirements Document

## Introduction

This project delivers two demo implementations showing how Amazon Bedrock AgentCore can serve as the MCP hosting and gateway layer for a Data & Analytics domain. Each demo deploys an open-source AWS Labs MCP server (S3 Tables and Redshift) onto AgentCore Runtime, registers it in AgentCore Gateway, and connects a Bedrock Agent to query data via natural language. The combined demo shows both servers behind a single unified AgentCore Gateway, enabling conversational analytics across S3 Tables (Apache Iceberg) and Redshift data sources.

**Context:** These demos map to AnyCompany's D&A AI Reference Architecture where Amazon Bedrock is the central AI platform, S3 and Redshift are primary data sources, AgentCore provides agent lifecycle and governance, and MCP is used for agent-to-system interactions.

**Target Audience:** Derek O'Harrow, Jamie West, Nadia (data science lead)

## Glossary

- **AgentCore_Runtime**: Amazon Bedrock AgentCore Runtime — the serverless compute layer that hosts MCP server containers with session isolation (microVM), auto-scaling, and managed lifecycle
- **AgentCore_Gateway**: Amazon Bedrock AgentCore Gateway — the routing and discovery layer that fronts MCP server runtimes with authentication, tool discovery, and observability
- **MCP_Server**: A Model Context Protocol server that exposes tools (capabilities) for an AI agent to invoke
- **S3_Tables_MCP_Server**: The `awslabs.s3-tables-mcp-server` — an MCP server for discovering, exploring, and querying Apache Iceberg tables stored in S3 Tables
- **Redshift_MCP_Server**: The `awslabs.redshift-mcp-server` — an MCP server for discovering Redshift clusters/workgroups, exploring schemas, and executing analytical SQL queries
- **Bedrock_Agent**: An Amazon Bedrock Agent connected to the AgentCore Gateway that interprets natural language and invokes appropriate MCP tools
- **Gateway_Target**: A registered MCP server runtime within the AgentCore Gateway, discoverable by agents via tool descriptions
- **ECR_Repository**: Amazon Elastic Container Registry repository used to store MCP server Docker images
- **D&A_Domain**: The Data & Analytics domain — the business context for these demos covering customer transactions, analytics outputs, and risk scores
- **Demo_Operator**: The technical person deploying and demonstrating the AgentCore MCP setup

## Requirements

### Requirement 1: Containerise and Deploy S3 Tables MCP Server to AgentCore Runtime

**User Story:** As a Demo_Operator, I want to package the S3 Tables MCP Server as a container and deploy it to AgentCore Runtime, so that it runs serverlessly without managing infrastructure.

#### Acceptance Criteria

1. THE Demo_Operator SHALL clone the `awslabs/mcp` repository and build a Docker image from `src/s3-tables-mcp-server`
2. THE Docker image SHALL be pushed to an ECR_Repository in the `eu-west-1` region
3. THE AgentCore_Runtime SHALL be created with the ECR image URI, `AWS_REGION=eu-west-1` environment variable, and an IAM role with `s3tables:*`, `s3:GetObject`, and `bedrock-agentcore:*` permissions
4. THE AgentCore_Runtime SHALL use stateless HTTP protocol configuration for the MCP server
5. THE AgentCore_Runtime SHALL confirm successful creation by returning a runtime ARN

### Requirement 2: Containerise and Deploy Redshift MCP Server to AgentCore Runtime

**User Story:** As a Demo_Operator, I want to package the Redshift MCP Server as a container and deploy it to AgentCore Runtime, so that it runs serverlessly with VPC connectivity to Redshift clusters.

#### Acceptance Criteria

1. THE Demo_Operator SHALL build a Docker image from `src/redshift-mcp-server` and push it to ECR in `eu-west-1`
2. THE AgentCore_Runtime SHALL be created with VPC configuration specifying subnet IDs and security group IDs that allow connectivity to Redshift
3. THE AgentCore_Runtime SHALL use an IAM role with permissions: `redshift:DescribeClusters`, `redshift-serverless:ListWorkgroups`, `redshift-data:ExecuteStatement`, `redshift-data:GetStatementResult`, `redshift-data:DescribeStatement`
4. THE AgentCore_Runtime SHALL use stateless HTTP protocol configuration for the MCP server
5. THE AgentCore_Runtime SHALL confirm successful creation by returning a runtime ARN

### Requirement 3: Create AgentCore Gateway with Authentication

**User Story:** As a Demo_Operator, I want to create an AgentCore Gateway with Cognito or Entra ID JWT authentication, so that MCP tool access is governed and auditable.

#### Acceptance Criteria

1. THE AgentCore_Gateway SHALL be created with a descriptive name (`da-analytics-gateway`) and description referencing the D&A domain
2. THE AgentCore_Gateway SHALL be configured with a custom JWT authorizer specifying allowed clients, allowed audiences, and an issuer URL (Cognito or Entra ID)
3. THE AgentCore_Gateway SHALL return a gateway ID upon successful creation
4. THE AgentCore_Gateway SHALL provide a single authentication endpoint for all registered MCP server targets

### Requirement 4: Register S3 Tables MCP Server as Gateway Target

**User Story:** As a Demo_Operator, I want to register the S3 Tables MCP Server as a target in the AgentCore Gateway, so that agents can discover and invoke S3 Tables tools through the gateway.

#### Acceptance Criteria

1. THE S3_Tables_MCP_Server SHALL be registered as a gateway target with name `s3-tables` and a description referencing discovery and query capabilities
2. THE gateway target SHALL reference the S3 Tables runtime ARN in its target configuration
3. AFTER registration, THE Demo_Operator SHALL synchronize gateway targets to trigger tool discovery
4. AFTER synchronization, THE AgentCore_Gateway SHALL expose S3 Tables tools (`list_table_buckets`, `list_namespaces`, `list_tables`, `get_table_metadata`, `query_table`) for agent invocation

### Requirement 5: Register Redshift MCP Server as Gateway Target

**User Story:** As a Demo_Operator, I want to register the Redshift MCP Server as an additional target in the same AgentCore Gateway, so that agents can access both S3 Tables and Redshift tools from a single endpoint.

#### Acceptance Criteria

1. THE Redshift_MCP_Server SHALL be registered as a gateway target with name `redshift-analytics` on the same gateway as S3 Tables
2. THE gateway target SHALL reference the Redshift runtime ARN in its target configuration
3. AFTER registration, THE Demo_Operator SHALL re-synchronize gateway targets to discover Redshift tools
4. AFTER synchronization, THE AgentCore_Gateway SHALL expose Redshift tools (`list_clusters`, `list_databases`, `list_schemas`, `list_tables`, `list_columns`, `execute_query`) alongside the existing S3 Tables tools

### Requirement 6: Connect a Bedrock Agent to the AgentCore Gateway

**User Story:** As a Demo_Operator, I want to create a Bedrock Agent connected to the AgentCore Gateway, so that end users can interact with D&A data sources via natural language.

#### Acceptance Criteria

1. THE Bedrock_Agent SHALL be created with agent name `da-analytics-agent` and foundation model `anthropic.claude-sonnet-4-20250514`
2. THE Bedrock_Agent SHALL be configured with an AgentCore Gateway config referencing the gateway ID
3. THE Bedrock_Agent SHALL have an instruction prompt defining it as a data analytics assistant for the D&A team, directing it to use available tools to discover and query data sources and explain findings
4. THE Bedrock_Agent SHALL automatically discover all tools registered in the gateway (both S3 Tables and Redshift)

### Requirement 7: S3 Tables Discovery and Query via Natural Language

**User Story:** As a D&A team member, I want to ask natural language questions about my S3 Tables data, so that I can discover table structure and run analytical queries without writing code.

#### Acceptance Criteria

1. WHEN a user asks "What tables are available?", THE Bedrock_Agent SHALL invoke `list_table_buckets`, `list_namespaces`, and `list_tables` tools and return a summary of available data
2. WHEN a user asks an analytical question (e.g., "Show me top 5 customers by transaction value"), THE Bedrock_Agent SHALL invoke `query_table` with appropriate SQL and return formatted results
3. THE Bedrock_Agent SHALL explain what data was found in natural language alongside any results
4. THE S3_Tables_MCP_Server SHALL operate in read-only mode by default, rejecting write operations unless explicitly opted in

### Requirement 8: Redshift Discovery and Query via Natural Language

**User Story:** As a D&A team member, I want to ask natural language questions about my Redshift data, so that I can explore clusters, schemas, and run SQL queries conversationally.

#### Acceptance Criteria

1. WHEN a user asks "Explore my Redshift environment", THE Bedrock_Agent SHALL invoke `list_clusters`, `list_databases`, `list_schemas`, and `list_tables` tools and return a summary
2. WHEN a user asks an analytical question, THE Bedrock_Agent SHALL invoke `execute_query` with read-only SQL via the Redshift Data API and return formatted results
3. THE Redshift_MCP_Server SHALL reject any write SQL (INSERT, UPDATE, DELETE, DDL) — only single-statement read-only queries are permitted
4. THE Bedrock_Agent SHALL discover both provisioned clusters and serverless workgroups automatically

### Requirement 9: Cross-Source Analytics via Unified Gateway

**User Story:** As a D&A team member, I want to ask questions that span both S3 Tables and Redshift, so that I can compare and correlate data across sources in a single conversation.

#### Acceptance Criteria

1. WHEN a user asks a question requiring data from both sources (e.g., "Compare customer counts between S3 Tables and Redshift"), THE Bedrock_Agent SHALL invoke tools from both S3 Tables and Redshift MCP servers and synthesise the results
2. THE AgentCore_Gateway SHALL serve both tool sets from a single endpoint without the user needing to specify which data source to query
3. THE Bedrock_Agent SHALL select the appropriate tool based on the user's question and available tool descriptions (semantic tool search)

### Requirement 10: Security and Governance

**User Story:** As a Demo_Operator, I want the demo to demonstrate production-grade security and governance features, so that stakeholders understand AgentCore replaces custom auth and audit infrastructure.

#### Acceptance Criteria

1. THE AgentCore_Runtime SHALL handle IAM authentication via role assumption — no credentials SHALL be exposed to the agent or end user
2. THE AgentCore_Gateway SHALL enforce JWT-based authentication on all tool invocations
3. ALL tool invocations SHALL be logged via CloudTrail for audit purposes
4. THE AgentCore_Runtime SHALL provide session isolation per user via microVM technology
5. THE S3_Tables_MCP_Server SHALL default to read-only mode; write operations require explicit `--allow-write` configuration

### Requirement 11: Prepare Sample Data

**User Story:** As a Demo_Operator, I want sample data available in both S3 Tables and Redshift, so that the demo produces meaningful query results.

#### Acceptance Criteria

1. THE S3 Tables bucket SHALL contain at least 3 namespaces (e.g., `customers`, `transactions`, `risk_scores`) with representative Iceberg tables
2. THE Redshift cluster/workgroup SHALL contain sample data accessible via the Data API (e.g., `sample_data_dev.tickit` or custom loaded data)
3. THE sample data SHALL be sufficient to demonstrate discovery queries (list operations) and analytical queries (aggregations, top-N, filters)

### Requirement 12: Demo Script and Talking Points

**User Story:** As a Demo_Operator, I want a prepared demo script with talking points, so that I can deliver a compelling demonstration to the target audience.

#### Acceptance Criteria

1. THE demo script SHALL include an opening that establishes context (AnyCompany D&A architecture, Derek's MCP diagram)
2. THE demo script SHALL walk through S3 Tables discovery, Redshift discovery, and cross-source comparison in sequence
3. THE demo script SHALL include talking points highlighting: no credentials exposed, read-only by default, serverless auto-scaling, replaces 3 components in Derek's diagram, and CloudTrail audit trail
4. THE demo script SHALL include a mapping table showing which components in Derek's architecture diagram are replaced or enhanced by AgentCore
