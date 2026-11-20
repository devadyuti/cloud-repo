# MWAA Serverless Demo

Lambda trigger and monitoring for MWAA Serverless workflows. Deployed via AWS CDK (Python) to `eu-west-1`. This project complements the [classic](../classic/) MWAA demo by adding the serverless workflow trigger and its dashboard.

## Architecture

| Stack | Resources |
|-------|-----------|
| `MwaaServerlessLambdaStack` | Lambda function (`mwaa-dag-trigger`), IAM role, S3 event notification on `serverless/incoming/`, workflow execution role (`MwaaServerlessWorkflowRole`) |
| `MwaaServerlessMonitoringStack` | CloudWatch dashboard (`mwaa-serverless-dashboard`) with Logs Insights queries |

The YAML workflow definitions (`serverless-workflows/`) are uploaded to S3 and registered via the `aws mwaa-serverless` CLI — they are not managed by CDK.

## Prerequisites

- Python 3.12+ with virtual environment
- AWS CDK CLI (`npm install -g aws-cdk`)
- AWS CLI v2 configured for account `123456789012` / `eu-west-1`
- The classic MWAA demo deployed (provides the S3 bucket and MWAA environment)

## Deploy CDK Stacks

```bash
cd mwaa-demo/serverless

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies (shares requirements with classic)
pip install -r ../classic/requirements-cdk.txt

# Synthesize (validate templates)
cdk synth

# Deploy all stacks
cdk deploy --all --require-approval never
```

## Deploy Serverless Workflows (YAML)

Workflow definitions live in `serverless-workflows/`. First upload the YAML to S3, then register or update the workflow with the `aws mwaa-serverless` CLI.

### 1. Upload workflow definitions to S3

```bash
# Sync all workflows
aws s3 sync serverless-workflows/ \
  s3://any-company-mwaa-demo-dags-123456789012/dags/serverless-workflows/

# Or upload a single file
aws s3 cp serverless-workflows/s3_etl_workflow.yml \
  s3://any-company-mwaa-demo-dags-123456789012/dags/serverless-workflows/s3_etl_workflow.yml
```

### 2. Create a new workflow

```bash
aws mwaa-serverless create-workflow \
  --name s3-etl-workflow \
  --definition-s3-location "bucketName=any-company-mwaa-demo-dags-123456789012,objectKey=dags/serverless-workflows/s3_etl_workflow.yml" \
  --role-arn arn:aws:iam::123456789012:role/MwaaServerlessWorkflowRole \
  --region eu-west-1
```

### 3. Update an existing workflow

When you update, MWAA Serverless creates a new version and disables scheduling on previous versions automatically.

```bash
aws mwaa-serverless update-workflow \
  --workflow-arn arn:aws:airflow-serverless:eu-west-1:123456789012:workflow/s3-etl-workflow-serverless-qLobqQ5Dpk \
  --definition-s3-location "bucketName=any-company-mwaa-demo-dags-123456789012,objectKey=dags/serverless-workflows/s3_etl_workflow.yml" \
  --role-arn arn:aws:iam::123456789012:role/MwaaServerlessWorkflowRole \
  --region eu-west-1
```

### Verify workflows

```bash
# List workflows in the account
aws mwaa-serverless list-workflows --region eu-west-1

# Check a specific workflow
aws mwaa-serverless get-workflow \
  --workflow-arn arn:aws:airflow-serverless:eu-west-1:123456789012:workflow/s3-etl-workflow-serverless-qLobqQ5Dpk

# Verify files in S3
aws s3 ls s3://any-company-mwaa-demo-dags-123456789012/dags/serverless-workflows/
```

### Remove a workflow

```bash
# Delete from MWAA Serverless
aws mwaa-serverless delete-workflow \
  --workflow-arn arn:aws:airflow-serverless:eu-west-1:123456789012:workflow/hello-world-xyz

# Remove YAML from S3
aws s3 rm s3://any-company-mwaa-demo-dags-123456789012/dags/serverless-workflows/hello_world.yml
```

## Run Tests

```bash
cd mwaa-demo/serverless
python -m pytest tests/ -v
```

## Validate

1. **Test Lambda trigger (direct):**
   ```bash
   aws lambda invoke --function-name mwaa-dag-trigger /tmp/out.json
   cat /tmp/out.json
   ```

2. **Test S3 event trigger:**
   ```bash
   echo "id,name,amount" > /tmp/data.csv
   aws s3 cp /tmp/data.csv \
     s3://any-company-mwaa-demo-dags-123456789012/serverless/incoming/data.csv
   ```
   The `s3_event_lambda_serverless` workflow should start automatically.

3. **Check dashboard:**
   Open CloudWatch → Dashboards → `mwaa-serverless-dashboard`

## Workflow Definitions

| Workflow | File | Trigger | Description |
|----------|------|---------|-------------|
| `hello_world` | `hello_world.yml` | Manual (Studio) | Writes greeting to S3. Validation workflow. |
| `s3_etl_workflow` | `s3_etl_workflow.yml` | Manual (Studio) | Multi-step S3 pipeline: list → write listing → copy to processed. |
| `s3_event_lambda_serverless` | `s3_event_lambda_serverless.yml` | S3 event → Lambda | Auto-triggered on file upload to `serverless/incoming/`. |

> Serverless workflows are managed in **Amazon SageMaker Unified Studio**, not the Airflow UI.

## Teardown

```bash
# Remove CDK stacks
cdk destroy --all

# Remove workflows from S3 (optional — bucket belongs to classic stack)
aws s3 rm --recursive \
  s3://any-company-mwaa-demo-dags-123456789012/dags/serverless-workflows/
```
