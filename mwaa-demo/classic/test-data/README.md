# Test Data for MWAA Serverless Demo

Sample data files organized by workflow type.

## S3 Bucket Structure

```
bucket/
├── serverless/          ← MWAA Serverless workflows
│   ├── incoming/        ← S3 event trigger (s3_event_lambda_serverless)
│   ├── etl-source/      ← ETL cron workflow reads from here
│   ├── output/          ← workflow log outputs
│   └── processed/       ← ETL processed results
└── classic/             ← Classic Airflow DAGs
    ├── incoming/
    ├── etl-source/
    ├── output/
    └── processed/
```

## Usage

### Trigger s3_event_lambda_serverless workflow

```bash
aws s3 cp test-data/serverless/incoming/transaction_001.csv \
  s3://any-company-mwaa-demo-dags-123456789012/serverless/incoming/
```

### Seed data for s3_etl_workflow (5-min cron)

```bash
aws s3 sync test-data/serverless/etl-source/ \
  s3://any-company-mwaa-demo-dags-123456789012/serverless/etl-source/
```

## File Descriptions

| File | S3 Prefix | Purpose |
|------|-----------|---------|
| `serverless/incoming/transaction_001.csv` | `serverless/incoming/` | Triggers s3_event_lambda_serverless on upload |
| `serverless/incoming/transaction_002.csv` | `serverless/incoming/` | Second test file |
| `serverless/etl-source/data.csv` | `serverless/etl-source/` | Source for s3_etl_workflow |
| `serverless/etl-source/metadata.json` | `serverless/etl-source/` | Metadata listed by ETL workflow |
