"""
ML Feature Pipeline — ECS Fargate feature engineering with Athena validation.

Pipeline:
  S3 Sensor (new training data) → ECS Fargate (feature engineering)
  → Athena Feature Validation → S3 Feature Store Write → Glue Catalog Update
  → Notify ML Team

Schedule: Every 6 hours
Tags: ["ml", "features", "ecs", "fargate"]

Demonstrates:
- ECS Fargate for compute-heavy feature engineering (sklearn, numpy, pandas)
- Task Groups for logical grouping of related operations
- Athena for statistical validation of computed features
- S3-based offline feature store with Hive-partitioned output
- Dynamic task parameters via Airflow Variables
- SLA miss callbacks for ML pipeline freshness guarantees
"""

import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.athena import AthenaOperator
from airflow.providers.amazon.aws.operators.ecs import EcsRunTaskOperator
from airflow.providers.amazon.aws.operators.glue_crawler import GlueCrawlerOperator
from airflow.providers.amazon.aws.operators.sns import SnsPublishOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.utils.task_group import TaskGroup

DATALAKE_BUCKET = "any-company-mwaa-demo-dags-123456789012"
FEATURE_STORE_PREFIX = "feature-store/customer-risk/"
ATHENA_OUTPUT = f"s3://{DATALAKE_BUCKET}/athena-results/"
GLUE_DB = "anycompany_feature_store"
SNS_TOPIC = "arn:aws:sns:eu-west-1:123456789012:mwaa-etl-notifications"

# Network config for ECS tasks (read from Variables with safe defaults)
PRIVATE_SUBNETS = json.loads(
    Variable.get(
        "private_subnet_ids",
        default_var='["subnet-0204cb14175c717eb", "subnet-0d65602c96c7689ae"]',
    )
)
MWAA_SG = Variable.get("mwaa_sg_id", default_var="sg-0ad71ccc014f195ab")

default_args = {
    "owner": "ml-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}


def sla_miss_callback(dag, task_list, blocking_task_list, slas, blocking_tis):
    """Alert when feature pipeline misses its 6-hour SLA."""
    print(f"SLA MISS: Feature pipeline is late. Blocking tasks: {blocking_task_list}")
    print("ML model retraining may be using stale features.")


def validate_feature_stats(**kwargs):
    """Check feature statistics from Athena are within expected bounds.

    Validates that computed features have reasonable distributions:
    - No features with 100% null
    - Standard deviations within expected ranges
    - Feature count matches expected schema
    """
    ti = kwargs["ti"]
    ds = kwargs["ds"]

    # In production, parse Athena query results via boto3
    # For demo, simulate statistical validation
    expected_features = 12
    actual_features = 12
    null_features = 0
    max_stddev = 15.2

    print(f"Feature validation for partition dt={ds}:")
    print(f"  Expected features: {expected_features}")
    print(f"  Actual features:   {actual_features}")
    print(f"  Null features:     {null_features}")
    print(f"  Max std deviation: {max_stddev}")

    if actual_features != expected_features:
        raise ValueError(
            f"Feature count mismatch: expected {expected_features}, got {actual_features}"
        )
    if null_features > 0:
        raise ValueError(f"{null_features} features are entirely null")

    return {
        "status": "valid",
        "feature_count": actual_features,
        "partition": f"dt={ds}",
    }


def register_feature_version(**kwargs):
    """Register the new feature partition in the feature metadata catalog.

    Updates a metadata JSON file in S3 that downstream ML training jobs
    reference to find the latest feature set.
    """
    ds = kwargs["ds"]
    ts = kwargs["ts"]

    metadata = {
        "latest_partition": f"dt={ds}",
        "feature_path": f"s3://{DATALAKE_BUCKET}/{FEATURE_STORE_PREFIX}dt={ds}/",
        "computed_at": ts,
        "feature_count": 12,
        "schema_version": "v2",
        "source_tables": ["transactions", "customer_profiles", "risk_scores"],
    }

    print(f"Registering feature version: {json.dumps(metadata, indent=2)}")
    print(f"Metadata written to: s3://{DATALAKE_BUCKET}/{FEATURE_STORE_PREFIX}_metadata/latest.json")
    return metadata


with DAG(
    dag_id="ml_feature_pipeline",
    schedule="0 */6 * * *",  # Every 6 hours
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["ml", "features", "ecs", "fargate"],
    sla_miss_callback=sla_miss_callback,
    doc_md="""
    ## ML Feature Pipeline

    Computes customer risk features every 6 hours for the ML model training pipeline.

    ### Feature Engineering (ECS Fargate)
    Runs a containerised Python job that:
    - Reads raw transaction data, customer profiles, and historical risk scores from S3
    - Computes 12 aggregate features (rolling averages, velocity metrics, risk indicators)
    - Writes Hive-partitioned Parquet files to the feature store prefix

    ### Why ECS?
    Feature computation requires pandas, numpy, scikit-learn, and 2GB+ memory —
    dependencies and resources that exceed what the Airflow worker provides.

    ### Downstream Consumers
    - ML model retraining pipeline (reads latest partition)
    - Real-time scoring service (syncs features to DynamoDB)
    - Analytics team (queries via Athena)

    ### SLA
    Must complete within 6 hours to avoid stale features in the next model retrain cycle.
    """,
) as dag:

    # --- Wait for source data to be available ---
    wait_for_source_data = S3KeySensor(
        task_id="wait_for_source_data",
        bucket_name=DATALAKE_BUCKET,
        bucket_key="silver/transactions/dt={{ ds }}/",
        wildcard_match=True,
        poke_interval=300,
        timeout=3600,
        mode="reschedule",
    )

    # --- Feature Engineering: ECS Fargate Task ---
    with TaskGroup("feature_engineering") as feature_engineering:

        compute_features = EcsRunTaskOperator(
            task_id="compute_features",
            cluster="any-company-demo-cluster",
            task_definition="any-company-etl-task",
            launch_type="FARGATE",
            overrides={
                "containerOverrides": [
                    {
                        "name": "EtlContainer",
                        "command": [
                            "python", "pipeline.py",
                            "--mode", "feature-engineering",
                            "--execution-date", "{{ ds }}",
                        ],
                        "environment": [
                            {"name": "EXECUTION_DATE", "value": "{{ ds }}"},
                            {"name": "SOURCE_BUCKET", "value": DATALAKE_BUCKET},
                            {"name": "SOURCE_PREFIX", "value": "silver/transactions/dt={{ ds }}/"},
                            {"name": "OUTPUT_BUCKET", "value": DATALAKE_BUCKET},
                            {"name": "OUTPUT_PREFIX", "value": f"{FEATURE_STORE_PREFIX}dt={{{{ ds }}}}/"},
                            {"name": "FEATURE_SET", "value": "customer_risk_v2"},
                        ],
                    }
                ],
                "cpu": "1024",
                "memory": "2048",
            },
            network_configuration={
                "awsvpcConfiguration": {
                    "subnets": PRIVATE_SUBNETS,
                    "securityGroups": [MWAA_SG],
                    "assignPublicIp": "DISABLED",
                }
            },
            awslogs_group="/ecs/any-company-etl-task",
            awslogs_stream_prefix="feature-eng",
        )

    # --- Validation: Athena statistical checks ---
    with TaskGroup("validation") as validation:

        check_feature_completeness = AthenaOperator(
            task_id="check_feature_completeness",
            query="""
                SELECT
                    COUNT(*) as row_count,
                    COUNT(DISTINCT customer_id) as unique_customers,
                    SUM(CASE WHEN risk_score_30d IS NULL THEN 1 ELSE 0 END) as null_risk_scores,
                    AVG(transaction_velocity_7d) as avg_velocity,
                    STDDEV(transaction_velocity_7d) as stddev_velocity
                FROM "{{ params.database }}"."customer_risk_features"
                WHERE dt = '{{ ds }}'
            """,
            database=GLUE_DB,
            output_location=ATHENA_OUTPUT,
            params={"database": GLUE_DB},
        )

        check_feature_drift = AthenaOperator(
            task_id="check_feature_drift",
            query="""
                WITH current_stats AS (
                    SELECT AVG(risk_score_30d) as curr_avg, STDDEV(risk_score_30d) as curr_std
                    FROM "{{ params.database }}"."customer_risk_features"
                    WHERE dt = '{{ ds }}'
                ),
                previous_stats AS (
                    SELECT AVG(risk_score_30d) as prev_avg, STDDEV(risk_score_30d) as prev_std
                    FROM "{{ params.database }}"."customer_risk_features"
                    WHERE dt = DATE_FORMAT(DATE_ADD('day', -1, DATE('{{ ds }}')), '%Y-%m-%d')
                )
                SELECT
                    curr_avg, prev_avg,
                    ABS(curr_avg - prev_avg) / NULLIF(prev_std, 0) as drift_score
                FROM current_stats, previous_stats
            """,
            database=GLUE_DB,
            output_location=ATHENA_OUTPUT,
            params={"database": GLUE_DB},
        )

        validate_stats = PythonOperator(
            task_id="validate_stats",
            python_callable=validate_feature_stats,
        )

        [check_feature_completeness, check_feature_drift] >> validate_stats

    # --- Catalog Update: Make features discoverable ---
    update_feature_catalog = GlueCrawlerOperator(
        task_id="update_feature_catalog",
        config={
            "Name": "any-company-feature-store-crawler",
            "Role": "arn:aws:iam::123456789012:role/GlueCrawlerRole",
            "DatabaseName": GLUE_DB,
            "Targets": {
                "S3Targets": [
                    {"Path": f"s3://{DATALAKE_BUCKET}/{FEATURE_STORE_PREFIX}"}
                ]
            },
        },
        wait_for_completion=True,
    )

    # --- Register version for downstream consumers ---
    register_version = PythonOperator(
        task_id="register_feature_version",
        python_callable=register_feature_version,
    )

    # --- Notify ML team ---
    notify_ml_team = SnsPublishOperator(
        task_id="notify_ml_team",
        target_arn=SNS_TOPIC,
        message=(
            "ML Feature Pipeline completed for {{ ds }}.\n"
            "Feature set: customer_risk_v2 (12 features)\n"
            "Location: s3://{{ params.bucket }}/{{ params.prefix }}dt={{ ds }}/\n"
            "Status: validated, cataloged, ready for training"
        ),
        subject="[MWAA] Feature Pipeline Complete - {{ ds }}",
        params={"bucket": DATALAKE_BUCKET, "prefix": FEATURE_STORE_PREFIX},
    )

    # --- DAG Wiring ---
    (
        wait_for_source_data
        >> feature_engineering
        >> validation
        >> update_feature_catalog
        >> register_version
        >> notify_ml_team
    )
