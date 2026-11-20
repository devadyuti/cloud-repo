"""Lambda handler — triggers MWAA DAG via InvokeRestApi."""

import json
import uuid
from datetime import datetime, timezone

import boto3

MWAA_ENV_NAME = "any-company-mwaa-demo"


def handler(event, context):
    """Trigger the api_triggered DAG on MWAA via REST API."""
    client = boto3.client("mwaa", region_name="eu-west-1")

    logical_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Pass Body as a dict — boto3 1.42+ handles serialization
    response = client.invoke_rest_api(
        Name=MWAA_ENV_NAME,
        Path="/dags/api_triggered/dagRuns",
        Method="POST",
        Body={
            "logical_date": logical_date,
            "conf": {
                "message": "Triggered from Lambda",
                "source": "mwaa-classic-dag-trigger",
                "request_id": str(uuid.uuid4()),
            },
        },
    )

    status = response["RestApiStatusCode"]
    body = response["RestApiResponse"]

    print(f"DAG triggered! Status: {status}, Run: {body.get('dag_run_id')}, State: {body.get('state')}")

    return {
        "statusCode": status,
        "body": json.dumps(body, default=str),
    }
