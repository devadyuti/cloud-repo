"""GenerateCDCRecord Lambda (matches the Modern Data Architecture workshop).

Inserts a single review into the Aurora PostgreSQL "reviews" table. Each insert
becomes a logical-replication change event that the DMS CDC task streams to the
raw bucket under reviews/.

Table schema (from the workshop initdb.py):
    reviews (
        id          serial PRIMARY KEY,
        product_id  varchar(40),
        comment     varchar(1024) NOT NULL,
        rating      int           NOT NULL,
        name        varchar(255)  NOT NULL,
        created_on  timestamp     NOT NULL
    )

Event payloads:
  Insert a review (the workshop payload shape):
    {"product_id": "88236", "comment": "What an amazing product!",
     "rating": "5", "name": "Your name"}
  Create/reset the reviews table (admin actions):
    {"action": "initdb"}    -> CREATE TABLE IF NOT EXISTS reviews (...)
    {"action": "droptable"} -> DROP TABLE IF EXISTS reviews
"""

import json
import os

import boto3
import pg8000.native

SECRET_ARN = os.environ["AURORA_SECRET_ARN"]
DB_HOST = os.environ["AURORA_HOST"]
DB_NAME = os.environ.get("AURORA_DB_NAME", "mdacluster")
DB_PORT = int(os.environ.get("AURORA_PORT", "5432"))

_secrets = boto3.client("secretsmanager")

CREATE_TABLE_SQL = (
    "CREATE TABLE IF NOT EXISTS reviews ("
    "id serial PRIMARY KEY, "
    "product_id varchar(40), "
    "comment varchar(1024) NOT NULL, "
    "rating int NOT NULL, "
    "name varchar(255) NOT NULL, "
    "created_on timestamp NOT NULL)"
)

def _connect():
    secret = json.loads(_secrets.get_secret_value(SecretId=SECRET_ARN)["SecretString"])
    return pg8000.native.Connection(
        user=secret["username"],
        password=secret["password"],
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
    )


def _init_table(conn):
    conn.run(CREATE_TABLE_SQL)
    # REPLICA IDENTITY defaults to the primary key (id), which is what DMS CDC
    # uses to identify rows. The serial PK covers that; no extra setting needed.


def handler(event, _context):
    event = event or {}
    action = event.get("action")

    conn = _connect()
    try:
        if action == "droptable":
            conn.run("DROP TABLE IF EXISTS reviews")
            return {"statusCode": 200, "message": "reviews table dropped"}

        if action == "initdb":
            _init_table(conn)
            return {"statusCode": 200, "message": "reviews table ready"}

        # Default: insert one review from the payload fields (workshop shape).
        # Missing fields are rejected rather than silently defaulted.
        required = ["product_id", "comment", "rating", "name"]
        missing = [f for f in required if f not in event]
        if missing:
            return {"statusCode": 400, "error": f"missing fields: {missing}"}

        # Ensure the table exists so a first insert does not fail.
        _init_table(conn)

        conn.run(
            "INSERT INTO reviews (product_id, comment, rating, name, created_on) "
            "VALUES (:product_id, :comment, :rating, :name, CURRENT_TIMESTAMP)",
            product_id=str(event["product_id"]),
            comment=str(event["comment"]),
            rating=int(event["rating"]),
            name=str(event["name"]),
        )
        return {
            "statusCode": 200,
            "message": "review inserted",
            "review": {k: event[k] for k in required},
        }
    finally:
        conn.close()
