# MWAA Serverless Demo Script

## Overview

**Duration:** ~20 minutes
**Audience:** Customer technical stakeholders
**Goal:** Prove MWAA Serverless is production-ready for orchestrating serverless ETL, container workloads, and event-driven pipelines — all deployed via IaC.

---

## Pre-Demo Checklist

- [ ] AWS Console open in `eu-west-1`
- [ ] Terminal ready in `mwaa-demo/serverless/` directory
- [ ] MWAA Airflow UI tab open (get URL below)
- [ ] CloudWatch Dashboard tab open: `mwaa-demo-dashboard`
- [ ] S3 Console open on `any-company-mwaa-demo-dags-123456789012`
- [ ] Ensure `serverless/etl-source/data.csv` exists in the bucket

```bash
# Get Airflow UI login URL
aws mwaa create-web-login-token --name any-company-mwaa-demo --region eu-west-1 --query 'WebServerHostname' --output text

# Verify test data is in place
aws s3 ls s3://any-company-mwaa-demo-dags-123456789012/serverless/etl-source/ --region eu-west-1
```

---

## Demo Flow

### Act 1: Infrastructure as Code (2 min)

**Talking Point:** "Everything you see today was deployed from a single `cdk deploy --all` command. Five stacks, zero manual console clicks."

**Show:**
- Open `app.py` — show the 5 stacks and their dependencies
- Open `stacks/` directory — walk through the file names
- Terminal: show deployed stacks

```bash
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --region eu-west-1 --query 'StackSummaries[?contains(StackName,`Mwaa`)].{Name:StackName,Status:StackStatus}' --output table
```

**Key Message:** "CDK Python, reproducible, teardown in one command."

---

### Act 2: MWAA Serverless Workflows (5 min)

**Talking Point:** "MWAA Serverless removes the need to provision or manage Airflow environments. You define workflows in YAML, upload to S3, and AWS handles scheduling, scaling, and execution."

**Show:**
- Open `serverless-workflows/s3_etl_workflow.yml` — walk through the 4-step ETL pipeline
- Show the MWAA Serverless console: list workflows

```bash
# List active serverless workflows
aws mwaa-serverless list-workflows --region eu-west-1 --query 'Workflows[*].{Name:Name,Status:Status}' --output table
```

**Live Demo — Trigger the ETL workflow:**

```bash
# Step 0: Ensure source data is in place for the ETL pipeline
aws s3 cp test-data/serverless/etl-source/data.csv \
  s3://any-company-mwaa-demo-dags-123456789012/serverless/etl-source/data.csv \
  --region eu-west-1
```

```bash
# Step 1: Trigger the s3-etl workflow
aws mwaa-serverless start-workflow-run \
  --workflow-arn "arn:aws:airflow-serverless:eu-west-1:123456789012:workflow/s3-etl-workflow-serverless-qLobqQ5Dpk" \
  --region eu-west-1
```

```bash
# Step 2: Check run status (replace RUN_ID from above output)
aws mwaa-serverless get-workflow-run \
  --workflow-arn "arn:aws:airflow-serverless:eu-west-1:123456789012:workflow/s3-etl-workflow-serverless-qLobqQ5Dpk" \
  --workflow-run-id <RUN_ID> \
  --region eu-west-1
```

**Key Message:** "4-step ETL: check S3 source, run Glue transform, load to Redshift, send SNS notification. Each task runs in its own Fargate container — fully isolated."

---

### Act 3: Event-Driven Trigger Pattern (5 min)

**Talking Point:** "Workflows can be triggered by any AWS service. Here we show S3 event → Lambda → MWAA Serverless — zero polling, instant reaction."

**Show:**
- Open `serverless-workflows/s3_event_lambda_serverless.yml` — walk through the workflow definition
- Open `lambda/trigger_dag.py` — explain: detects S3 event, extracts bucket/key, calls `StartWorkflowRun`
- Open `stacks/lambda_stack.py` — show S3 event notification config (prefix filter `serverless/incoming/`)

**Live Demo — Drop a file to trigger the s3-event-lambda workflow:**

```bash
# Step 1: Upload a file to the trigger prefix — Lambda fires automatically
aws s3 cp test-data/serverless/incoming/transaction_001.csv \
  s3://any-company-mwaa-demo-dags-123456789012/serverless/incoming/transaction_$(date +%s).csv \
  --region eu-west-1
```

```bash
# Step 2: Confirm Lambda was triggered (wait ~5 seconds)
aws logs tail /aws/lambda/mwaa-dag-trigger --since 2m --region eu-west-1 | head -20
```

```bash
# Step 3: Check the serverless workflow was started
aws mwaa-serverless list-workflow-runs \
  --workflow-arn "arn:aws:airflow-serverless:eu-west-1:123456789012:workflow/s3-event-lambda-serverless-HvYwSyW3qO" \
  --region eu-west-1 --query 'WorkflowRuns[0:3].{Id:WorkflowRunId,Status:Status,Created:CreatedAt}' --output table
```

```bash
# Step 4: Verify the workflow wrote its output to S3
aws s3 ls s3://any-company-mwaa-demo-dags-123456789012/serverless/output/ --region eu-west-1 | tail -5
```

**Then show in Console:**
- Lambda → mwaa-dag-trigger → Monitor tab (invocation spike)
- CloudWatch Dashboard → Lambda Invocations widget updates
- S3 → `serverless/output/` — new file created by the workflow

**Explain the end-to-end flow:**
1. File lands in `serverless/incoming/` prefix
2. S3 Event Notification fires → invokes Lambda
3. Lambda extracts bucket + key from the event record
4. Lambda calls `StartWorkflowRun` on the s3-event-lambda-serverless workflow
5. Workflow executes: writes a confirmation file to `serverless/output/`

**Key Message:** "Any AWS service that can call an API can trigger MWAA Serverless. EventBridge, Step Functions, IoT Rules — all work the same way via `StartWorkflowRun`. No polling, no cron — pure event-driven."

---

### Act 4: Container Execution Pattern (3 min)

**Talking Point:** "For heavy compute or custom dependencies, workflows can launch Fargate tasks with your own Docker images."

**Show:**
- Open `docker/Dockerfile` and `docker/app/pipeline.py`
- Open `dags/container_execution.py` — show the EcsRunTaskOperator
- Show ECS cluster in console (or CLI):

```bash
aws ecs list-tasks --cluster any-company-demo-cluster --region eu-west-1 --output table
```

**Key Message:** "Dependency isolation. Your ETL container has pandas, pyarrow, whatever you need — without polluting the Airflow environment."

---

### Act 5: Monitoring & Observability (3 min)

**Talking Point:** "Full visibility without building anything custom. CloudWatch dashboard deployed by CDK."

**Show:**
- Switch to CloudWatch Dashboard tab (`mwaa-demo-dashboard`)
- Walk through the sections:
  - Classic MWAA: scheduler health, task queue depth
  - Serverless: Lambda trigger metrics, custom workflow metrics
  - Logs Insights: real-time task-level log analysis

**Live Demo — Show metrics populating:**

```bash
# Invoke Lambda directly to show metrics appear
aws lambda invoke --function-name mwaa-dag-trigger --payload '{}' /dev/stdout --region eu-west-1
```

Wait 30 seconds, refresh dashboard — Lambda Invocations widget updates.

**Key Message:** "Metrics populate the moment workflows run. Custom namespace gives you business-level KPIs (runs started, success rate, duration)."

---

### Act 6: CI/CD Pipeline (2 min)

**Talking Point:** "DAG deployment is automated. Push to main, GitHub Actions handles lint, test, and S3 sync."

**Show:**
- Open `.github/workflows/deploy-dags.yml`
- Walk through the 3 stages: lint → test → deploy
- Show the path trigger (only fires on DAG/plugin changes)

**Key Message:** "No manual S3 uploads. OIDC auth, no static credentials. DAGs auto-sync to MWAA within minutes of merge."

---

## Closing Summary (1 min)

| Capability | Proven |
|------------|--------|
| IaC deployment (CDK) | 5 stacks, one command |
| Serverless ETL pipeline | S3 → Glue → Redshift → SNS |
| Event-driven triggers | S3 → Lambda → MWAA Serverless |
| Container workloads | ECS Fargate via EcsRunTaskOperator |
| REST API triggers | Lambda → StartWorkflowRun |
| Monitoring | CloudWatch dashboard + Logs Insights |
| CI/CD | GitHub Actions → S3 auto-sync |

---

## Backup Commands (if something fails)

```bash
# Re-upload test data if bucket was emptied
aws s3 cp test-data/serverless/etl-source/data.csv \
  s3://any-company-mwaa-demo-dags-123456789012/serverless/etl-source/data.csv \
  --region eu-west-1

# Check MWAA environment status
aws mwaa get-environment --name any-company-mwaa-demo --region eu-west-1 \
  --query 'Environment.Status' --output text

# List recent workflow runs
aws mwaa-serverless list-workflow-runs \
  --workflow-arn "arn:aws:airflow-serverless:eu-west-1:123456789012:workflow/s3-etl-workflow-serverless-qLobqQ5Dpk" \
  --region eu-west-1 --query 'WorkflowRuns[0:3].{Id:WorkflowRunId,Status:Status}' --output table

# Force redeploy dashboard if it looks wrong
cd mwaa-demo/serverless && cdk deploy MwaaMonitoringStack --require-approval never --exclusively
```

---

## Visuals to Prepare

1. **Architecture Diagram** — the ASCII diagram from README.md (or recreate in draw.io)
2. **MWAA Serverless Console** — workflows list showing active workflows
3. **CloudWatch Dashboard** — `mwaa-demo-dashboard` (leave open during demo)
4. **S3 Bucket** — show the folder structure (dags/, serverless/, plugins/)
5. **Airflow UI** — show DAG list and recent runs (for classic MWAA portion)
6. **Terminal** — for live CLI commands (use a large font)

---

## Teardown After Demo

```bash
cdk destroy --all --force
```
