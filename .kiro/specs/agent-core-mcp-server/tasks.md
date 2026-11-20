# Implementation Plan: MCP AgentCore Demo — D&A Analytics Gateway

## Overview

Deploy two AWS Labs MCP servers (S3 Tables and Redshift) onto Amazon Bedrock AgentCore Runtime, front them with a unified AgentCore Gateway, and connect a Bedrock Agent for natural language data exploration. The implementation follows an incremental approach: scaffold the project, provision infrastructure (ECR, IAM, Cognito, VPC), build and push MCP server container images, deploy AgentCore runtimes and gateway, prepare sample data, create the Bedrock Agent, validate end-to-end, and prepare demo materials. All infrastructure is defined in Python CDK; deployment orchestration uses boto3 scripts.

## Tasks

- [x] 1. Scaffold project structure
  - [x] 1.1 Create the project root directory and folder structure
    - Create `agent-core-mcp-demo/` at the workspace root
    - Create subdirectories: `infra/stacks/`, `deploy/`, `data/sample/`, `demo/`, `docs/`
    - Create `pyproject.toml` with project metadata, Python 3.12 requirement, and dependencies (`aws-cdk-lib`, `boto3`, `constructs`)
    - Create root `README.md` describing the project purpose, architecture overview, and quick-start instructions
    - _Requirements: 1, 2, 3_

  - [x] 1.2 Initialise CDK app structure
    - Create `infra/app.py` as the CDK app entry point importing all stacks
    - Create `infra/cdk.json` with CDK configuration and context parameters (account_id, region, vpc_subnet_ids, vpc_security_group_ids)
    - Create `infra/requirements.txt` with `aws-cdk-lib>=2.150.0` and `constructs>=10.0.0`
    - _Requirements: 1, 2, 3_

  - [x] 1.3 Create shared configuration module
    - Create `deploy/config.py` with the `AgentCoreConfig` dataclass holding all resource names, region, account ID, VPC config, and model IDs
    - Configuration values should be overridable via environment variables for flexibility across accounts
    - _Requirements: 1, 2, 3, 6_

- [x] 2. Provision supporting infrastructure (CDK)
  - [x] 2.1 Create ECR stack for container image repositories
    - Create `infra/stacks/ecr_stack.py`
    - Define two ECR repositories: `s3-tables-mcp-server` and `redshift-mcp-server`
    - Enable image scanning on push and set lifecycle policy to retain last 5 images
    - Output repository URIs as CloudFormation exports
    - _Requirements: 1.2, 2.1_

  - [x] 2.2 Create IAM stack for AgentCore runtime roles
    - Create `infra/stacks/iam_stack.py`
    - Define `AgentCoreS3TablesRole` with trust policy for `bedrock-agentcore.amazonaws.com` and permissions: `s3tables:*`, `s3:GetObject`, `s3:ListBucket`
    - Define `AgentCoreRedshiftRole` with trust policy for `bedrock-agentcore.amazonaws.com` and permissions: `redshift:DescribeClusters`, `redshift-serverless:ListWorkgroups`, `redshift-data:ExecuteStatement`, `redshift-data:GetStatementResult`, `redshift-data:DescribeStatement`
    - Output role ARNs as CloudFormation exports
    - _Requirements: 1.3, 2.3, 10.1_

  - [x] 2.3 Create Cognito stack for JWT authentication
    - Create `infra/stacks/cognito_stack.py`
    - Define Cognito User Pool (`da-analytics-pool`) with email sign-in and password policy
    - Define User Pool Client for the gateway authorizer
    - Output pool ID, pool ARN, client ID, and issuer URL as CloudFormation exports
    - _Requirements: 3.2, 3.4, 10.2_

  - [x] 2.4 Create VPC stack for Redshift connectivity (optional — use existing VPC)
    - Create `infra/stacks/vpc_stack.py`
    - If using existing VPC: accept subnet IDs and security group IDs via CDK context
    - If creating new: define VPC with 2 private subnets and a security group allowing Redshift port 5439
    - Output subnet IDs and security group IDs
    - _Requirements: 2.2_

  - [x] 2.5 Deploy CDK stacks
    - Run `cdk deploy --all` to provision ECR repos, IAM roles, Cognito pool, and VPC resources
    - Verify all stack outputs are available
    - _Requirements: 1, 2, 3_

- [x] 3. Build and push MCP server container images
  - [x] 3.1 Create build-and-push script
    - Create `deploy/build_and_push.sh`
    - Clone `https://github.com/awslabs/mcp.git` (or use existing clone)
    - Build Docker image for S3 Tables MCP server from `src/s3-tables-mcp-server/`
    - Build Docker image for Redshift MCP server from `src/redshift-mcp-server/`
    - Authenticate with ECR (`aws ecr get-login-password`)
    - Tag and push both images to their respective ECR repositories
    - Accept region and account ID as parameters
    - _Requirements: 1.1, 1.2, 2.1_

  - [x] 3.2 Verify container images
    - Confirm both images are present in ECR with `latest` tag
    - Optionally test locally with `docker run` to verify MCP server starts
    - _Requirements: 1.2, 2.1_

- [x] 4. Deploy AgentCore Runtimes
  - [x] 4.1 Create runtime deployment script
    - Create `deploy/deploy_runtimes.py`
    - Import config from `deploy/config.py`
    - Instantiate `boto3.client('bedrock-agentcore-control')`
    - Implement `deploy_s3_tables_runtime()`: calls `create_runtime` with ECR image URI, environment variables (`AWS_REGION`, `FASTMCP_LOG_LEVEL`), stateless HTTP protocol config, and S3 Tables IAM role ARN
    - Implement `deploy_redshift_runtime()`: calls `create_runtime` with ECR image URI, environment variables, stateless HTTP protocol config, VPC network config (subnets + security groups), and Redshift IAM role ARN
    - Store returned runtime ARNs in config/output file for downstream scripts
    - _Requirements: 1.3, 1.4, 1.5, 2.2, 2.4, 2.5_

  - [x] 4.2 Execute runtime deployment
    - Run `deploy_runtimes.py`
    - Verify both runtimes are created successfully (runtime ARNs returned)
    - Check runtime status transitions to ACTIVE
    - _Requirements: 1.5, 2.5_

- [x] 5. Deploy AgentCore Gateway and register targets
  - [x] 5.1 Create gateway deployment script
    - Create `deploy/deploy_gateway.py`
    - Import config and runtime ARNs from previous step
    - Implement `create_gateway()`: calls `create_gateway` with name, description, and JWT authorizer config (Cognito client ID, pool ARN, issuer URL)
    - Implement `register_s3_tables_target()`: calls `create_gateway_target` with gateway ID, name `s3-tables`, and S3 Tables runtime ARN
    - Implement `register_redshift_target()`: calls `create_gateway_target` with gateway ID, name `redshift-analytics`, and Redshift runtime ARN
    - Implement `synchronize_targets()`: calls `synchronize_gateway_targets` to trigger tool discovery
    - Store gateway ID in config/output file
    - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4_

  - [x] 5.2 Execute gateway deployment
    - Run `deploy_gateway.py`
    - Verify gateway is created with correct auth config
    - Verify both targets are registered
    - Verify synchronization completes and tools are discoverable
    - _Requirements: 3.3, 4.4, 5.4_

- [x] 6. Prepare sample data
  - [x] 6.1 Create sample CSV data files
    - Create `data/sample/customers.csv` with ~1000 records (customer_id, name, segment, region, onboarded_date, lifetime_value)
    - Create `data/sample/transactions.csv` with ~5000 records (txn_id, customer_id, amount, category, txn_date, channel)
    - Create `data/sample/risk_scores.csv` with ~1000 records (customer_id, score, model_version, calculated_date, risk_band)
    - Use realistic UK financial data patterns (GBP values, UK regions, banking categories)
    - _Requirements: 11.1, 11.3_

  - [x] 6.2 Create S3 Tables seed script
    - Create `data/seed_s3_tables.py`
    - Create S3 Table Bucket (`anycompany-da-analytics`) if not exists
    - Create namespaces: `customers`, `transactions`, `risk_scores`
    - Create Iceberg tables with appropriate schemas from CSV headers
    - Load CSV data into tables using `create_table_from_csv` or PyIceberg append
    - _Requirements: 11.1, 11.3_

  - [x] 6.3 Create Redshift seed script
    - Create `data/seed_redshift.py`
    - Connect to Redshift cluster/workgroup via Data API
    - Create `analytics_db.public.customers`, `analytics_db.public.monthly_sales`, `analytics_db.public.risk_assessments` tables
    - Load subset of sample data using COPY or INSERT statements via Data API
    - Verify data is queryable
    - _Requirements: 11.2, 11.3_

  - [x] 6.4 Execute data seeding
    - Run `seed_s3_tables.py` and `seed_redshift.py`
    - Verify data is accessible (manual S3 Tables query, manual Redshift Data API query)
    - _Requirements: 11.1, 11.2, 11.3_

- [x] 7. Create and configure Bedrock Agent
  - [x] 7.1 Create agent deployment script
    - Create `deploy/deploy_agent.py`
    - Import config and gateway ID from previous steps
    - Implement `create_agent()`: calls `bedrock_client.create_agent` with agent name `da-analytics-agent`, foundation model `anthropic.claude-sonnet-4-20250514`, instruction prompt, and AgentCore gateway config
    - Instruction prompt should define the agent as a D&A analytics assistant, direct it to use tools for discovery and queries, and instruct it to explain findings clearly
    - Store agent ID in config/output file
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 7.2 Execute agent deployment
    - Run `deploy_agent.py`
    - Verify agent is created and linked to gateway
    - Verify agent can discover tools from both S3 Tables and Redshift MCP servers
    - _Requirements: 6.4_

- [ ] 8. End-to-end validation
  - [ ] 8.1 Create test queries script
    - Create `demo/test_queries.py`
    - Implement automated test queries covering:
      - S3 Tables discovery: "What tables are available in our analytics bucket?"
      - S3 Tables query: "Show me the top 5 customers by lifetime value"
      - Redshift discovery: "Explore my Redshift environment"
      - Redshift query: "What were the top 10 sales last month?"
      - Cross-source: "Compare customer counts between S3 Tables and Redshift"
    - Assert each query returns a non-empty response referencing expected data
    - _Requirements: 7.1, 7.2, 7.3, 8.1, 8.2, 9.1, 9.2, 9.3_

  - [ ] 8.2 Validate security controls
    - Verify S3 Tables MCP server rejects write operations (attempt `create_table_bucket` without `--allow-write`)
    - Verify Redshift MCP server rejects write SQL (attempt INSERT statement)
    - Verify gateway rejects unauthenticated requests (call without JWT token)
    - Check CloudTrail for tool invocation audit logs
    - _Requirements: 7.4, 8.3, 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ] 8.3 Validate auto-scaling and session isolation
    - Submit concurrent requests and verify runtime scales
    - Verify sessions are isolated (one user's query state doesn't leak to another)
    - _Requirements: 10.4_

- [ ] 9. Prepare demo materials
  - [ ] 9.1 Write demo script
    - Create `demo/demo_script.md`
    - Structure: Opening (context, Derek's diagram) → S3 Tables Discovery → S3 Tables Query → Redshift Discovery → Redshift Query → Cross-Source Comparison → Security & Governance Highlights → Architecture Mapping → Closing
    - Include exact natural language prompts to type and expected agent responses
    - Include timing estimates per section (total ~15 minutes)
    - _Requirements: 12.1, 12.2_

  - [ ] 9.2 Write talking points
    - Create `demo/talking_points.md`
    - Key messages: no credentials exposed, read-only by default, serverless auto-scaling, replaces 3+ components in Derek's diagram, CloudTrail audit trail, semantic tool discovery, unified endpoint
    - Per-section bullets for the demo presenter
    - _Requirements: 12.3_

  - [ ] 9.3 Write architecture mapping document
    - Create `docs/architecture_mapping.md`
    - Side-by-side table: Derek's component → AgentCore replacement → benefit
    - Include before/after architecture diagrams
    - _Requirements: 12.4_

  - [ ] 9.4 Write setup guide
    - Create `docs/setup_guide.md`
    - Prerequisites: AWS account, Bedrock AgentCore access, Docker, Python 3.12+, `uv`/`pip`, CDK CLI, AWS CLI configured for eu-west-1
    - Step-by-step deployment instructions referencing the scripts
    - Troubleshooting section for common issues (ECR auth, VPC connectivity, IAM permissions)
    - _Requirements: 1, 2, 3_

- [ ] 10. Create teardown script
  - [ ] 10.1 Create resource cleanup script
    - Create `deploy/teardown.py`
    - Delete Bedrock Agent
    - Delete gateway targets, then gateway
    - Delete AgentCore runtimes
    - Optionally delete ECR images (retain repos for rebuild)
    - Optionally destroy CDK stacks (`cdk destroy --all`)
    - Include confirmation prompts before destructive actions
    - Print summary of what was deleted
    - _Requirements: 1, 2, 3 (cleanup)_

- [ ] 11. Final checkpoint — end-to-end demo rehearsal
  - Run through the full demo script against live infrastructure
  - Verify all queries produce expected results
  - Time the demo and adjust pacing if needed
  - Confirm talking points align with live behaviour
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

## Notes

- All infrastructure code is Python (CDK + boto3 scripts) — no TypeScript or CloudFormation templates
- The MCP server containers are off-the-shelf AWS Labs images — no custom application code needed for the servers themselves
- Region is `eu-west-1` to match AnyCompany's environment and Bedrock AgentCore availability
- The Redshift MCP server requires VPC connectivity; the S3 Tables MCP server uses public AWS APIs
- Tasks marked with `*` (none currently) would be optional production-readiness items
- The demo should take ~15 minutes to present, with setup deployable in ~30 minutes from a clean account
- All deployment scripts should be idempotent where possible (check-before-create pattern)
- The teardown script ensures demo resources don't accumulate costs after the demo
- Sample data uses realistic UK financial patterns to resonate with AnyCompany stakeholders
