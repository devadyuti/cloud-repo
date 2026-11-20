# Classic MWAA Demo

End-to-end Amazon Managed Workflows for Apache Airflow (MWAA) demonstration deployed via AWS CDK (Python) to `eu-west-1`. Showcases DAG orchestration patterns including ETL pipelines, ECS Fargate container execution, API-triggered workflows, and CI/CD automation.

## Architecture

The project deploys four CDK stacks into an existing VPC:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS Account (eu-west-1)                      │
│                                                                      │
│  ┌──────────────┐     ┌──────────────────────────────────────────┐  │
│  │ GitHub Actions│────▶│ S3 Bucket (any-company-mwaa-demo-dags-{acct}) │  │
│  │   CI/CD      │     │  ├── dags/                                │  │
│  └──────────────┘     │  ├── plugins/                             │  │
│         │ OIDC        │  └── requirements.txt                     │  │
│         ▼             └───────────────┬──────────────────────────┘  │
│  ┌──────────────┐                     │ auto-sync                   │
│  │  IAM Role    │                     ▼                             │
│  └──────────────┘     ┌──────────────────────────────────────────┐  │
│                       │     MWAA Serverless (any-company-mwaa-demo)    │  │
│                       │     ┌────────┐ ┌────────┐ ┌────────┐     │  │
│                       │     │etl     │ │ecs     │ │cdc     │     │  │
│                       │     │pipeline│ │_exec   │ │_ingest │     │  │
│                       │     └────────┘ └───┬────┘ └───┬────┘     │  │
│                       └────────────────────┼──────────┼──────────┘  │
│                                            │          │             │
│              ┌─────────────────────────────┼──────────┼───────┐    │
│              │         Existing VPC         │          │       │    │
│              │  ┌─────────┐  ┌─────────┐   │          │       │    │
│              │  │Private  │  │Private  │   │          │       │    │
│              │  │Subnet-a │  │Subnet-b │   │          │       │    │
│              │  └─────────┘  └─────────┘   │          │       │    │
│              │       │                     │          │       │    │
│              │  ┌────┴────┐                │          │       │    │
│              │  │NAT GW   │                │          │       │    │
│              │  └─────────┘                │          │       │    │
│              └─────────────────────────────┼──────────┼───────┘    │
│                                            │          │             │
│         ┌──────────────────────────────────┘          │             │
│         ▼                                             ▼             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │  AWS Glue    │  │  Redshift    │  │  ECS Fargate             │ │
│  │  (transform) │  │  (Data API)  │  │  (any-company-demo-cluster)   │ │
│  └──────────────┘  └──────────────┘  │  ┌────────────────────┐  │ │
│                                       │  │ ETL Container      │  │ │
│                                       │  │ (ECR image)        │  │ │
│                                       │  └────────────────────┘  │ │
│                                       └──────────────────────────┘ │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ CloudWatch Dashboard (mwaa-demo-dashboard)                    │  │
│  │ Classic MWAA: [QueuedTasks] [RunningTasks] [Heartbeat] [Fail] │  │
│  │ Serverless:   [Runs Started] [Success/Fail] [Avg Duration]    │  │
│  │               [Logs Insights — task events]                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

| Stack | Resources | Dependencies |
|-------|-----------|--------------|
| `MwaaVpcStack` | Lookup existing VPC/subnets, create MWAA security group | None (`vpc_id` context optional — falls back to VPC named "Analytics Workshop VPC") |
| `MwaaStack` | S3 bucket, MWAA environment (Airflow 3.2.1), execution role (S3, SQS, SNS, KMS, Glue, ECS, Secrets Manager) | VpcStack |
| `MwaaEcsStack` | ECS Fargate cluster, task definition, ECR repository | VpcStack |
| `MwaaMonitoringStack` | CloudWatch dashboard with MWAA + serverless workflow metrics | MwaaStack |

Key design decisions:

- **MWAA Serverless** (not Classic) — auto-scaling, scales to zero when idle, simpler configuration
- **Existing VPC lookup** via `Vpc.from_lookup()` — no new VPC, NAT, or endpoints created
- **Public web server** — for demo accessibility (use PRIVATE + VPN in production)
- **Redshift provisioned cluster** — `analytics-cluster` loaded via Redshift Data API (CREATE TABLE + COPY)
- **GitHub OIDC** — no static AWS credentials in CI/CD

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12+ | Virtual environment recommended |
| AWS CDK CLI | Latest | `npm install -g aws-cdk` |
| AWS CLI | v2 | Configured with credentials for target account |
| Docker | Latest | Required for building ECS container image |
| Node.js | 18+ | Required by AWS CDK CLI |
| Amazon SageMaker Unified Studio | Configured | Required to view and manage MWAA Serverless workflows |

Your existing VPC must have:

- Private subnets with NAT egress (at least 2 AZs)
- VPC endpoints for: S3, Glue, SQS, CloudWatch Logs, KMS, STS, ECR

## Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd mwaa-serverless-demo

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# Install CDK dependencies
pip install -r requirements-cdk.txt

# Bootstrap CDK (one-time per account/region)
cdk bootstrap aws://<ACCOUNT_ID>/eu-west-1

# Deploy all stacks — optionally pass your VPC ID (falls back to "Analytics Workshop VPC")
cdk deploy --all -c vpc_id=vpc-xxx --require-approval never

# Or deploy without vpc_id (uses VPC named "Analytics Workshop VPC")
cdk deploy --all --require-approval never
```

After deployment completes:

```bash
# Build and push Docker image to ECR
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.eu-west-1.amazonaws.com
docker build -t any-company-etl-container docker/
docker tag any-company-etl-container:latest <ACCOUNT_ID>.dkr.ecr.eu-west-1.amazonaws.com/any-company-etl-container:latest
docker push <ACCOUNT_ID>.dkr.ecr.eu-west-1.amazonaws.com/any-company-etl-container:latest

# Upload DAGs and requirements to S3
aws s3 sync dags/ s3://any-company-mwaa-demo-dags-<ACCOUNT_ID>/dags/
aws s3 cp requirements.txt s3://any-company-mwaa-demo-dags-<ACCOUNT_ID>/requirements.txt
```

## Validate

1. **Check MWAA environment status:**
   ```bash
   aws mwaa get-environment --name any-company-mwaa-demo \
     --query 'Environment.Status' --output text
   # Expected: AVAILABLE (may take 15-25 minutes after deploy)
   ```

2. **Open the Airflow UI:**
   ```bash
   aws mwaa create-web-login-token --name any-company-mwaa-demo \
     --query 'WebServerHostname' --output text
   ```
   Navigate to `https://<hostname>` in your browser.

   > **Note:** The Airflow UI shows only the traditional Python DAGs. For MWAA Serverless workflows (YAML), use Amazon SageMaker Unified Studio.

3. **Trigger the sample_etl_pipeline DAG:**
   - In the Airflow UI, find `sample_etl_pipeline` → click the play button → Trigger DAG
   - Verify the 4 tasks complete in order: `wait_for_data` → `glue_transform` → `load_to_redshift` → `notify_success`

4. **Test the Lambda trigger (if deployed separately):**
   ```bash
   aws lambda invoke --function-name mwaa-dag-trigger /tmp/out.json
   cat /tmp/out.json
   ```
   The Lambda calls the MWAA `InvokeRestApi` API directly (no web login token or session cookie needed), POSTing to `/dags/api_triggered/dagRuns` with a conf payload (`message`, `source`, `request_id`). Each invocation uses a microsecond-precision `logical_date` to avoid DAG run conflicts. Verify the DAG run appears in the Airflow UI.

   > **Note:** The Lambda function is no longer deployed as part of this CDK app. Deploy it separately if needed for API-triggered workflows.

5. **Check the CloudWatch dashboard:**
   - Open CloudWatch → Dashboards → `mwaa-demo-dashboard`
   - **Classic MWAA section:** QueuedTasks, RunningTasks, SchedulerHeartbeat, TaskInstanceFailures
   - **Serverless Workflow section:** Lambda Invocations/Errors/Duration/Throttles, custom workflow metrics (runs started/succeeded/failed, avg duration), and a Logs Insights query for task-level events

6. **Test automatic S3 event trigger:**
   ```bash
   # Drop a file in serverless/incoming/ — s3_event_lambda_serverless workflow starts automatically
   echo "id,name,amount\n1,Alice,100" > /tmp/data.csv
   aws s3 cp /tmp/data.csv s3://any-company-mwaa-demo-dags-<ACCOUNT_ID>/serverless/incoming/data.csv
   ```
   Check SageMaker Unified Studio — `s3_event_lambda_serverless` workflow should start within seconds. Verify with:
   ```bash
   aws s3 cp s3://any-company-mwaa-demo-dags-<ACCOUNT_ID>/output/api_trigger_log.txt -
   ```

## DAG Descriptions

| DAG | Schedule | Tags | Description |
|-----|----------|------|-------------|
| `sample_etl_pipeline` | `@daily` | `demo`, `any-company`, `etl` | Lightweight ETL: S3KeySensor → GlueJobOperator → mock Redshift load → SnsPublishOperator notification. |
| `container_execution` | None (manual) | `demo`, `ecs`, `container` | Launches an ECS Fargate task (`any-company-etl-task`) via EcsRunTaskOperator for dependency-isolated workloads. |
| `external_system_integration` | None (manual) | `demo`, `integration`, `api` | Calls car search REST API (POST with JSON body) → transform results into data lake schema → S3 JSON load (`external-api/car-search/{date}/`) → SNS notification. Requires `car_search_api` Airflow HTTP connection. |
| `data_lake_etl` | `@daily` | `production`, `data-lake`, `etl`, `medallion` | Medallion architecture: S3 landing → Glue Crawler → Glue ETL (bronze→silver) → Athena quality gate → Redshift COPY (gold) → SNS. Branch logic for quarantine on failure. |
| `ml_feature_pipeline` | Every 6h | `ml`, `features`, `ecs`, `fargate` | ECS Fargate feature engineering → Athena validation (completeness + drift) → Glue catalog update → S3 feature store registration → SNS. SLA-enforced. |
| `cdc_ingestion` | Every 15min | `cdc`, `integration`, `external-api`, `incremental` | CDC from external REST API: HTTP poll → transform/deduplicate → partitioned S3 write → Glue crawler → Athena view refresh → Redshift MERGE upsert. High-watermark tracking. |
| `api_triggered` | None (API-only) | `demo`, `api` | Accepts `dag_run.conf` via MWAA REST API, writes execution metadata to S3, and publishes an SNS notification to `mwaa-etl-notifications`. |

## Serverless Workflows (YAML)

In addition to traditional Python DAGs, this demo includes **MWAA Serverless workflow definitions** in YAML format (`serverless-workflows/`). These demonstrate the declarative, code-free workflow authoring model unique to MWAA Serverless.

> **Important:** MWAA Serverless workflows are managed through **Amazon SageMaker Unified Studio** — they do NOT appear in the traditional Airflow UI. The Airflow UI only shows the Python-based DAGs (`dags/`). To view, trigger, and monitor serverless workflows, use the SageMaker Unified Studio console.

### Key Differences from Python DAGs

| | Traditional DAGs (`dags/`) | Serverless Workflows (`serverless-workflows/`) |
|---|---|---|
| Format | Python | YAML |
| Operators | Any Airflow operator | AWS-native operators only (no PythonOperator) |
| Management UI | Airflow Web UI | Amazon SageMaker Unified Studio |
| Authoring | Code-based, full flexibility | Declarative, simpler, constrained |
| Use case | Complex logic, custom code | AWS service orchestration pipelines |

### Workflow Definitions

| Workflow | File | Description |
|----------|------|-------------|
| `hello_world` | `serverless-workflows/hello_world.yml` | Writes "Hello from MWAA Serverless" to S3 via `S3CreateObjectOperator`. Single-task validation workflow. |
| `s3_etl_workflow` | `serverless-workflows/s3_etl_workflow.yml` | Multi-step S3 pipeline: list objects → write file listing (XCom) → copy to processed prefix. Demonstrates task dependencies and data passing. |
| `s3_event_lambda_serverless` | `serverless-workflows/s3_event_lambda_serverless.yml` | **Automatically triggered** when files land in `serverless/incoming/` prefix. S3 event → Lambda (`start_workflow_run`) → this workflow. Logs trigger metadata to S3. |

### SageMaker Unified Studio Setup

First-time users must configure Amazon SageMaker Unified Studio before they can view or manage MWAA Serverless workflows.

**1. IAM Role (Admin):**

You need an IAM role with administrator-level permissions to set up SageMaker Unified Studio. This role is used during initial configuration only — not for day-to-day workflow execution.

```bash
# Verify you're using an admin role
aws sts get-caller-identity
# The role ARN should include AdministratorAccess or equivalent
```

**2. Encryption Key:**

During setup, you'll be prompted to choose an encryption key for the SageMaker Unified Studio domain:

- **AWS managed key** (recommended for demos) — no additional setup required
- **Customer managed key (CMK)** — use if your organisation requires KMS key control; you'll need to create or select an existing KMS key in `eu-west-1`

**3. Domain Setup Steps:**

1. Open the [Amazon SageMaker Unified Studio console](https://console.aws.amazon.com/sagemaker/unified-studio)
2. Create a new domain (or use an existing one) in `eu-west-1`
3. Select your IAM admin role as the execution role
4. Choose your encryption key preference (AWS managed or CMK)
5. Wait for domain status to become **Active**
6. Add users/groups who need access to view and trigger workflows

Once the domain is active, MWAA Serverless workflows deployed to S3 will appear in the Studio interface under the Workflows section.

> **Note:** The admin IAM role is only needed for initial Studio setup. After configuration, users can access workflows with their own federated or IAM Identity Center credentials.

### Deploying Serverless Workflows

Upload the YAML definitions to the MWAA S3 bucket:

```bash
aws s3 sync serverless-workflows/ \
  s3://any-company-mwaa-demo-dags-<ACCOUNT_ID>/dags/serverless-workflows/
```

### Validating Serverless Workflows

**1. Seed test data (for ETL workflow):**

```bash
echo "id,name,amount" > /tmp/data.csv
echo "1,Alice,100" >> /tmp/data.csv
aws s3 cp /tmp/data.csv s3://any-company-mwaa-demo-dags-<ACCOUNT_ID>/serverless/incoming/data.csv
```

**2. Trigger and validate each workflow:**

| Workflow | Trigger | Validate |
|----------|---------|----------|
| `hello_world` | SageMaker Unified Studio → Trigger | `aws s3 cp s3://any-company-mwaa-demo-dags-<ACCOUNT_ID>/output/hello_world.txt -` shows greeting |
| `s3_etl_workflow` | SageMaker Unified Studio → Trigger | `aws s3 ls s3://any-company-mwaa-demo-dags-<ACCOUNT_ID>/processed/` shows `file_listing.txt` and `data.csv` |
| `api_triggered` | Automatic (upload file to `serverless/incoming/`) | `aws s3 cp s3://any-company-mwaa-demo-dags-<ACCOUNT_ID>/output/api_trigger_log.txt -` shows trigger message |

**3. Demo narrative:**

> "MWAA Serverless workflows are defined in YAML and managed through SageMaker Unified Studio — no Python code, no Airflow UI needed. They use only AWS-native operators (S3, Glue, etc.), scale to zero, and don't require custom code packaging. You define your pipeline declaratively, deploy the YAML to S3, and manage everything from a unified data engineering interface."

## CI/CD Setup

The GitHub Actions workflow (`.github/workflows/deploy-dags.yml`) automates DAG deployment on push to `main`.

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_OIDC_ROLE_ARN` | ARN of the IAM role assumed via GitHub OIDC federation (e.g., `arn:aws:iam::<ACCOUNT_ID>:role/github-actions-mwaa-deploy`) |
| `MWAA_BUCKET` | Name of the MWAA DAGs S3 bucket (e.g., `any-company-mwaa-demo-dags-<ACCOUNT_ID>`) |

### Pipeline Stages

1. **Lint** — `pylint dags/ --disable=all --enable=E` (error-only checks)
2. **Test** — `pytest tests/ -v` (DAG import and structural tests)
3. **Deploy** — Syncs `dags/` to S3 and uploads `requirements.txt` (runs only after lint + test pass)

### OIDC Role Setup

Create an IAM role with trust policy for GitHub OIDC:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"},
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
      "StringLike": {"token.actions.githubusercontent.com:sub": "repo:<ORG>/<REPO>:ref:refs/heads/main"}
    }
  }]
}
```

The role needs `s3:PutObject`, `s3:DeleteObject`, and `s3:ListBucket` permissions on the MWAA bucket.

## Teardown

Remove all deployed resources:

```bash
cdk destroy --all -c vpc_id=vpc-xxx   # include -c vpc_id if you used it during deploy
```

This removes:
- MWAA environment and S3 bucket (auto-deletes objects)
- ECS cluster, task definition, and ECR repository
- CloudWatch dashboard
- Security group

The existing VPC, subnets, NAT gateway, and VPC endpoints are **not affected** (they were only referenced, not created).

## Cost Notes

- **MWAA Serverless** scales to zero when idle but incurs charges when workers are active. Expect minimal cost if only running manual-trigger DAGs during testing.
- **Existing VPC** — no additional NAT gateway or VPC endpoint costs from this demo.
- **ECS Fargate** — billed per-second only while tasks are running.
- **ECR** — charges for stored images (minimal for a single demo image).
- **S3** — minimal storage for DAG files.

**Recommendation:** Run `cdk destroy --all` when the demo is complete to avoid ongoing charges. The most significant cost component is the MWAA environment when workers are active.

## Project Structure

```
mwaa-serverless-demo/
├── app.py                          # CDK entry point (4 stacks, eu-west-1)
├── cdk.json                        # CDK config with vpc_id context
├── requirements-cdk.txt            # CDK Python dependencies
├── requirements.txt                # Airflow provider dependencies (deployed to MWAA)
├── stacks/
│   ├── __init__.py
│   ├── vpc_stack.py                # VPC lookup + security group
│   ├── mwaa_stack.py               # S3 bucket + MWAA environment + IAM role
│   ├── ecs_stack.py                # ECS cluster + Fargate task + ECR
│   └── monitoring_stack.py         # CloudWatch dashboard (MWAA + serverless metrics)
├── dags/
│   ├── sample_etl_pipeline.py      # ETL pipeline with Glue + mock Redshift
│   ├── container_execution.py      # ECS Fargate task execution
│   ├── external_system_integration.py  # REST API polling + S3 load
│   ├── data_lake_etl.py            # Medallion architecture (bronze → silver → gold)
│   ├── ml_feature_pipeline.py      # ECS feature engineering + Athena validation
│   ├── cdc_ingestion.py            # CDC from external API + Redshift MERGE
│   └── api_triggered.py            # API-triggered workflow with SNS notification
├── plugins/                        # Airflow plugins (extensibility placeholder)
├── docker/
│   ├── Dockerfile                  # ETL container (python:3.11-slim)
│   └── app/
│       └── pipeline.py             # S3 parquet transform script
├── lambda/
│   └── trigger_dag.py              # Lambda handler — triggers api_triggered DAG via InvokeRestApi
├── serverless-workflows/           # MWAA Serverless YAML workflow definitions
│   ├── hello_world.yml             # Single-task S3 write validation
│   ├── s3_etl_workflow.yml         # Multi-step S3 ETL pipeline
│   └── s3_event_lambda_serverless.yml  # Auto-triggered on S3 upload via Lambda
├── tests/
│   ├── conftest.py                 # Test fixtures (Airflow env setup)
│   └── test_dags.py                # DAG integrity tests
└── .github/
    └── workflows/
        └── deploy-dags.yml         # CI/CD pipeline (lint → test → deploy)
```
