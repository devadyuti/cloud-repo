# Demo: S3 → EventBridge (Rule + Scheduler) → Glue ETL Pipeline

## Overview

Two trigger patterns for a Glue ETL job:
1. **Event-driven:** Upload CSV to S3 → EventBridge Rule → Lambda (thin wrapper) → Glue Job
2. **Scheduled:** EventBridge Scheduler → Glue `StartJobRun` directly (no Lambda needed)

## Architecture

```
┌──────────┐     PutObject      ┌──────────────┐     Rule Match     ┌───────────┐
Pattern 1 — Event-driven (reactive):

│  S3      │ ──── event ──────▶ │ EventBridge  │ ──────────────▶    │  Lambda   │ ──────────────▶   │ Glue Job  │
│ (source) │                    │    Rule      │                    │ (trigger) │                   │ (ETL)     │
└──────────┘                    └──────────────┘                    └──────────┘                   └─────┬─────┘

Pattern 2 — Scheduled (proactive):

┌───────────────────┐     cron/rate       ┌───────────┐
│  EventBridge      │ ── StartJobRun ──▶  │ Glue Job  │
│  Scheduler        │    (direct API)     │ (ETL)     │
└───────────────────┘                     └─────┬─────┘
                                                │
                                                ▼
                                          ┌──────────┐
                                          │  S3      │
                                          │ (target) │
                                          └──────────┘
                                                                          │
                                                                          ▼
                                                                    ┌──────────┐
                                                                    │  S3      │
                                                                    │ (target) │
                                                                    └──────────┘
```

## Requirements

### Functional

1. When a `.csv` file is uploaded to the source S3 bucket under the `input/` prefix, the system must automatically trigger a Glue ETL job.
2. The Glue job must read the uploaded CSV, transform it to Parquet format, and write the output to the target S3 bucket under `output/`.
3. The source file key must be passed dynamically to the Glue job as a parameter.
4. A scheduled trigger must run the Glue job daily at 8am (Europe/London) against a known input path.
5. Failed events must not be lost — use DLQ or retry configuration.

### Non-Functional

- Glue job timeout: 5 minutes max
- Glue job type: Spark (for demo; Python Shell also acceptable)
- Region: `eu-west-1`
- Timezone: `Europe/London`
- Environment suffix: `dev`

## Infrastructure Resources

| Resource | Logical Name | Configuration |
|----------|-------------|---------------|
| S3 Bucket (source) | `demo-source-dev` | EventBridge notifications **enabled** |
| S3 Bucket (target) | `demo-target-dev` | Standard storage |
| EventBridge Rule | `s3-csv-upload-rule` | Default bus, pattern matches Object Created for `.csv` in `input/` |
| Lambda (trigger) | `glue-trigger-fn` | Receives EventBridge event, calls `glue:StartJobRun` |
| EventBridge Schedule | `daily-glue-etl-schedule` | `cron(0 8 * * ? *)`, Europe/London, target: Glue StartJobRun |
| Glue Job | `csv-to-parquet-job` | Spark 3.5, Glue 5.0, 2 DPU, timeout 300s |
| IAM Role (Glue) | `glue-etl-role` | S3 read on source bucket, S3 write on target bucket, Glue service trust |
| IAM Role (Lambda) | `lambda-trigger-role` | `glue:StartJobRun`, CloudWatch Logs |
| IAM Role (Scheduler) | `scheduler-glue-role` | `glue:StartJobRun` with `scheduler.amazonaws.com` trust |

## EventBridge Rule

### Event Pattern

```json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "detail": {
    "bucket": {
      "name": ["demo-source-dev"]
    },
    "object": {
      "key": [{ "suffix": ".csv" }]
    }
  }
}
```

### Target Configuration

- **Target:** AWS Glue → `StartJobRun`
- **Job name:** `csv-to-parquet-job`
- **Input Transformer:**

```json
{
  "InputPathsMap": {
    "key": "$.detail.object.key",
    "bucket": "$.detail.bucket.name"
  },
  "InputTemplate": "{\"--source_bucket\": \"<bucket>\", \"--source_key\": \"<key>\"}"
}
```

### Retry & DLQ

- Retry attempts: 2
- Max event age: 300 seconds
- DLQ: SQS queue `demo-eventbridge-dlq-dev`

## Lambda Trigger Function (`glue_trigger.py`)

Thin wrapper — receives EventBridge event, starts Glue job with S3 key:

```python
import boto3
import os

glue = boto3.client('glue')

def handler(event, context):
    bucket = event['detail']['bucket']['name']
    key = event['detail']['object']['key']
    
    response = glue.start_job_run(
        JobName=os.environ['GLUE_JOB_NAME'],
        Arguments={
            '--source_bucket': bucket,
            '--source_key': key
        }
    )
    print(f"Started Glue job run: {response['JobRunId']}")
    return {'statusCode': 200, 'jobRunId': response['JobRunId']}
```

**Environment variables:**
- `GLUE_JOB_NAME`: `csv-to-parquet-job`

**Runtime:** Python 3.12 | **Timeout:** 30s | **Memory:** 128 MB

## EventBridge Scheduler (Pattern 2 — Scheduled)

### Schedule Configuration

| Setting | Value |
|---------|-------|
| Name | `daily-glue-etl-schedule` |
| Expression | `cron(0 8 * * ? *)` (daily at 8am) |
| Timezone | `Europe/London` |
| Flexible window | 15 minutes |
| State | ENABLED |

### Target — Glue StartJobRun (Universal Target)

**ARN:** `arn:aws:scheduler:::aws-sdk:glue:startJobRun`

**Input payload:**
```json
{
  "JobName": "csv-to-parquet-job",
  "Arguments": {
    "--source_bucket": "demo-source-dev",
    "--source_key": "input/daily-feed.csv"
  }
}
```

### Scheduler IAM Role (`scheduler-glue-role`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["glue:StartJobRun"],
      "Resource": "arn:aws:glue:eu-west-1:*:job/csv-to-parquet-job"
    }
  ]
}
```

**Trust policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "scheduler.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## S3 Bucket Configuration (Source)

```yaml
Properties:
  BucketName: demo-source-dev
  NotificationConfiguration:
    EventBridgeConfiguration:
      EventBridgeEnabled: true
```

## Glue Job Script (`csv_to_parquet.py`)

```python
import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext

args = getResolvedOptions(sys.argv, ['source_bucket', 'source_key'])

sc = SparkContext()
glueContext = GlueContext(sc)

# Read CSV from source
input_path = f"s3://{args['source_bucket']}/{args['source_key']}"
df = glueContext.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": [input_path]},
    format="csv",
    format_options={"withHeader": True}
)

# Write as Parquet to target
output_key = args['source_key'].replace('input/', '').replace('.csv', '')
output_path = f"s3://demo-target-dev/output/{output_key}"

glueContext.write_dynamic_frame.from_options(
    frame=df,
    connection_type="s3",
    connection_options={"path": output_path},
    format="parquet"
)

print(f"Successfully transformed {input_path} → {output_path}")
```

## IAM Policies

### Glue Execution Role (`glue-etl-role`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::demo-source-dev/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::demo-target-dev/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:eu-west-1:*:*"
    }
  ]
}
```

**Trust policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "glue.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### EventBridge Role (`eb-glue-role`)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["glue:StartJobRun"],
      "Resource": "arn:aws:glue:eu-west-1:*:job/csv-to-parquet-job"
    }
  ]
}
```

**Trust policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "events.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## Test Data (`sample-orders.csv`)

```csv
order_id,customer,product,quantity,price,order_date
1001,Acme Corp,Widget A,50,12.99,2026-06-15
1002,Beta Ltd,Widget B,25,24.50,2026-06-15
1003,Gamma Inc,Widget A,100,12.99,2026-06-16
1004,Acme Corp,Widget C,10,49.99,2026-06-16
1005,Delta Co,Widget B,75,24.50,2026-06-17
```

## Verification Steps

### Demo Flow — Pattern 1 (Event-driven, show first)

| Step | Action | What audience sees |
|------|--------|-------------------|
| 1 | Upload `sample-orders.csv` to `s3://demo-source-dev/input/` | S3 console or CLI |
| 2 | Show EventBridge rule matched | EventBridge console → Monitoring (invocation +1) |
| 3 | Show Lambda invoked | CloudWatch Logs → Glue job run ID printed |
| 4 | Show Glue job started & succeeded | Glue console → Job runs → Succeeded |
| 5 | Show Parquet output | S3 target bucket → `output/sample-orders/` |
| 6 | (Bonus) Query with Athena | `SELECT * FROM ... LIMIT 5` on Parquet |

### Demo Flow — Pattern 2 (Scheduled, show second)

| Step | Action | What audience sees |
|------|--------|-------------------|
| 1 | Show the Scheduler in console | EventBridge → Schedules → `daily-glue-etl-schedule` |
| 2 | Highlight: cron expression, timezone, flexible window | No Lambda in the middle — direct API call |
| 3 | Click "Invoke" (or wait for schedule) | Glue job starts without any Lambda |
| 4 | Show Glue job run | Same Glue job, same output — different trigger |

**Key message:** *"Event-driven for reactive (file lands → process it). Scheduled for proactive (run ETL every morning). Both serverless, no cron servers."*

## IaC Preference

Use **AWS CDK (TypeScript)** or **SAM (YAML)** — whichever Kiro scaffolds best.
