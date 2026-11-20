# MWAA Classic Demo Script

## Pre-Demo Checklist

- [ ] AWS Console open in `eu-west-1`
- [ ] Airflow UI tab open (get URL below)
- [ ] CloudWatch Dashboard tab open
- [ ] Lambda console open on `mwaa-classic-dag-trigger`
- [ ] Terminal ready

```bash
# Get Airflow UI URL
aws mwaa create-web-login-token --name any-company-mwaa-demo --region eu-west-1 --query 'WebServerHostname' --output text
```

---

## Demo Flow (~20 min)

---

### 1. Classic Environment Setup (3 min)

**Talking Point:** "Everything is deployed from CDK — reproducible, version-controlled infrastructure."

**Show in IDE:**
- Open `app.py` — 4 stacks wired together (VPC, MWAA, ECS, Monitoring)
- Open `stacks/mwaa_stack.py` — environment config: Airflow 3.2.1, auto-scaling workers, Celery executor, SecretsManager backend

**Show in Console:**
- MWAA Console → `any-company-mwaa-demo` → Status: AVAILABLE
- Point out: environment class, worker scaling (1-5), Airflow version

**Show in Terminal:**
```bash
# All stacks deployed
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --region eu-west-1 \
  --query 'StackSummaries[?contains(StackName,`Mwaa`)].{Name:StackName,Status:StackStatus}' --output table
```

**Key Message:** "One `cdk deploy --all`, full environment ready. No manual console clicks."

---

### 2. DAG Workflow & Visualisation (5 min)

**Talking Point:** "Let's look at a production-grade data lake ETL pipeline — medallion architecture, quality gates, branching logic."

**Show in Airflow UI:**
- Click `data_lake_etl` → show the graph view (top-left icon)
- Walk through the nodes:
  1. S3 sensor waits for raw data
  2. Glue Crawler discovers schema
  3. Glue ETL job transforms (bronze → silver)
  4. Athena runs quality checks
  5. Quality gate branches: pass → Redshift, fail → quarantine + alert

**Show in IDE:**
- Open `dags/data_lake_etl.py` — point out BranchPythonOperator, real Glue/Athena/Redshift operators

**Trigger the pipeline:**
```bash
# Ensure test data exists
aws s3 ls s3://any-company-mwaa-demo-dags-123456789012/landing/transactions/dt=$(date +%Y-%m-%d)/ --region eu-west-1
```

If no data, seed it:
```bash
aws s3 cp mwaa-demo/classic/test-data/etl-source/transactions.csv \
  "s3://any-company-mwaa-demo-dags-123456789012/landing/transactions/dt=$(date +%Y-%m-%d)/data.csv" \
  --region eu-west-1
```

Then trigger from Airflow UI (play button on `data_lake_etl`).

**While it runs, explain each step as it lights up green in the UI.**

**Key Message:** "Real AWS services orchestrated by Airflow. Glue for ETL, Athena for quality, Redshift for the warehouse. Branch logic decides pass or quarantine — no bad data reaches analysts."

---

### 3. API-Driven Workflow Calls (3 min)

**Talking Point:** "Any application can trigger MWAA workflows programmatically — Lambda, Step Functions, EventBridge, or any AWS SDK client."

**Show in Lambda Console:**
- Open `mwaa-classic-dag-trigger`
- Click **Test** tab → click **Test** button
- Show the response: DAG triggered, state = queued

**Show in Airflow UI:**
- Switch to `api_triggered` DAG
- New run appears, goes green
- Point out `triggered_by: rest_api` in the run details

**Show the Lambda code (in IDE):**
```python
# Key line — this is all it takes:
response = client.invoke_rest_api(
    Name="any-company-mwaa-demo",
    Path="/dags/api_triggered/dagRuns",
    Method="POST",
    Body={...}
)
```

**Check your email** — SNS notification should arrive.

**Key Message:** "One API call. Any event source — S3 upload, database change, user action — can start an Airflow workflow. Zero polling."

---

### 4. External Service Integration (3 min)

**Talking Point:** "MWAA can call any external REST API — partner systems, SaaS platforms, internal microservices. Credentials managed via Secrets Manager."

**Show in Airflow UI:**
- Trigger `external_system_integration` (play button)
- Watch it progress: API call → transform → S3 write → SNS

**Explain while it runs:**
- "This DAG calls our car search API — a real REST endpoint"
- "Airflow handles retries, timeouts, and error routing"
- "Connection string stored in Secrets Manager — no credentials in code"

**After completion, verify in S3:**
```bash
aws s3 ls s3://any-company-mwaa-demo-dags-123456789012/external-api/car-search/ --recursive --region eu-west-1
```

**Show the data:**
```bash
aws s3 cp s3://any-company-mwaa-demo-dags-123456789012/external-api/car-search/$(date +%Y-%m-%d)/ - --recursive --region eu-west-1 | head -20
```

**Key Message:** "Pull data from any system into your data lake — scheduled or on-demand. MWAA handles the orchestration, retries, and monitoring."

---

### 5. Workflow Failure & Restart (2 min)

**Talking Point:** "Failures happen. Airflow gives you granular control — retry from the exact failed step, no full re-run needed."

**Show in Airflow UI:**
- Find a previously failed run (from earlier today)
- Click the failed task (red)
- Show the **Clear** option — "this resets the task and all downstream"
- Explain: "Fix the issue, clear the task, pipeline continues from where it left off"

**Also show:**
- Retry count in task details
- Log viewer with the actual error
- Task duration for SLA monitoring

**Key Message:** "No wasted compute. Fix the problem, clear the task, pipeline resumes. Every task is independently restartable."

---

### 6. Classic vs Serverless (3 min)

**Talking Point:** "Both are MWAA. Different trade-offs for different workloads."

| | Classic | Serverless |
|---|---|---|
| **Authoring** | Python (full flexibility) | YAML (declarative) |
| **Operators** | Any Airflow operator | AWS-native only |
| **Scaling** | Worker auto-scale (1-N) | Scale to zero |
| **UI** | Airflow Web UI | SageMaker Unified Studio |
| **Use case** | Complex logic, custom code, ECS, branching | Simple AWS service orchestration |
| **Cost** | Pay for idle workers | Pay per execution |

**When to use Classic:**
- Custom Python logic (transforms, validations, ML)
- ECS/Fargate container orchestration
- Complex branching (quality gates)
- HTTP calls to external systems

**When to use Serverless:**
- Simple S3 → Glue → Redshift pipelines
- No custom code needed
- Bursty, infrequent workloads
- Want zero management

**Key Message:** "Use both. Classic for complex orchestration, Serverless for simple pipelines. Same MWAA platform, choose the right tool per workflow."

---

## Backup Commands

```bash
# Check MWAA status
aws mwaa get-environment --name any-company-mwaa-demo --region eu-west-1 --query 'Environment.Status' --output text

# Re-seed test data (if needed)
aws s3 cp mwaa-demo/classic/test-data/classic/transactions.csv "s3://any-company-mwaa-demo-dags-123456789012/landing/transactions/dt=$(date +%Y-%m-%d)/data.csv" --region eu-west-1

# Re-sync DAGs (if you edited locally)
aws s3 sync mwaa-demo/classic/dags/ s3://any-company-mwaa-demo-dags-123456789012/dags/ --region eu-west-1

# Trigger DAG via CLI (backup if UI is slow)
aws mwaa invoke-rest-api --name any-company-mwaa-demo --path "/dags/data_lake_etl/dagRuns" --method POST --body '{"logical_date":"2026-08-07T12:00:00Z","conf":{}}' --region eu-west-1
```

---

## If Something Fails During Demo

1. **Task stuck/failed:** Click task → Clear → explain "retry from failure point"
2. **DAG disappeared:** Check import errors in Airflow UI → Admin → Import Errors
3. **Environment updating:** "MWAA is applying a config change — give it 2 min" (show CloudWatch dashboard while waiting)
4. **No logs:** "Logs take a few seconds to stream to CloudWatch" — move to next topic and come back
