"""Representative ETL pipeline — realistic shape, safe to run on a bare environment.

Ported from the reference pipeline: S3KeySensor -> Glue transform -> warehouse
load -> SNS notify.

Why this DAG exists
-------------------
The diagnostic DAGs (`upgrade_canary`, `s3_provider_check`) prove the
environment is healthy. This one gives the rehearsal a realistic DAG shape, so
the scheduler is parsing something comparable to the customer's actual fleet
across the 2.10.3 -> 2.11.2 upgrade.

SIMULATE flag
-------------
`SIMULATE = True` (the default) replaces the AWS-touching operators with
PythonOperator stand-ins that log exactly what the real operator would do. This
lets the DAG run green on a brand-new environment where no Glue job, SNS topic,
or raw-data bucket exists yet — so a red task means a real problem, not missing
demo infrastructure.

Note that the real operators are still imported at module scope, so a broken
provider install after the upgrade still surfaces as an import error here.

Flip to `SIMULATE = False` once the backing resources exist.

Compatibility: imports are Airflow 2 style and valid on 2.10.3 and 2.11.2.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG

# AIRFLOW 3 MIGRATION: moves to airflow.providers.standard.operators.python
from airflow.operators.python import PythonOperator

# Imported unconditionally so a post-upgrade provider breakage shows up as an
# ImportError at parse time, even while SIMULATE is True.
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.providers.amazon.aws.operators.sns import SnsPublishOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor

DAG_ID = "anycompany_etl_pipeline"

# Set to False once the Glue job, SNS topic, and raw bucket below exist.
SIMULATE = True

RAW_BUCKET = "anycompany-raw-data"
GLUE_JOB_NAME = "anycompany-transform-demo"
SNS_TOPIC_DEFAULT = "arn:aws:sns:eu-west-1:123456789012:anycompany-demo-notifications"

default_args = {
    "owner": "anycompany-data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}


# --- Simulated stand-ins -----------------------------------------------------


def simulate_wait_for_data(**kwargs) -> str:
    key = f"incoming/{kwargs['ds']}/data.parquet"
    print(f"[SIMULATED S3KeySensor] would poll s3://{RAW_BUCKET}/{key}")
    print("  poke_interval=60s timeout=3600s mode=reschedule")
    return key


def simulate_glue_transform(**kwargs) -> dict:
    ds = kwargs["ds"]
    print(f"[SIMULATED GlueJobOperator] would run job '{GLUE_JOB_NAME}'")
    print(f"  --source_path s3://{RAW_BUCKET}/incoming/{ds}/")
    print(f"  --target_path s3://{RAW_BUCKET}/transformed/{ds}/")
    return {"job_name": GLUE_JOB_NAME, "status": "simulated"}


def simulate_notify(**kwargs) -> str:
    rows = (kwargs["ti"].xcom_pull(task_ids="load_to_warehouse") or {}).get(
        "rows_loaded", "unknown"
    )
    print(f"[SIMULATED SnsPublishOperator] would publish to {SNS_TOPIC_DEFAULT}")
    print(f"  ETL complete for {kwargs['ds']}, rows_loaded={rows}")
    return "simulated"


# --- Real work ---------------------------------------------------------------


def load_to_warehouse(**kwargs) -> dict:
    """Stand-in for a Redshift Data API load.

    Kept as plain Python in both modes so the DAG always has one task doing
    real, dependency-free work.
    """
    ds = kwargs["ds"]
    print(f"Loading transformed data for {ds}")
    print(f"  source: s3://{RAW_BUCKET}/transformed/{ds}/")
    print("  target: anycompany_analytics.daily_transactions")
    print("  rows loaded: simulated (demo mode)")
    return {"status": "success", "rows_loaded": 1500}


def on_failure_callback(context) -> None:
    ti = context["task_instance"]
    print(f"Task {ti.task_id} failed in DAG {ti.dag_id}")


with DAG(
    dag_id=DAG_ID,
    description="Representative daily ETL pipeline for the upgrade rehearsal.",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["anycompany", "etl", "demo"],
    on_failure_callback=on_failure_callback,
    doc_md=__doc__,
) as dag:
    if SIMULATE:
        wait_for_data = PythonOperator(
            task_id="wait_for_data",
            python_callable=simulate_wait_for_data,
        )
        transform = PythonOperator(
            task_id="glue_transform",
            python_callable=simulate_glue_transform,
        )
    else:
        wait_for_data = S3KeySensor(
            task_id="wait_for_data",
            bucket_name=RAW_BUCKET,
            bucket_key="incoming/{{ ds }}/data.parquet",
            poke_interval=60,
            timeout=3600,
            mode="reschedule",
        )
        transform = GlueJobOperator(
            task_id="glue_transform",
            job_name=GLUE_JOB_NAME,
            wait_for_completion=True,
            script_args={
                "--source_path": f"s3://{RAW_BUCKET}/incoming/{{{{ ds }}}}/",
                "--target_path": f"s3://{RAW_BUCKET}/transformed/{{{{ ds }}}}/",
                "--execution_date": "{{ ds }}",
            },
        )

    load = PythonOperator(
        task_id="load_to_warehouse",
        python_callable=load_to_warehouse,
    )

    if SIMULATE:
        notify_success = PythonOperator(
            task_id="notify_success",
            python_callable=simulate_notify,
        )
    else:
        notify_success = SnsPublishOperator(
            task_id="notify_success",
            target_arn=(
                "{{ var.value.get('anycompany_sns_topic_arn', '"
                + SNS_TOPIC_DEFAULT
                + "') }}"
            ),
            message=(
                "ETL pipeline completed successfully for {{ ds }}.\n"
                "Rows loaded: "
                "{{ ti.xcom_pull(task_ids='load_to_warehouse')['rows_loaded'] }}"
            ),
            subject="[AnyCompany MWAA] ETL Pipeline Complete - {{ ds }}",
        )

    wait_for_data >> transform >> load >> notify_success
