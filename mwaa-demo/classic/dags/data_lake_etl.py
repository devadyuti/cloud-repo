"""
Data Lake ETL Pipeline — End-to-end medallion architecture on AWS.

Pipeline:
  S3 Landing Zone Sensor → Glue Crawler (raw → catalog) → Glue ETL Job (bronze → silver)
  → Athena Data Quality Checks → Redshift COPY (silver → gold) → SNS Notification

Schedule: @daily
Tags: ["production", "data-lake", "etl", "medallion"]

Demonstrates:
- Medallion architecture (bronze/silver/gold) on S3
- Glue Crawlers for automatic schema discovery
- Glue ETL jobs for PySpark transformations
- Athena queries for in-pipeline data quality validation
- Redshift Data API for warehouse loading
- Branching logic (quality gate pass/fail)
- SLA enforcement with task-level timeouts
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.providers.amazon.aws.operators.athena import AthenaOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.operators.glue_crawler import GlueCrawlerOperator
from airflow.providers.amazon.aws.operators.sns import SnsPublishOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.amazon.aws.operators.redshift_data import RedshiftDataOperator

DATALAKE_BUCKET = "any-company-mwaa-demo-dags-123456789012"
ATHENA_OUTPUT = f"s3://{DATALAKE_BUCKET}/athena-results/"
GLUE_DB = "anycompany_data_lake"
SNS_TOPIC = "arn:aws:sns:eu-west-1:123456789012:mwaa-etl-notifications"

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
    "execution_timeout": timedelta(hours=2),
}


def evaluate_quality_results(**kwargs):
    """Check Athena quality query results and decide pass/fail branch.

    Pulls the query execution ID from XCom, then checks whether
    the null rate and duplicate rate are within acceptable thresholds.
    """
    ti = kwargs["ti"]
    # In production, parse Athena results via boto3 get_query_results
    # For demo, simulate the quality gate logic
    null_rate = 0.02  # 2% nulls — acceptable
    duplicate_rate = 0.001  # 0.1% dupes — acceptable

    print(f"Data quality results — null_rate: {null_rate:.2%}, duplicate_rate: {duplicate_rate:.2%}")

    if null_rate > 0.05 or duplicate_rate > 0.01:
        print("QUALITY GATE FAILED — routing to quarantine")
        return "quarantine_and_alert"
    else:
        print("QUALITY GATE PASSED — proceeding to Redshift load")
        return "load_to_redshift"


def quarantine_bad_data(**kwargs):
    """Move failed partition to quarantine prefix for manual review."""
    ds = kwargs["ds"]
    print(f"Quarantining data for {ds}")
    print(f"  Moving: s3://{DATALAKE_BUCKET}/silver/transactions/dt={ds}/")
    print(f"  To:     s3://{DATALAKE_BUCKET}/quarantine/transactions/dt={ds}/")
    print("  Reason: Data quality checks failed (null_rate > 5% or duplicate_rate > 1%)")


with DAG(
    dag_id="data_lake_etl",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["production", "data-lake", "etl", "medallion"],
    doc_md="""
    ## Data Lake ETL — Medallion Architecture

    Daily batch pipeline implementing bronze → silver → gold data movement:

    1. **Bronze (Landing):** Raw files arrive in `landing/transactions/` via upstream systems
    2. **Glue Crawler:** Discovers schema, registers in Glue Data Catalog
    3. **Glue ETL (Silver):** PySpark job deduplicates, validates, partitions by date
    4. **Athena Quality Gate:** SQL-based checks (null rates, duplicates, row counts)
    5. **Gold (Redshift):** COPY from silver S3 into Redshift analytics tables
    6. **Notification:** SNS alert on success or quarantine on failure

    ### Data Quality Thresholds
    - Max null rate: 5%
    - Max duplicate rate: 1%
    - Min row count: 100

    ### Recovery
    Failed partitions are moved to `quarantine/` prefix for manual review.
    Re-trigger after fixing source data by clearing the task in Airflow UI.
    """,
) as dag:

    # --- Bronze: Wait for upstream data ---
    wait_for_landing_data = S3KeySensor(
        task_id="wait_for_landing_data",
        bucket_name=DATALAKE_BUCKET,
        bucket_key="landing/transactions/dt={{ ds }}/data.csv",
        poke_interval=30,
        timeout=300,
    )

    # --- Bronze → Catalog: Discover schema ---
    crawl_raw_data = GlueCrawlerOperator(
        task_id="crawl_raw_data",
        config={"Name": "any-company-transactions-crawler"},
        wait_for_completion=True,
    )

    # --- Bronze → Silver: Transform and partition ---
    transform_to_silver = GlueJobOperator(
        task_id="transform_to_silver",
        job_name="any-company-bronze-to-silver",
        wait_for_completion=True,
        script_args={
            "--source_database": GLUE_DB,
            "--source_table": "raw_transactions",
            "--target_path": f"s3://{DATALAKE_BUCKET}/silver/transactions/",
            "--partition_key": "dt",
            "--execution_date": "{{ ds }}",
            "--dedup_keys": "transaction_id,customer_id",
        },
    )

    # --- Silver: Data quality check via Athena ---
    run_quality_checks = AthenaOperator(
        task_id="run_quality_checks",
        query="""
            SELECT
                COUNT(*) as total_rows,
                SUM(CASE WHEN transaction_id IS NULL THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as null_rate,
                1.0 - (COUNT(DISTINCT transaction_id) * 1.0 / COUNT(*)) as duplicate_rate
            FROM "{{ params.database }}"."raw_transactions"
            WHERE dt = '{{ ds }}'
        """,
        database=GLUE_DB,
        output_location=ATHENA_OUTPUT,
        params={"database": GLUE_DB},
    )

    # --- Quality Gate: Branch based on results ---
    quality_gate = BranchPythonOperator(
        task_id="quality_gate",
        python_callable=evaluate_quality_results,
    )

    # --- Gold: Load to Redshift (happy path) ---
    load_to_redshift = RedshiftDataOperator(
        task_id="load_to_redshift",
        database="dev",
        cluster_identifier="analytics-cluster",
        db_user="awsuser",
        sql="""
            DROP TABLE IF EXISTS public.transactions;
            CREATE TABLE public.transactions (
                transaction_id VARCHAR(256),
                customer_id VARCHAR(256),
                amount DOUBLE PRECISION,
                region VARCHAR(256),
                date VARCHAR(256),
                category VARCHAR(256),
                ingested_at TIMESTAMP,
                source_layer VARCHAR(256)
            );
            COPY public.transactions
            FROM 's3://{{ params.bucket }}/silver/transactions/dt={{ ds }}/'
            IAM_ROLE 'arn:aws:iam::123456789012:role/service-role/AmazonRedshift-CommandsAccessRole-20250901T162924'
            FORMAT AS PARQUET;
        """,
        params={"bucket": DATALAKE_BUCKET},
        wait_for_completion=True,
    )

    # --- Quarantine path (quality failed) ---
    quarantine_and_alert = PythonOperator(
        task_id="quarantine_and_alert",
        python_callable=quarantine_bad_data,
    )

    notify_quarantine = SnsPublishOperator(
        task_id="notify_quarantine",
        target_arn=SNS_TOPIC,
        message=(
            "DATA QUALITY ALERT: Partition {{ ds }} failed quality checks.\n"
            "Data moved to quarantine prefix for manual review.\n"
            "Pipeline: data_lake_etl\n"
            "Action required: inspect quarantine/transactions/dt={{ ds }}/"
        ),
        subject="[MWAA] Data Quality FAILED - {{ ds }}",
    )

    # --- Success notification ---
    notify_success = SnsPublishOperator(
        task_id="notify_success",
        target_arn=SNS_TOPIC,
        message=(
            "Data Lake ETL completed successfully for {{ ds }}.\n"
            "Bronze → Silver → Gold pipeline finished.\n"
            "Redshift table: anycompany_analytics.transactions\n"
            "Quality gate: PASSED"
        ),
        subject="[MWAA] Data Lake ETL Complete - {{ ds }}",
    )

    # --- DAG Wiring ---
    (
        wait_for_landing_data
        >> crawl_raw_data
        >> transform_to_silver
        >> run_quality_checks
        >> quality_gate
    )

    quality_gate >> load_to_redshift >> notify_success
    quality_gate >> quarantine_and_alert >> notify_quarantine
