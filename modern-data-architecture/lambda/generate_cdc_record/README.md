# GenerateCDCRecord Lambda

In-VPC Lambda that inserts review rows into the Stream 1 Aurora PostgreSQL
`reviews` table. Each insert becomes a logical-replication change event that the
DMS CDC task streams to the raw bucket under `reviews/`.

Table schema (matches the Modern Data Architecture workshop `initdb.py`):

```sql
CREATE TABLE IF NOT EXISTS reviews (
    id          serial PRIMARY KEY,
    product_id  varchar(40),
    comment     varchar(1024) NOT NULL,
    rating      int           NOT NULL,
    name        varchar(255)  NOT NULL,
    created_on  timestamp     NOT NULL
);
```

## Event payloads

Insert a review (the workshop payload shape):

```json
{ "product_id": "88236", "comment": "What an amazing product!", "rating": "5", "name": "Your name" }
```

Admin actions:

```json
{ "action": "initdb" }         // CREATE TABLE IF NOT EXISTS reviews (...)
{ "action": "droptable" }      // DROP TABLE IF EXISTS reviews
```

## Build & deploy

The deployment package vendors `pg8000` (pure-Python Postgres driver, no
compiled deps). `build/` and `package.zip` are git-ignored — rebuild them:

```bash
cd modern-data-architecture/lambda/generate_cdc_record
rm -rf build package.zip
mkdir -p build && cp app.py build/
pip install --target build pg8000
(cd build && zip -qr ../package.zip .)

# Upload to the Stream 0 scripts bucket (referenced by the Stream 1 template)
aws s3 cp package.zip \
  s3://mda-scripts-123456789012-eu-west-1/lambda/generate_cdc_record.zip \
  --region eu-west-1
```

The `mda-stream-1-ingestion` stack references this object via the
`CDCLambdaCodeKey` parameter (`lambda/generate_cdc_record.zip`). After
re-uploading, update the running function:

```bash
aws lambda update-function-code --region eu-west-1 \
  --function-name mda-GenerateCDCRecord \
  --s3-bucket mda-scripts-123456789012-eu-west-1 \
  --s3-key lambda/generate_cdc_record.zip
```

## Environment variables (set by the CloudFormation template)

- `AURORA_SECRET_ARN` — Secrets Manager ARN holding `{username, password}`
- `AURORA_HOST` — Aurora writer endpoint
- `AURORA_DB_NAME` — default `mdacluster`
- `AURORA_PORT` — default `5432`
