# MWAA Serverless Demo — Build Spec

## Objective

Build a working end-to-end demo of Amazon MWAA Serverless for a customer show-and-tell session. The demo must prove:

1. MWAA Serverless workflows deploy cleanly via IaC (CDK Python)
2. DAG CI/CD pipeline works (GitHub Actions → S3 → MWAA auto-syncs)
3. A realistic ETL DAG runs successfully (S3 sensor → Glue → Redshift → notification)
4. Container-based task execution works (EcsRunTaskOperator)
5. REST API can trigger DAGs programmatically (Lambda → REST API)
6. Monitoring is visible (CloudWatch dashboard + Airflow UI)

## Deadline

3 days — demo must be functional by Thursday 31 July 2026.

## Technical Requirements

### Infrastructure (CDK Python, region: eu-west-1)

Deploy these resources via `cdk deploy`:

**VPC:**

- 2 private subnets (AZ-a, AZ-b) for MWAA ENIs
- 2 public subnets for NAT Gateway
- 1 NAT Gateway (single — demo only, cost reasons)
- VPC Endpoints: S3 (Gateway), Glue, Redshift Data API, SQS, CloudWatch Logs, KMS, STS, ECR API, ECR DKR
- Security group for MWAA: self-referencing ingress, all outbound

**MWAA Serverless workflows:**

- No environment to provision — create Serverless workflows directly
- Source bucket: S3 bucket for workflow definitions (DAGs/plugins/requirements)
- DAGs path: `dags/`
- Web server access: Public (for demo ease — private recommended for production)
- Each workflow gets its own execution role (workflow-level IAM) with permissions: S3, Glue, Redshift Data API, SNS, ECS RunTask, CloudWatch

**S3 Bucket:**

- Name: `any-company-mwaa-demo-dags-{account_id}`
- Structure: `dags/`, `plugins/`, `requirements.txt`

**ECS Cluster + Task Definition:**

- Fargate cluster: `any-company-demo-cluster`
- Task definition for a sample Python container that simulates heavy ETL
- ECR repo for the container image

**Redshift Serverless (optional — can use mock if time-tight):**

- Namespace + workgroup for demo SQL execution
- IAM role for COPY/UNLOAD operations

**CloudWatch Dashboard:**

- Widgets: QueuedTasks, RunningTasks, SchedulerHeartbeat, TaskInstanceFailures

### CI/CD Pipeline (GitHub Actions)

File: `.github/workflows/deploy-dags.yml`

Triggers on push to `main` branch when `dags/`, `requirements.txt`, or `plugins/` change.

Stages:

1. Lint: `pylint dags/ --disable=all --enable=E`
2. Test: `pytest tests/ -v`
3. Deploy: `aws s3 sync dags/ s3://{bucket}/dags/ --delete` + copy requirements.txt

Auth: GitHub OIDC → assume IAM role (no static credentials)

### DAGs to Build

**1. **`hello_world.py` — Validation DAG

- Single PythonOperator that prints "Hello from MWAA Serverless"
- Schedule: None (manual trigger)
- Purpose: Validate environment is working

**2. **`sample_etl_pipeline.py` — Main Demo DAG

- Schedule: `@daily`
- Tasks:1. `S3KeySensor` — wait for `s3://any-company-raw-data/incoming/{{ ds }}/data.parquet`

1. `GlueJobOperator` — trigger `any-company-transform-demo` Glue job
2. `RedshiftDataOperator` — run COPY to load transformed data (or mock SQL if no Redshift)
3. `SnsPublishOperator` — send completion notification

- Tags: `["demo", "any-company", "etl"]`

**3. **`container_execution.py` — ECS Demo DAG

- Schedule: None (manual trigger)
- Tasks:1. `EcsRunTaskOperator` — launches Fargate task with custom Docker image from ECR

1. `PythonOperator` — logs the ECS task output

- Purpose: Prove container-based dependency isolation pattern

**4. **`api_triggered.py` — API-Triggered DAG

- Schedule: None (triggered externally via REST API)
- Accepts `conf` parameter with `{"source": "...", "date": "..."}`
- Tasks: PythonOperator that logs the received parameters
- Purpose: Prove REST API trigger pattern

### Lambda Function (Event-Driven Trigger Demo)

- Function: `mwaa-dag-trigger`
- Runtime: Python 3.11
- Trigger: can be manually invoked or wired to EventBridge
- Logic: calls `create_web_login_token` → POST to MWAA REST API → triggers `api_triggered` DAG
- Deployed via CDK (same stack)

### Tests

File: `tests/test_dags.py`

- `test_dags_load_without_errors` — validates all DAGs import cleanly
- `test_sample_etl_task_count` — asserts correct number of tasks
- `test_dag_tags` — verifies tags are present

### Docker Image (for ECS demo)

File: `docker/Dockerfile`

```dockerfile
FROM python:3.11-slim
RUN pip install pandas boto3 pyarrow
COPY app/pipeline.py /app/pipeline.py
WORKDIR /app
ENTRYPOINT ["python", "pipeline.py"]

```

`app/pipeline.py` should simulate an ETL job: read a parquet from S3, apply a simple transform, write back to S3, and print a summary.

## Project Structure

```
mwaa-demo/
├── app.py                          # CDK entry point
├── cdk.json
├── requirements-cdk.txt            # CDK dependencies
├── stacks/
│   ├── __init__.py
│   ├── vpc_stack.py
│   ├── mwaa_stack.py
│   ├── ecs_stack.py
│   ├── lambda_stack.py
│   └── monitoring_stack.py
├── dags/
│   ├── hello_world.py
│   ├── sample_etl_pipeline.py
│   ├── container_execution.py
│   └── api_triggered.py
├── plugins/                        # Empty for now
├── requirements.txt                # Airflow provider deps
├── tests/
│   ├── test_dags.py
│   └── conftest.py
├── docker/
│   ├── Dockerfile
│   └── app/
│       └── pipeline.py
├── lambda/
│   └── trigger_dag.py
├── .github/
│   └── workflows/
│       └── deploy-dags.yml
└── README.md                       # Deploy + teardown instructions

```

## Constraints

- Region: `eu-west-1` (Ireland)
- CDK Python only (no TypeScript)
- No hardcoded credentials — IAM roles everywhere
- Tag all resources: `Project=mwaa-demo`, `Owner=demo-owner`
- Keep costs minimal — tear down after demo
- README must include exact `cdk deploy` and `cdk destroy` commands
- If Redshift Serverless takes too long to provision, mock the SQL step with a PythonOperator that logs "Redshift load simulated"

