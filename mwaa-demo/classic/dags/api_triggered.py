"""
API-Triggered DAG — Simple workflow triggered externally via Lambda/REST API.

Accepts dag_run.conf with a message, writes it to S3 as proof of execution.
Schedule: None (API-only trigger)
Tags: ["demo", "api"]
"""

import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.sns import SnsPublishOperator

DATALAKE_BUCKET = "any-company-mwaa-demo-dags-123456789012"
SNS_TOPIC = "arn:aws:sns:eu-west-1:123456789012:mwaa-etl-notifications"

default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
    "execution_timeout": timedelta(minutes=5),
}


def process_api_request(**kwargs):
    """Process the API request and write confirmation to S3."""
    import boto3

    conf = kwargs["dag_run"].conf or {}
    ts = kwargs["ts"]
    ts_nodash = kwargs["ts_nodash"]

    message = conf.get("message", "Triggered via API")
    source = conf.get("source", "unknown")

    output = {
        "status": "success",
        "message": message,
        "source": source,
        "triggered_at": ts,
        "dag_id": "api_triggered",
    }

    s3_client = boto3.client("s3")
    key = f"api-triggered/runs/{ts_nodash}.json"

    s3_client.put_object(
        Bucket=DATALAKE_BUCKET,
        Key=key,
        Body=json.dumps(output, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    print(f"API-triggered workflow completed. Output: s3://{DATALAKE_BUCKET}/{key}")
    print(f"Message: {message}")
    print(f"Source: {source}")
    return output


with DAG(
    dag_id="api_triggered",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["demo", "api"],
    doc_md="""
    ## API-Triggered Workflow
    Simple DAG that runs when triggered via the MWAA REST API.
    Writes the trigger metadata to S3 as proof of execution.

    Trigger with: `aws mwaa invoke-rest-api --name any-company-mwaa-demo --path /api/v1/dags/api_triggered/dagRuns --method POST --body '{"conf":{"message":"hello","source":"lambda"}}'`
    """,
) as dag:

    process = PythonOperator(
        task_id="process_api_request",
        python_callable=process_api_request,
    )

    notify = SnsPublishOperator(
        task_id="send_notification",
        target_arn=SNS_TOPIC,
        message=(
            "API-triggered workflow completed.\n"
            "Message: {{ dag_run.conf.get('message', 'N/A') }}\n"
            "Source: {{ dag_run.conf.get('source', 'N/A') }}\n"
            "Run ID: {{ run_id }}"
        ),
        subject="[MWAA Demo] API-Triggered Workflow Complete",
    )

    process >> notify
