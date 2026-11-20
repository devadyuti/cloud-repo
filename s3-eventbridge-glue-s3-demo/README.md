# S3 → EventBridge → Glue ETL Pipeline Demo

Upload a CSV to S3 → EventBridge rule triggers on PutObject → Starts a Glue job → Transforms CSV to Parquet in a target bucket.

## Architecture

```
┌──────────┐     PutObject      ┌──────────────┐     Rule Match     ┌───────────┐
│  S3      │ ──── event ──────▶ │ EventBridge  │ ────────────────▶  │ Glue Job  │
│ (source) │                    │ (default bus)│                    │ (ETL)     │
└──────────┘                    └──────────────┘                    └─────┬─────┘
                                                                          │
                                                                          ▼
                                                                    ┌──────────┐
                                                                    │  S3      │
                                                                    │ (target) │
                                                                    └──────────┘
```

## Prerequisites

- Python 3.12+
- AWS CDK CLI (`npm install -g aws-cdk`)
- AWS credentials configured for `eu-west-1`
- CDK bootstrapped in target account (`cdk bootstrap`)

## Setup

```bash
cd infra
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Deploy

```bash
cd infra
cdk deploy --require-approval never
```

## Test

```bash
# Upload the sample CSV to trigger the pipeline
./scripts/test-pipeline.sh
```

## Clean Up

```bash
cd infra
cdk destroy --force
```

## Structure

```
s3-eventbridge-glue-s3-demo/
├── Demo Spec for Kiro.md    # Requirements spec
├── README.md                # This file
├── infra/                   # CDK infrastructure
│   ├── app.py              # CDK app entry point
│   ├── stacks/
│   │   └── pipeline_stack.py
│   ├── cdk.json
│   └── requirements.txt
├── glue/
│   └── csv_to_parquet.py   # Glue ETL script
├── test-data/
│   └── sample-orders.csv   # Sample CSV for testing
└── scripts/
    └── test-pipeline.sh    # End-to-end test script
```
