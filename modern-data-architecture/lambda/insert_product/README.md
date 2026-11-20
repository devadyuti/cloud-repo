# InsertProduct Lambda

Inserts a single product into the Aurora PostgreSQL `product` table (matches the
Modern Data Architecture workshop `InsertProductFunction`). This is the
**relational** `product` table in Aurora used by the Athena federated-query
part — distinct from the DynamoDB `Product` table used by the Kinesis/Firehose
branch.

The table is assumed to already exist (created/loaded separately); this Lambda
only performs inserts.

## Event payloads

`product_id`, `product_name`, and `product_category` are **required**. `price`
and `quantity` are **optional** — when omitted they bind as `NULL`, so both the
3-field (workshop) and 5-field payloads work.

Minimal (workshop) payload:

```json
{
  "product_id": 999999,
  "product_name": "Zero-ETL Test Product",
  "product_category": "Electronics"
}
```

Full payload with price/quantity:

```json
{
  "product_id": 999999,
  "product_name": "Zero-ETL Test Product",
  "product_category": "Electronics",
  "price": 19.99,
  "quantity": 42
}
```

The INSERT targets all five columns:

```sql
INSERT INTO product
    (product_id, product_name, price, quantity, product_category)
VALUES (:product_id, :product_name, :price, :quantity, :product_category)
```

A missing required field returns `400`; a DB error returns `500`. On success the
`200` response body echoes back all five fields (`price`/`quantity` are `null`
when not supplied).

## Configuration

Credentials come from Secrets Manager; the Aurora endpoint is read from SSM
Parameter Store. Both lookups are overridable via environment variables:

- `AURORA_SECRET_ID` — Secrets Manager id holding `{username, password}` (default `mda-aurora-secret`)
- `AURORA_ENDPOINT_PARAM` — SSM parameter name for the Aurora endpoint (default `AuroraEndpoint`)
- `AURORA_DB_NAME` — default `mdacluster`
- `AURORA_PORT` — default `5432`

## Tests

```bash
cd modern-data-architecture/lambda/insert_product
python -m pytest test_app.py -q
```

`pg8000` and `boto3` are stubbed before import (see `test_app.py`), so the tests
run without the Lambda bundle or any network access.
