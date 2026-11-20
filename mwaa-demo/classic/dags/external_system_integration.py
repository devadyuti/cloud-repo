"""
External System Integration DAG — MWAA calling a car search API.

Pipeline: Call Car Search API → Transform Results → Load to S3 → SNS
Schedule: None (manual trigger)
Tags: ["demo", "integration", "api"]

Demonstrates:
- HttpOperator calling a real external REST API (POST with JSON body)
- PythonOperator for data transformation
- S3 write for landing external data in the data lake
- End-to-end external system integration from MWAA

External API: https://api.example.com/car-search/api/search
"""

import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.sns import SnsPublishOperator
from airflow.providers.http.operators.http import HttpOperator

DATALAKE_BUCKET = "any-company-mwaa-demo-dags-123456789012"
SNS_TOPIC = "arn:aws:sns:eu-west-1:123456789012:mwaa-etl-notifications"

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
    "execution_timeout": timedelta(minutes=10),
}


def transform_car_data(**kwargs):
    """Transform car search API results into data lake records."""
    ti = kwargs["ti"]
    raw_response = ti.xcom_pull(task_ids="call_car_search_api")

    if raw_response is None:
        raise ValueError("No response received from car search API")

    if isinstance(raw_response, str):
        data = json.loads(raw_response)
    else:
        data = raw_response

    # Extract results from response
    results = data.get("results", data.get("items", []))
    if isinstance(data, list):
        results = data

    records = []
    for car in results:
        records.append({
            "title": car.get("title", car.get("name")),
            "price": car.get("price"),
            "make": car.get("make"),
            "model": car.get("model"),
            "year": car.get("year"),
            "fuel_type": car.get("fuelType", car.get("fuel_type")),
            "source": "car-search-api",
            "ingested_at": kwargs["ts"],
        })

    print(f"Transformed {len(records)} car listings from API")
    return records


def load_to_s3(**kwargs):
    """Write transformed records to S3 as JSON."""
    import boto3

    ti = kwargs["ti"]
    records = ti.xcom_pull(task_ids="transform_results")
    ds = kwargs["ds"]
    ts_nodash = kwargs["ts_nodash"]

    if not records:
        print("No records to load")
        return {"status": "skipped", "records_written": 0}

    s3_client = boto3.client("s3")
    key = f"external-api/car-search/{ds}/{ts_nodash}.json"

    body = json.dumps(records, indent=2)
    s3_client.put_object(
        Bucket=DATALAKE_BUCKET,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/json",
    )

    s3_path = f"s3://{DATALAKE_BUCKET}/{key}"
    print(f"Wrote {len(records)} records to {s3_path}")
    return {"status": "success", "records_written": len(records), "s3_path": s3_path}


with DAG(
    dag_id="external_system_integration",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["demo", "integration", "api"],
    doc_md="""
    ## External System Integration

    Calls a car search REST API, transforms the results, and lands them
    in the S3 data lake. Demonstrates MWAA orchestrating external API calls.

    ### Pipeline
    1. **Call API** — POST to car-search service with search query
    2. **Transform** — normalise results into data lake schema
    3. **Load** — write JSON to S3 (`external-api/car-search/{date}/`)
    4. **Notify** — SNS email on completion
    """,
) as dag:

    # Step 1: Call the car search API
    call_car_search_api = HttpOperator(
        task_id="call_car_search_api",
        http_conn_id="car_search_api",
        endpoint="/car-search/api/search",
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        data=json.dumps({
            "query": "electric SUV under 30k",
            "maxResults": 20,
            "page": 1,
        }),
        response_filter=lambda response: response.json(),
        log_response=True,
    )

    # Step 2: Transform
    transform_results = PythonOperator(
        task_id="transform_results",
        python_callable=transform_car_data,
    )

    # Step 3: Load to S3
    load_to_datalake = PythonOperator(
        task_id="load_to_s3",
        python_callable=load_to_s3,
    )

    # Step 4: Notify
    notify_success = SnsPublishOperator(
        task_id="notify_success",
        target_arn=SNS_TOPIC,
        message=(
            "External API integration completed for {{ ds }}.\n"
            "Source: Car Search API\n"
            "Query: electric SUV under 30k\n"
            "Records: {{ ti.xcom_pull(task_ids='load_to_s3')['records_written'] }}\n"
            "Output: {{ ti.xcom_pull(task_ids='load_to_s3')['s3_path'] }}"
        ),
        subject="[MWAA Demo] External Integration Complete - {{ ds }}",
    )

    call_car_search_api >> transform_results >> load_to_datalake >> notify_success
