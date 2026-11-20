# AgentCore MCP Demo — D&A Analytics Gateway

Deploy two AWS Labs MCP servers (S3 Tables and Redshift) onto Amazon Bedrock AgentCore Runtime, front them with a unified AgentCore Gateway, and run a Strands-based local agent for natural language data exploration.

## Architecture Overview

```
User / Agent Client
        │
        ▼
┌─────────────────────────┐
│   Strands Agent (local) │
│   (da-analytics-agent)  │
│   Claude Sonnet 4       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   AgentCore Gateway     │
│   (da-analytics-gateway)│
│   • SigV4 Auth          │
│   • Tool Discovery      │
│   • Routing             │
└──────┬──────────┬───────┘
       │          │
       ▼          ▼
┌────────────┐ ┌─────────────────────┐
│ S3 Tables  │ │ Redshift            │
│ MCP Server │ │ MCP Server          │
│ (Runtime)  │ │ (Runtime, VPC opt.) │
└──────┬─────┘ └──────────┬──────────┘
       │                │
       ▼                ▼
┌────────────┐ ┌────────────────┐
│ S3 Tables  │ │ Amazon         │
│ (Iceberg)  │ │ Redshift       │
└────────────┘ └────────────────┘
```

**Key benefits over custom hosting:**

- No Fargate clusters or Lambda runtimes to manage
- Serverless auto-scaling (scale to zero when idle)
- Session isolation via microVM per invocation
- Single gateway endpoint for all MCP tools
- AWS SigV4 auth (service: `bedrock-agentcore`) — uses existing IAM credentials
- CloudTrail audit trail out of the box

## Project Structure

```
agent-core-mcp-demo/
├── infra/                  # AWS CDK infrastructure
│   ├── app.py             # CDK app entry point
│   ├── stacks/            # CDK stack definitions
│   ├── cdk.json           # CDK configuration
│   └── requirements.txt   # CDK Python dependencies
├── containers/             # AgentCore Runtime wrapper images
│   ├── s3-tables/         # S3 Tables wrapper (streamable HTTP, stateless, no DNS rebind)
│   │   ├── Dockerfile
│   │   └── entrypoint.py
│   └── redshift/          # Redshift wrapper (streamable HTTP, stateless, no DNS rebind)
│       ├── Dockerfile
│       └── entrypoint.py
├── deploy/                 # Deployment & orchestration scripts
│   ├── build_and_push.sh  # Build Docker images, push to ECR
│   ├── deploy_runtimes.py # Create AgentCore runtimes via boto3
│   ├── deploy_gateway.py  # Create gateway, register targets
│   ├── deploy_agent.py    # Validate gateway, save agent config
│   └── teardown.py        # Clean up all resources
├── tests/                  # Unit tests (pytest)
│   ├── test_build_and_push.py
│   ├── test_config.py
│   ├── test_deploy_agent.py
│   ├── test_deploy_runtimes.py
│   ├── test_entrypoints.py
│   ├── test_run_agent.py
│   └── test_seed_s3_tables.py
├── data/                   # Sample data and seeding scripts
│   ├── seed_s3_tables.py  # Load sample data into S3 Tables
│   ├── seed_redshift.py   # Load sample data into Redshift
│   └── sample/            # CSV sample datasets
├── demo/                   # Demo materials
│   ├── demo_script.md     # Step-by-step walkthrough
│   ├── talking_points.md  # Key messages per section
│   └── test_queries.py    # Automated validation queries
├── docs/                   # Documentation
│   ├── architecture_mapping.md
│   └── setup_guide.md
├── pyproject.toml          # Project metadata and dependencies
└── README.md               # This file
```

## Prerequisites

- Python 3.12+
- AWS CLI v2 configured with `eu-west-1` region
- AWS CDK CLI (`npm install -g aws-cdk`)
- Docker (for building MCP server images)
- An AWS account with Bedrock AgentCore access enabled

## Quick Start

1. **Install dependencies:**

   ```bash
   cd agent-core-mcp-demo
   pip install -e .
   pip install strands-agents mcp httpx botocore
   ```

2. **Deploy infrastructure (ECR, IAM, Cognito, VPC):**

   ```bash
   cd infra
   pip install -r requirements.txt
   cdk deploy --all
   ```

   The IAM stack creates runtime roles with S3 Tables / Redshift data access,
   ECR pull permissions so AgentCore can pull container images at runtime
   startup, **and** a gateway role (`AgentCoreGatewayRole`) for the AgentCore
   Gateway to assume.

3. **Build and push MCP server container images:**

   ```bash
   ./deploy/build_and_push.sh
   ```

   This clones the awslabs/mcp repo, builds the base S3 Tables and Redshift
   images, then builds AgentCore Runtime wrapper images (from `containers/`)
   that configure stateless streamable HTTP transport and disable DNS rebinding
   protection. The wrappers override the base image tags before pushing to ECR.

4. **Deploy AgentCore runtimes and gateway:**

   ```bash
   python deploy/deploy_runtimes.py         # PUBLIC mode for both by default
   python deploy/deploy_runtimes.py --wait  # Deploy and poll until ACTIVE
   python deploy/deploy_gateway.py
   ```

   The Redshift runtime uses VPC network mode when `AGENTCORE_VPC_SUBNET_IDS` and
   `AGENTCORE_VPC_SECURITY_GROUP_IDS` are set; otherwise it falls back to PUBLIC mode.

5. **Seed sample data:**

   ```bash
   python data/seed_s3_tables.py
   python data/seed_redshift.py
   ```

6. **Validate gateway and save agent config:**

   ```bash
   python -m deploy.deploy_agent           # Validate gateway and save config
   python -m deploy.deploy_agent --verify  # Also test gateway HTTP reachability
   ```

7. **Run the interactive demo agent:**

   ```bash
   python -m demo.run_agent
   python -m demo.run_agent --query "What tables are available?"
   ```

## Running Tests

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## Region

All resources deploy to **eu-west-1** (London).

## Teardown

```bash
python deploy/teardown.py
cd infra && cdk destroy --all
```
