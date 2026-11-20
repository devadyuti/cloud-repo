"""Lambda function to trigger MWAA Serverless workflows.

Supports two trigger modes:
- S3 event: Automatically triggers s3-event-lambda-serverless workflow when files arrive in serverless/incoming/
- Direct invocation: Triggers the same workflow on demand
"""

import json
import os
import time
from datetime import date, datetime, timezone

import boto3


def _put_metric(cw_client, metric_name, value=1.0, unit="Count"):
    """Publish a custom metric to the MWAADemo/Serverless namespace."""
    try:
        cw_client.put_metric_data(
            Namespace="MWAADemo/Serverless",
            MetricData=[
                {
                    "MetricName": metric_name,
                    "Value": value,
                    "Unit": unit,
                    "Timestamp": datetime.now(timezone.utc),
                }
            ],
        )
    except Exception:
        pass  # Best-effort — don't fail the workflow trigger on metric publish errors


def handler(event, context):
    """Trigger MWAA Serverless workflow based on event source.

    - S3 PutObject events in serverless/incoming/ -> triggers workflow automatically
    - Direct invocation -> triggers workflow on demand
    """
    workflow_arn = os.environ["WORKFLOW_ARN"]
    client = boto3.client("mwaa-serverless")
    cw_client = boto3.client("cloudwatch")

    # Build execution parameters from event
    records = event.get("Records", [])
    if records and records[0].get("eventSource") == "aws:s3":
        s3_key = records[0]["s3"]["object"]["key"]
        s3_bucket = records[0]["s3"]["bucket"]["name"]
        params = {
            "source": "s3_event",
            "s3_bucket": s3_bucket,
            "s3_key": s3_key,
            "date": date.today().isoformat(),
        }
    else:
        params = {
            "source": "lambda_direct",
            "date": date.today().isoformat(),
        }

    # Start the serverless workflow run
    start_time = time.time()
    try:
        response = client.start_workflow_run(
            WorkflowArn=workflow_arn,
            OverrideParameters=params,
        )
        elapsed_ms = (time.time() - start_time) * 1000

        # Publish custom metrics
        _put_metric(cw_client, "WorkflowRunsStarted")
        _put_metric(cw_client, "WorkflowRunsSucceeded")
        _put_metric(cw_client, "WorkflowDurationMs", value=elapsed_ms, unit="Milliseconds")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Workflow run started",
                "runId": response.get("RunId", "unknown"),
                "status": response.get("Status", "unknown"),
                "trigger": params,
            }, default=str),
        }
    except Exception as e:
        # Publish failure metric
        _put_metric(cw_client, "WorkflowRunsFailed")

        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "trigger": params,
            }),
        }
