# Requirements: MWAA Serverless Demo

## Functional Requirements

### FR-1: Infrastructure as Code Deployment
**Description:** The entire MWAA Serverless environment must be deployable via AWS CDK (Python) with a single `cdk deploy --all` command.
**Acceptance Criteria:**
- CDK app synthesizes without errors
- All stacks deploy to eu-west-1
- All resources tagged with `Project=mwaa-demo`, `Owner=demo-owner`
- `cdk destroy --all` cleanly removes all resources

### FR-2: VPC and Networking
**Description:** Use an existing VPC with private subnets for MWAA Serverless ENIs. Only create a new security group.
**Acceptance Criteria:**
- Look up existing VPC by ID (CDK context variable `vpc_id`)
- Select private subnets (with NAT/egress) for MWAA ENI placement
- Assume VPC endpoints (S3, Glue, SQS, CloudWatch Logs, KMS, STS, ECR) already exist
- Create security group with self-referencing ingress and all outbound
- Do NOT create new VPC, subnets, NAT Gateway, or VPC endpoints

### FR-3: MWAA Serverless Environment
**Description:** A fully functional MWAA Serverless environment that auto-syncs DAGs from S3.
**Acceptance Criteria:**
- Environment name: `any-company-mwaa-demo`
- DAGs sourced from S3 bucket at path `dags/`
- Web server access mode: Public (demo purposes)
- Execution role with permissions for S3, Glue, Redshift Data API, SNS, ECS RunTask, CloudWatch
- S3 bucket structure: `dags/`, `plugins/`, `requirements.txt`

### FR-4: DAG CI/CD Pipeline
**Description:** GitHub Actions workflow that lints, tests, and deploys DAGs to S3 on push to main.
**Acceptance Criteria:**
- Triggers on changes to `dags/`, `requirements.txt`, or `plugins/`
- Lint stage: `pylint dags/ --disable=all --enable=E`
- Test stage: `pytest tests/ -v`
- Deploy stage: `aws s3 sync dags/ s3://{bucket}/dags/ --delete`
- Auth via GitHub OIDC (no static credentials)

### FR-5: Validation DAG (hello_world)
**Description:** Simple DAG to validate environment is working.
**Acceptance Criteria:**
- Single PythonOperator prints "Hello from MWAA Serverless"
- Schedule: None (manual trigger only)
- Imports cleanly without errors

### FR-6: ETL Pipeline DAG (sample_etl_pipeline)
**Description:** Realistic ETL DAG demonstrating S3 sensor, Glue, Redshift, and notification pattern.
**Acceptance Criteria:**
- Schedule: `@daily`
- Tasks: S3KeySensor → GlueJobOperator → RedshiftDataOperator (or mock) → SnsPublishOperator
- Tags: `["demo", "any-company", "etl"]`
- Graceful fallback: if Redshift unavailable, mock with PythonOperator logging "Redshift load simulated"

### FR-7: Container Execution DAG (container_execution)
**Description:** DAG demonstrating ECS Fargate task execution for dependency-isolated workloads.
**Acceptance Criteria:**
- Schedule: None (manual trigger)
- Uses EcsRunTaskOperator to launch Fargate task with custom Docker image
- Logs ECS task output via PythonOperator

### FR-8: API-Triggered DAG (api_triggered)
**Description:** DAG triggered externally via MWAA REST API demonstrating event-driven orchestration.
**Acceptance Criteria:**
- Schedule: None (triggered via REST API)
- Accepts `conf` parameter with `{"source": "...", "date": "..."}`
- Logs received parameters

### FR-9: Lambda DAG Trigger
**Description:** Lambda function that triggers DAGs programmatically via MWAA REST API.
**Acceptance Criteria:**
- Runtime: Python 3.11
- Calls `create_web_login_token` then POSTs to MWAA REST API
- Triggers `api_triggered` DAG with conf payload
- Deployed via CDK in the same app

### FR-10: ECS Fargate Infrastructure
**Description:** ECS cluster and task definition for container-based task execution from Airflow.
**Acceptance Criteria:**
- Fargate cluster: `any-company-demo-cluster`
- Task definition running a Python container simulating ETL
- ECR repository for the container image

### FR-11: Docker ETL Image
**Description:** Docker image simulating a heavy ETL workload for ECS execution.
**Acceptance Criteria:**
- Base: python:3.11-slim
- Installs pandas, boto3, pyarrow
- `pipeline.py` reads parquet from S3, transforms, writes back, prints summary

### FR-12: Monitoring Dashboard
**Description:** CloudWatch dashboard providing visibility into MWAA health.
**Acceptance Criteria:**
- Widgets: QueuedTasks, RunningTasks, SchedulerHeartbeat, TaskInstanceFailures
- Auto-references the MWAA environment name

### FR-13: DAG Tests
**Description:** Unit tests validating DAG integrity without requiring a live Airflow instance.
**Acceptance Criteria:**
- `test_dags_load_without_errors` — all DAGs import cleanly
- `test_sample_etl_task_count` — correct number of tasks
- `test_dag_tags` — tags present on tagged DAGs

## Non-Functional Requirements

### NFR-1: Cost Efficiency
- Uses existing VPC (no new NAT Gateway costs)
- Redshift Serverless optional (mock acceptable)
- README includes teardown instructions

### NFR-2: Security
- No hardcoded credentials anywhere
- IAM roles for all service interactions
- GitHub OIDC for CI/CD (no static keys)

### NFR-3: Region
- All resources deployed to `eu-west-1` (Ireland)

### NFR-4: Documentation
- README with deploy, validate, and teardown instructions
- Architecture overview in README
