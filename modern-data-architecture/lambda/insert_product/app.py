"""InsertProduct Lambda (matches the Modern Data Architecture workshop
InsertProductFunction).

Inserts a single product into the Aurora PostgreSQL "product" table. This is
the RELATIONAL product table in Aurora used by the Athena federated-query part,
distinct from the DynamoDB "Product" table used by the Kinesis/Firehose branch.

Event payload (workshop shape; price and quantity optional):
    {
      "product_id": 999999,
      "product_name": "Zero-ETL Test Product",
      "product_category": "Electronics",
      "price": 19.99,      # optional
      "quantity": 100       # optional
    }

Credentials come from Secrets Manager (mda-aurora-secret); the Aurora endpoint
is read from SSM Parameter Store (AuroraEndpoint). Matches the workshop, which
inserts only product_id / product_name / product_category (price and quantity
are left null / populated by the bulk initdb load).
"""

import json
import logging
import os

import boto3
import pg8000.native

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Secret id and endpoint SSM param name are overridable via env, defaulting to
# this project's names.
SECRET_ID = os.environ.get("AURORA_SECRET_ID", "mda-aurora-secret")
ENDPOINT_PARAM = os.environ.get("AURORA_ENDPOINT_PARAM", "AuroraEndpoint")
DB_NAME = os.environ.get("AURORA_DB_NAME", "mdacluster")
DB_PORT = int(os.environ.get("AURORA_PORT", "5432"))

_secrets = boto3.client("secretsmanager")
_ssm = boto3.client("ssm")


def lambda_handler(event, _context):
    event = event or {}
    logger.info("Received event: %s", json.dumps(event))

    product_id = event.get("product_id")
    product_name = event.get("product_name")
    product_category = event.get("product_category")
    # price and quantity are optional; if omitted they are left NULL.
    price = event.get("price")
    quantity = event.get("quantity")

    if not all([product_id, product_name, product_category]):
        return {
            "statusCode": 400,
            "body": json.dumps(
                "Missing required fields: product_id, product_name, product_category"
            ),
        }

    secret = json.loads(_secrets.get_secret_value(SecretId=SECRET_ID)["SecretString"])
    db_endpoint = _ssm.get_parameter(Name=ENDPOINT_PARAM)["Parameter"]["Value"]

    conn = pg8000.native.Connection(
        user=secret["username"],
        password=secret["password"],
        host=db_endpoint,
        database=DB_NAME,
        port=DB_PORT,
    )
    try:
        # Insert all 5 columns; price/quantity bind as NULL when not supplied,
        # so both the 3-field and 5-field payloads work.
        conn.run(
            "INSERT INTO product "
            "(product_id, product_name, price, quantity, product_category) "
            "VALUES (:product_id, :product_name, :price, :quantity, :product_category)",
            product_id=product_id,
            product_name=product_name,
            price=price,
            quantity=quantity,
            product_category=product_category,
        )
        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Product inserted successfully",
                    "product_id": product_id,
                    "product_name": product_name,
                    "price": price,
                    "quantity": quantity,
                    "product_category": product_category,
                }
            ),
        }
    except Exception as e:  # noqa: BLE001
        logger.error("Error inserting product: %s", e, exc_info=True)
        return {"statusCode": 500, "body": json.dumps(f"Error inserting product: {str(e)}")}
    finally:
        conn.close()
