# MCP Server Demo: AgentCore Gateway for Data & Analytics

## Overview

This spec defines two demo implementations showing how **Amazon Bedrock AgentCore** can serve as the MCP hosting and gateway layer for a Data & Analytics domain. Each demo deploys an open-source AWS Labs MCP server onto AgentCore Runtime, registers it in AgentCore Gateway, and connects a Bedrock Agent to query data via natural language.

**Context:** These demos map directly to AnyCompany's D&A AI Reference Architecture where:

- Amazon Bedrock is the central AI platform
- S3 and Redshift are primary data sources
- AgentCore provides agent lifecycle and governance
- MCP is used for agent-to-system interactions (not raw data access, but AI outputs/intents)

**Target Audience:** Derek O'Harrow, Jamie West, Nadia (data science lead)

---

## Section 1: S3 Tables MCP Server on AgentCore

### 1.1 Objective

Deploy the `awslabs.s3-tables-mcp-server` onto AgentCore Runtime and front it with AgentCore Gateway, demonstrating how an AI agent can discover, explore, and query Apache Iceberg tables stored in S3 Tables — without direct database credentials or custom integration code.

### 1.2 Why S3 Tables

- S3 is AnyCompany's primary data layer in the D&A domain (training data, AI outputs, curated analytics)
- S3 Tables (Apache Iceberg format) is the modern analytical table format for lakehouse architectures
- Demonstrates "conversational analytics" — natural language access to structured data
- Works with any Iceberg-compatible engine (Athena, Redshift, Spark)

### 1.3 MCP Server Capabilities

| Tool | Description | Mode |
| --- | --- | --- |
| `list_table_buckets` | List all S3 Table Buckets | Read |
| `list_namespaces` | List namespaces within a table bucket | Read |
| `list_tables` | List tables within a namespace | Read |
| `get_table_metadata` | View schema, storage info, maintenance config | Read |
| `query_table` | Run read-only SQL against S3 Tables (via Daft/PyIceberg) | Read |
| `create_table_bucket` | Create new table bucket | Write (opt-in) |
| `create_table_from_csv` | Generate S3 Table from CSV file in S3 | Write (opt-in) |
| `append_rows` | Append data rows to an Iceberg table | Write (opt-in) |
| `get_bucket_metadata` | Discover metadata via S3 Metadata Table | Read |
| `get_maintenance_config` | Retrieve table/bucket maintenance settings | Read |
| `get_resource_policy` | Access resource policies for tables/buckets | Read |

### 1.4 Architecture

```
User / Agent Client
        │
        ▼
┌──────────────────────────────┐
│  AgentCore Gateway           │
│  • Tool discovery            │
│  • Auth (Cognito / Entra ID) │
│  • Routing & observability   │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  AgentCore Runtime           │
│  • s3-tables-mcp-server      │
│  • Serverless (auto-scale)   │
│  • Session isolation (microVM)│
│  • Read-only mode by default │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  S3 Tables (Iceberg)         │
│  • Table Buckets             │
│  • Namespaces                │
│  • Managed Iceberg tables    │
└──────────────────────────────┘

```

### 1.5 Implementation Steps

Step 1: Prerequisites

- AWS account with Bedrock AgentCore access
- S3 Tables bucket with sample data (e.g. customer transactions, analytics outputs)
- Python 3.10+, `uv` installed
- IAM role with permissions: `s3tables:*`, `s3:GetObject`, `bedrock-agentcore:*`

Step 2: Containerise the MCP Server

```bash
# Clone the awslabs MCP repo
git clone https://github.com/awslabs/mcp.git
cd mcp/src/s3-tables-mcp-server

# Build Docker image
docker build -t s3-tables-mcp-server:latest .

# Push to ECR
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.eu-west-1.amazonaws.com
docker tag s3-tables-mcp-server:latest <account>.dkr.ecr.eu-west-1.amazonaws.com/s3-tables-mcp-server:latest
docker push <account>.dkr.ecr.eu-west-1.amazonaws.com/s3-tables-mcp-server:latest

```

Step 3: Deploy to AgentCore Runtime

```python
import boto3

client = boto3.client('bedrock-agentcore-control')

# Create MCP server runtime
response = client.create_runtime(
    name='s3-tables-mcp-server',
    description='S3 Tables MCP Server for D&A domain',
    containerConfig={
        'imageUri': '<account>.dkr.ecr.eu-west-1.amazonaws.com/s3-tables-mcp-server:latest',
        'environmentVariables': {
            'AWS_REGION': 'eu-west-1',
            'FASTMCP_LOG_LEVEL': 'INFO'
        }
    },
    protocolConfig={
        'mcpConfig': {
            'statelessHttp': True  # Recommended for basic MCP servers
        }
    },
    roleArn='arn:aws:iam::<account>:role/AgentCoreS3TablesRole'
)
runtime_arn = response['runtimeArn']
print(f'Runtime created: {runtime_arn}')

```

Step 4: Create AgentCore Gateway and Register Target

```python
# Create Gateway with Cognito auth (or Entra ID custom JWT)
gateway_response = client.create_gateway(
    name='da-analytics-gateway',
    description='D&A Domain MCP Gateway for analytics tools',
    authorizationConfig={
        'customJWTAuthorizer': {
            'allowedClients': ['<cognito_client_id>'],
            'allowedAudiences': ['<cognito_pool_arn>'],
            'issuerUrl': 'https://cognito-idp.eu-west-1.amazonaws.com/<pool_id>'
        }
    }
)
gateway_id = gateway_response['gatewayId']

# Add S3 Tables MCP Server as target
client.create_gateway_target(
    gatewayId=gateway_id,
    name='s3-tables',
    description='S3 Tables discovery and query tools',
    targetConfig={
        'mcpServerTarget': {
            'runtimeArn': runtime_arn
        }
    }
)

# Synchronize to discover tools
client.synchronize_gateway_targets(gatewayId=gateway_id)

```

Step 5: Connect Bedrock Agent to Gateway

```python
bedrock_client = boto3.client('bedrock-agent')

# Create agent pointing at the gateway
agent_response = bedrock_client.create_agent(
    agentName='da-analytics-agent',
    foundationModel='anthropic.claude-sonnet-4-20250514',
    instruction='You are a data analytics assistant for the D&A team. Use the available tools to discover and query S3 Tables. Always explain what data you found.',
    agentCoreGatewayConfig={
        'gatewayId': gateway_id
    }
)

```

Step 6: Test

```
User: "What tables are available in our analytics bucket?"
Agent: → calls list_table_buckets → list_namespaces → list_tables
Agent: "I found 3 namespaces in the analytics bucket: customers, transactions, and risk_scores..."

User: "Show me the top 5 customers by transaction value this month"
Agent: → calls query_table with SQL
Agent: "Here are the top 5 customers by spend in July 2026: ..."

```

### 1.6 Demo Talking Points

- **No credentials exposed to the agent** — AgentCore handles IAM auth via role assumption
- **Read-only by default** — write operations require explicit `--allow-write` flag
- **Serverless** — no ECS/EKS/Fargate cluster to manage; auto-scales to zero
- **Replaces 3 components in Derek's diagram** — Fargate MCP Servers + MCP Auth Service + Load Balancer
- **Audit trail** — all tool invocations logged via CloudTrail

---

## Section 2: Redshift MCP Server on AgentCore

### 2.1 Objective

Deploy the `awslabs.redshift-mcp-server` onto AgentCore Runtime and front it with AgentCore Gateway, demonstrating how an AI agent can discover Redshift clusters/workgroups, explore schemas, and execute analytical SQL queries — all via natural language through a governed MCP interface.

### 2.2 Why Redshift

- Redshift is a core analytical engine in many D&A environments
- Demonstrates cross-service tool composition (S3 Tables + Redshift behind same Gateway)
- Shows multi-cluster/workgroup discovery (provisioned + serverless)
- Relevant for Nadia's data science team running analytical queries

### 2.3 MCP Server Capabilities

| Tool | Description | Mode |
| --- | --- | --- |
| `list_clusters` | Discover provisioned clusters and serverless workgroups | Read |
| `list_databases` | List databases in a cluster/workgroup | Read |
| `list_schemas` | List schemas in a database | Read |
| `list_tables` | List tables, views, and external tables in a schema | Read |
| `list_columns` | Get column metadata (types, nullability, constraints) | Read |
| `execute_query` | Run read-only SQL via Redshift Data API | Read |

**Key constraint:** Single-statement read-only queries only. Write operations (INSERT, UPDATE, DELETE, DDL) are rejected by the MCP server.

### 2.4 Architecture

```
User / Agent Client
        │
        ▼
┌──────────────────────────────┐
│  AgentCore Gateway           │
│  • Unified tool discovery    │
│  • S3 Tables + Redshift tools│
│  • Single auth endpoint      │
└──────────────┬───────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
┌──────────────┐ ┌──────────────┐
│ AgentCore    │ │ AgentCore    │
│ Runtime:     │ │ Runtime:     │
│ S3 Tables    │ │ Redshift     │
│ MCP Server   │ │ MCP Server   │
└──────┬───────┘ └──────┬───────┘
       │                │
       ▼                ▼
┌──────────────┐ ┌──────────────┐
│ S3 Tables    │ │ Redshift     │
│ (Iceberg)    │ │ (Provisioned │
│              │ │  + Serverless)│
└──────────────┘ └──────────────┘

```

### 2.5 Implementation Steps

Step 1: Prerequisites

- Redshift cluster or serverless workgroup with sample data (e.g. `sample_data_dev.tickit`)
- IAM role with permissions: `redshift:DescribeClusters`, `redshift-serverless:ListWorkgroups`, `redshift-data:ExecuteStatement`, `redshift-data:GetStatementResult`, `redshift-data:DescribeStatement`
- Network connectivity: AgentCore Runtime needs access to Redshift (VPC endpoint or public access)

Step 2: Containerise the MCP Server

```bash
cd mcp/src/redshift-mcp-server
docker build -t redshift-mcp-server:latest .

aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.eu-west-1.amazonaws.com
docker tag redshift-mcp-server:latest <account>.dkr.ecr.eu-west-1.amazonaws.com/redshift-mcp-server:latest
docker push <account>.dkr.ecr.eu-west-1.amazonaws.com/redshift-mcp-server:latest

```

Step 3: Deploy to AgentCore Runtime

```python
response = client.create_runtime(
    name='redshift-mcp-server',
    description='Redshift MCP Server for D&A analytics queries',
    containerConfig={
        'imageUri': '<account>.dkr.ecr.eu-west-1.amazonaws.com/redshift-mcp-server:latest',
        'environmentVariables': {
            'AWS_REGION': 'eu-west-1',
            'FASTMCP_LOG_LEVEL': 'INFO'
        }
    },
    protocolConfig={
        'mcpConfig': {
            'statelessHttp': True
        }
    },
    networkConfig={
        'vpcConfig': {
            'subnetIds': ['subnet-xxx', 'subnet-yyy'],
            'securityGroupIds': ['sg-redshift-access']
        }
    },
    roleArn='arn:aws:iam::<account>:role/AgentCoreRedshiftRole'
)
redshift_runtime_arn = response['runtimeArn']

```

Step 4: Register as Additional Target in Gateway

```python
# Add Redshift MCP Server as second target to same gateway
client.create_gateway_target(
    gatewayId=gateway_id,  # Same gateway as S3 Tables
    name='redshift-analytics',
    description='Redshift cluster discovery and SQL query tools',
    targetConfig={
        'mcpServerTarget': {
            'runtimeArn': redshift_runtime_arn
        }
    }
)

# Re-synchronize to discover new tools
client.synchronize_gateway_targets(gatewayId=gateway_id)

```

Step 5: Test (Agent Now Has Both S3 Tables + Redshift Tools)

```
User: "Explore my Redshift environment"
Agent: → calls list_clusters → list_databases → list_schemas → list_tables
Agent: "I found 2 clusters and 1 serverless workgroup. The analytics cluster has 4 databases..."

User: "What were the top 10 sales last month?"
Agent: → calls list_tables (finds sales table) → execute_query
Agent: "Here are the top 10 sales from July 2026: ..."

User: "Now compare that with the S3 Tables data in the transactions namespace"
Agent: → calls S3 Tables query_table tool
Agent: "Cross-referencing: the S3 Tables transactions data shows..."

```

### 2.6 VPC / Network Considerations

Unlike S3 Tables (public API), Redshift typically sits in a private VPC. AgentCore Runtime supports VPC configuration:

- **Private connectivity:** AgentCore Runtime runs inside your VPC (subnet + security group config)
- **Redshift Data API:** Uses the Redshift Data API (not direct JDBC) — can reach clusters/serverless via VPC or public endpoints
- **No need for Transit Gateway** in the demo — AgentCore Runtime deploys into the same VPC as Redshift

### 2.7 Demo Talking Points

- **Multi-cluster discovery** — agent finds provisioned AND serverless workgroups automatically
- **Read-only enforcement** — the MCP server rejects any write SQL; governance built in
- **Unified Gateway** — single endpoint serves both S3 Tables and Redshift tools; agent chooses the right tool based on the question
- **Semantic tool search** — AgentCore Gateway lets the agent discover tools by capability description, not by knowing server names
- **Production-grade** — CloudTrail audit of every query, session isolation per user, auto-scaling

---

## Combined Demo: Unified D&A Analytics Gateway

The most powerful demo shows **both servers behind a single AgentCore Gateway**:

```
User: "Show me our data estate"
Agent: → S3 Tables: list_table_buckets + list_namespaces
       → Redshift: list_clusters + list_databases
Agent: "You have 3 S3 Table namespaces (customers, transactions, risk_scores) 
        and 2 Redshift environments (analytics cluster, ETL workgroup)..."

User: "Compare customer counts between S3 Tables and Redshift"
Agent: → S3 Tables: query_table (SELECT COUNT(*) FROM customers)
       → Redshift: execute_query (SELECT COUNT(*) FROM public.customers)
Agent: "S3 Tables has 1.2M customer records; Redshift analytics has 1.2M. In sync."

```

This directly maps to AnyCompany's architecture where the D&A domain accesses **both S3 and Redshift** as data sources, with Bedrock as the central AI platform and AgentCore providing governance.

---

## Appendix: Mapping to Derek's MCP Architecture Diagram

| Derek's Component | Replaced / Enhanced By |
| --- | --- |
| MCP Servers (Fargate/Lambda) | AgentCore Runtime (serverless, managed) |
| MCP Auth Service | AgentCore Gateway auth (Cognito / Entra ID JWT) |
| AWS Load Balancer (for MCP) | AgentCore Gateway (built-in routing + discovery) |
| Amazon Cognito (manual config) | AgentCore Gateway authorizer (integrated) |
| Amazon DynamoDB (session state) | AgentCore Runtime session management (automatic) |
| ECR (container registry) | Still used — images pushed to ECR, deployed by AgentCore |
| CloudWatch / Secrets Manager | Still used — AgentCore integrates natively |
| Transit Gateway | Still used for cross-VPC connectivity (Redshift) |
| MuleSoft MCP Gateway | Remains as enterprise cross-domain layer (not replaced) |

---

## References

- [awslabs S3 Tables MCP Server](https://github.com/awslabs/mcp/blob/main/src/s3-tables-mcp-server/README.md)
- [awslabs Redshift MCP Server](https://awslabs.github.io/mcp/servers/redshift-mcp-server)
- [Deploy MCP servers in AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html)
- [Transform your MCP architecture with AgentCore Gateway](https://aws.amazon.com/jp/blogs/machine-learning/transform-your-mcp-architecture-unite-mcp-servers-through-agentcore-gateway/)
- [Private connectivity patterns for AgentCore Gateway](https://aws.amazon.com/jp/blogs/networking-and-content-delivery/private-connectivity-patterns-for-amazon-bedrock-agentcore-gateway-targets/)
- [Build long-running MCP servers on AgentCore](https://aws.amazon.com/blogs/machine-learning/build-long-running-mcp-servers-on-amazon-bedrock-agentcore-with-strands-agents-integration/)
- [Implementing conversational AI for S3 Tables using MCP](https://aws.amazon.com/ko/blogs/storage/implementing-conversational-ai-for-s3-tables-using-model-context-protocol-mcp/)
- [Accelerating SQL analytics with Redshift MCP server](https://aws.amazon.com/blogs/big-data/accelerating-sql-analytics-with-amazon-redshift-mcp-server/)

