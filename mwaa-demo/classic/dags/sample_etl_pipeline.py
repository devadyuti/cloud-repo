"""
Sample ETL Pipeline DAG — Multi-step data pipeline on classic MWAA.

Pipeline: S3KeySensor → GlueJobOperator → PythonOperator (Redshift load) → SnsPublishOperator
Schedule: @daily
Tags: ["demo", "any-company", "etl"]

Demonstrates:
- Sensor-based waiting for upstream data arrival
- AWS Glue integration for serverless Spark transforms
- Redshift Data API for warehouse loading
- SNS notifications on pipeline completion/failure
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.operators.sns import SnsPublishOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}


def load_to_redshift(**kwargs):
    """Load transformed data into Redshift via Data API.

    In production this would call redshift-data:ExecuteStatement.
    For demo purposes, logs a simulated load.
    """
    ds = kwargs["ds"]
    print(f"Loading transformed data for {ds} into Redshift cluster")
    print("  Source: s3://any-company-raw-data/transformed/{ds}/")
    print("  Target: anycompany_analytics.daily_transactions")
    print("  Rows loaded: simulated (demo mode)")
    return {"status": "success", "rows_loaded": 1500}


def on_failure_callback(context):
    """Log failure details for observability."""
    task_instance = context["task_instance"]
    print(f"Task {task_instance.task_id} failed in DAG {task_instance.dag_id}")


with DAG(
    dag_id="sample_etl_pipeline",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["demo", "any-company", "etl"],
    doc_md="""
    ## ETL Pipeline
    Daily batch pipeline that ingests raw transaction data from S3,
    transforms via Glue, loads into Redshift, and sends completion notification.
    """,
    on_failure_callback=on_failure_callback,
) as dag:

    wait_for_data = S3KeySensor(
        task_id="wait_for_data",
        bucket_name="any-company-raw-data",
        bucket_key="incoming/{{ ds }}/data.parquet",
        poke_interval=60,
        timeout=3600,
        mode="reschedule",  # Frees up worker slot while waiting
    )

    transform = GlueJobOperator(
        task_id="glue_transform",
        job_name="any-company-transform-demo",
        wait_for_completion=True,
        script_args={
            "--source_path": "s3://any-company-raw-data/incoming/{{ ds }}/",
            "--target_path": "s3://any-company-raw-data/transformed/{{ ds }}/",
            "--execution_date": "{{ ds }}",
        },
    )

    load = PythonOperator(
        task_id="load_to_redshift",
        python_callable=load_to_redshift,
    )

    notify_success = SnsPublishOperator(
        task_id="notify_success",
        target_arn="{{ var.value.get('sns_topic_arn', 'arn:aws:sns:eu-west-1:123456789012:any-company-demo-notifications') }}",
        message="ETL pipeline completed successfully for {{ ds }}.\nRows loaded: {{ ti.xcom_pull(task_ids='load_to_redshift')['rows_loaded'] }}",
        subject="[MWAA Demo] ETL Pipeline Complete - {{ ds }}",
    )

    wait_for_data >> transform >> load >> notify_success
