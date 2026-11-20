# Implementation Plan: MWAA Serverless Demo

## Overview

Build a working end-to-end Amazon MWAA Serverless demo deployed via CDK Python (eu-west-1). The implementation creates VPC networking, MWAA Serverless environment, ECS Fargate cluster, Lambda DAG trigger, CloudWatch monitoring, four Airflow DAGs, a Docker ETL image, CI/CD pipeline, and supporting tests. Project folder is `mwaa-serverless-demo/` at the workspace root.

## Tasks

- [x] 1. Create project scaffold and CDK entry point
  - **Requirements:** FR-1
  - Create `mwaa-serverless-demo/` directory at workspace root
  - Create `app.py` with CDK app importing all 5 stacks (VpcStack, MwaaStack, EcsStack, LambdaStack, MonitoringStack), setting region to `eu-west-1`, and applying tags `Project=mwaa-demo`, `Owner=demo-owner` to all stacks
  - Create `cdk.json` with `"app": "python3 app.py"` and recommended CDK context flags
  - Create `requirements-cdk.txt` with `aws-cdk-lib>=2.150.0` and `constructs>=10.0.0,<11.0.0`
  - Create `stacks/__init__.py` (empty)
  - Create `plugins/.gitkeep` (empty placeholder)
  - Files: `mwaa-serverless-demo/app.py`, `mwaa-serverless-demo/cdk.json`, `mwaa-serverless-demo/requirements-cdk.txt`, `mwaa-serverless-demo/stacks/__init__.py`, `mwaa-serverless-demo/plugins/.gitkeep`

- [x] 2. Build VPC stack (lookup existing VPC)
  - **Requirements:** FR-2
  - Create `stacks/vpc_stack.py` with a `VpcStack` class extending `Stack`
  - Use `ec2.Vpc.from_lookup()` to reference an existing VPC by VPC ID (passed via CDK context variable `vpc_id`) or by tag/name
  - Select existing private subnets (with egress/NAT) for MWAA ENIs using subnet filters or explicit subnet IDs from CDK context
  - Create security group `mwaa-demo-sg` within the looked-up VPC: self-referencing ingress (all traffic) and all outbound allowed
  - Do NOT create new VPC, subnets, NAT Gateway, or VPC endpoints — assume these already exist in the target account
  - Expose `self.vpc`, `self.private_subnets`, and `self.mwaa_sg` as stack properties
  - Add CDK context variables to `cdk.json`: `vpc_id` (required), optionally `private_subnet_ids` for explicit subnet selection
  - Files: `mwaa-serverless-demo/stacks/vpc_stack.py`

- [x] 3. Build MWAA stack
  - **Requirements:** FR-3
  - Create `stacks/mwaa_stack.py` with a `MwaaStack` class that accepts `vpc` parameter
  - Create S3 bucket named `any-company-mwaa-demo-dags-{account_id}` with `RemovalPolicy.DESTROY` and `auto_delete_objects=True`
  - Upload placeholder objects to establish `dags/`, `plugins/` prefixes
  - Create IAM execution role with policies for: S3 (bucket access), Glue (StartJobRun, GetJobRun), Redshift Data API (ExecuteStatement, DescribeStatement), SNS (Publish), ECS (RunTask, DescribeTask), CloudWatch Logs, and SQS
  - Create `CfnEnvironment` for MWAA Serverless with: name `any-company-mwaa-demo`, source bucket ARN, `dags_s3_path="dags/"`, `requirements_s3_path="requirements.txt"`, public web server access, network configuration using private subnets and security group, execution role ARN
  - Expose `self.environment_name` as stack property
  - Files: `mwaa-serverless-demo/stacks/mwaa_stack.py`

- [x] 4. Build ECS stack
  - **Requirements:** FR-10
  - Create `stacks/ecs_stack.py` with `EcsStack` class accepting `vpc` parameter
  - Create ECS Fargate cluster named `any-company-demo-cluster`
  - Create ECR repository `any-company-etl-container` with `RemovalPolicy.DESTROY` and image tag mutability
  - Create Fargate task definition `any-company-etl-task` with 0.5 vCPU, 1024 MB memory
  - Add container to task definition referencing ECR repo image, with CloudWatch log driver
  - Grant task role permissions to read/write S3
  - Expose `self.cluster`, `self.task_definition`, `self.ecr_repo` as properties
  - Files: `mwaa-serverless-demo/stacks/ecs_stack.py`

- [x] 5. Build Lambda stack
  - **Requirements:** FR-9
  - Create `stacks/lambda_stack.py` with `LambdaStack` class accepting `mwaa_environment_name` parameter
  - Create Lambda function `mwaa-dag-trigger` with Python 3.11 runtime, handler pointing to `lambda/trigger_dag.handler`, 30s timeout
  - Set environment variable `MWAA_ENV_NAME` to the passed environment name
  - Grant Lambda role permissions: `airflow:CreateWebLoginToken` on the MWAA environment ARN
  - Bundle `lambda/` directory as the code asset
  - Files: `mwaa-serverless-demo/stacks/lambda_stack.py`

- [x] 6. Build Monitoring stack
  - **Requirements:** FR-12
  - Create `stacks/monitoring_stack.py` with `MonitoringStack` class accepting `mwaa_environment_name`
  - Create CloudWatch dashboard `mwaa-demo-dashboard`
  - Add 4 metric widgets in a 2x2 grid: QueuedTasks, RunningTasks, SchedulerHeartbeat, TaskInstanceFailures — all using namespace `AWS/MWAA` with dimension `Environment=any-company-mwaa-demo`
  - Files: `mwaa-serverless-demo/stacks/monitoring_stack.py`

- [x] 7. Write DAG files
  - **Requirements:** FR-5, FR-6, FR-7, FR-8
  - Create `dags/hello_world.py`: single PythonOperator printing "Hello from MWAA Serverless", `schedule=None`, `start_date=datetime(2024, 1, 1)`, `catchup=False`
  - Create `dags/sample_etl_pipeline.py`: `schedule="@daily"`, tags `["demo", "any-company", "etl"]`, tasks: `S3KeySensor` (waits for `s3://any-company-raw-data/incoming/{{ ds }}/data.parquet`) → `GlueJobOperator` (job `any-company-transform-demo`) → `PythonOperator` logging "Redshift load simulated" (mock fallback) → `SnsPublishOperator` (topic ARN from Variable)
  - Create `dags/container_execution.py`: `schedule=None`, `EcsRunTaskOperator` launching Fargate task on `any-company-demo-cluster` with `any-company-etl-task` definition → `PythonOperator` logging task completion
  - Create `dags/api_triggered.py`: `schedule=None`, accepts `dag_run.conf` with `source` and `date` keys, `PythonOperator` that logs the received parameters
  - Files: `mwaa-serverless-demo/dags/hello_world.py`, `mwaa-serverless-demo/dags/sample_etl_pipeline.py`, `mwaa-serverless-demo/dags/container_execution.py`, `mwaa-serverless-demo/dags/api_triggered.py`

- [x] 8. Write Airflow requirements.txt
  - **Requirements:** FR-3
  - Create `requirements.txt` with pinned versions of: `apache-airflow-providers-amazon` (covers S3, Glue, ECS, Redshift, SNS operators)
  - Files: `mwaa-serverless-demo/requirements.txt`

- [x] 9. Write Docker image files
  - **Requirements:** FR-11
  - Create `docker/Dockerfile`: base `python:3.11-slim`, install `pandas`, `boto3`, `pyarrow`, copy `app/pipeline.py`, set entrypoint
  - Create `docker/app/pipeline.py`: reads a parquet file from S3 (path from env var or arg), applies a simple transform (e.g., add computed column), writes result back to S3, prints row count summary
  - Files: `mwaa-serverless-demo/docker/Dockerfile`, `mwaa-serverless-demo/docker/app/pipeline.py`

- [x] 10. Write Lambda trigger function
  - **Requirements:** FR-9
  - Create `lambda/trigger_dag.py` with `handler(event, context)` function
  - Use boto3 `mwaa` client to call `create_web_login_token` for the environment
  - Extract the web server hostname and token from the response
  - POST to `https://{hostname}/api/v1/dags/api_triggered/dagRuns` with `Authorization: Bearer {token}` header and body `{"conf": {"source": "lambda", "date": "<today>"}}`
  - Return response status and body
  - Files: `mwaa-serverless-demo/lambda/trigger_dag.py`

- [x] 11. Write DAG tests
  - **Requirements:** FR-13
  - Create `tests/conftest.py` with pytest fixtures: add `dags/` to sys.path, set required Airflow env vars (`AIRFLOW_HOME` to temp dir)
  - Create `tests/test_dags.py` with tests: `test_dags_load_without_errors` (imports all DAG files, asserts no import errors), `test_sample_etl_task_count` (asserts 4 tasks in sample_etl_pipeline), `test_dag_tags` (asserts `["demo", "any-company", "etl"]` present on sample_etl_pipeline)
  - Files: `mwaa-serverless-demo/tests/conftest.py`, `mwaa-serverless-demo/tests/test_dags.py`

- [x] 12. Write CI/CD pipeline
  - **Requirements:** FR-4, NFR-2
  - Create `.github/workflows/deploy-dags.yml` triggered on push to `main` when paths `dags/**`, `requirements.txt`, or `plugins/**` change
  - Define `lint` job: checkout, install pylint, run `pylint dags/ --disable=all --enable=E`
  - Define `test` job: checkout, install pytest + apache-airflow, run `pytest tests/ -v`
  - Define `deploy` job (needs lint + test): configure AWS credentials via `aws-actions/configure-aws-credentials` with OIDC role ARN from secrets, run `aws s3 sync dags/ s3://${{ secrets.MWAA_BUCKET }}/dags/ --delete` and `aws s3 cp requirements.txt s3://${{ secrets.MWAA_BUCKET }}/requirements.txt`
  - Files: `mwaa-serverless-demo/.github/workflows/deploy-dags.yml`

- [x] 12b. Create MWAA Serverless workflows
  - **Requirements:** FR-5, FR-6
  - Create `serverless-workflows/` directory at project root for YAML workflow definitions
  - Create S3 bucket for MWAA Serverless workflows (versioning enabled, block public access) — can reuse existing DAGs bucket or create separate `any-company-mwaa-serverless-workflows-{account_id}` bucket via CDK
  - Create IAM execution role `mwaa-serverless-workflow-role` with trust policy for `airflow-serverless.amazonaws.com`, permissions for S3, CloudWatch Logs, and KMS
  - Install the DAG converter: `pip install python-to-yaml-dag-converter-mwaa-serverless`
  - Convert `dags/hello_world.py` to YAML: `dag-converter convert dags/hello_world.py --output serverless-workflows/`
  - Convert `dags/api_triggered.py` to YAML: `dag-converter convert dags/api_triggered.py --output serverless-workflows/`
  - Manually create a YAML workflow `serverless-workflows/s3_etl_workflow.yml` demonstrating S3 operations (list objects, copy, transform) since the ETL pipeline DAG uses operators not yet supported in Serverless
  - Upload YAML workflows to S3: `aws s3 sync serverless-workflows/ s3://{bucket}/workflows/`
  - Create workflows via CLI: `aws mwaa-serverless create-workflow --name hello-world-serverless --definition-s3-location '{"Bucket": "{bucket}", "ObjectKey": "workflows/hello_world.yml"}' --execution-role-arn {role_arn}`
  - Trigger a workflow run: `aws mwaa-serverless start-workflow-run --workflow-arn {arn}`
  - Verify workflow reaches `SUCCESS` state: `aws mwaa-serverless get-workflow-run --workflow-arn {arn} --workflow-run-id {run_id}`
  - Files: `mwaa-serverless-demo/serverless-workflows/hello_world.yml`, `mwaa-serverless-demo/serverless-workflows/api_triggered.yml`, `mwaa-serverless-demo/serverless-workflows/s3_etl_workflow.yml`

- [x] 13. Deploy to AWS and validate
  - **Requirements:** FR-1, FR-3, FR-5
  - Run `pip install -r requirements-cdk.txt` to install CDK dependencies
  - Run `cdk bootstrap aws://{account}/eu-west-1` if not already bootstrapped
  - Run `cdk synth` to verify templates synthesize without errors
  - Run `cdk deploy --all -c vpc_id={existing_vpc_id} --require-approval never` to deploy all stacks
  - Build and push Docker image to ECR: `docker build -t any-company-etl-container docker/` then tag and push to the ECR repo created by the ECS stack
  - Upload DAGs to S3: `aws s3 sync dags/ s3://{bucket}/dags/` and `aws s3 cp requirements.txt s3://{bucket}/requirements.txt`
  - Validate MWAA environment reaches `AVAILABLE` status: `aws mwaa get-environment --name any-company-mwaa-demo --query 'Environment.Status'`
  - Open Airflow UI and manually trigger `hello_world` DAG to confirm environment works
  - Invoke Lambda trigger: `aws lambda invoke --function-name mwaa-dag-trigger out.json` and verify `api_triggered` DAG runs
  - Check CloudWatch dashboard shows metrics populating
  - Ask user to confirm VPC ID and account details before deploying

- [x] 14. Write README
  - **Requirements:** NFR-4
  - Create `README.md` with sections: Overview, Architecture (text description referencing design diagram), Prerequisites (Python 3.12+, AWS CDK, AWS CLI, Docker), Quick Start (clone, pip install, cdk bootstrap, cdk deploy --all -c vpc_id=vpc-xxx), Validate (open Airflow UI, trigger hello_world, check CloudWatch dashboard), DAG Descriptions (table), CI/CD Setup (GitHub secrets needed), Teardown (`cdk destroy --all`), Cost Notes (uses existing VPC, teardown after demo)
  - Files: `mwaa-serverless-demo/README.md`
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- MWAA Serverless is used (not Classic) for auto-scaling and simpler config
- Redshift step is mocked with a PythonOperator fallback to avoid long provisioning times
- All resources in `eu-west-1` (Ireland)
- Existing VPC is used via `Vpc.from_lookup()` — pass VPC ID at deploy time with `-c vpc_id=vpc-xxx`
- Ensure the existing VPC has private subnets with NAT egress and VPC endpoints for S3, Glue, SQS, CloudWatch Logs, KMS, STS, ECR
