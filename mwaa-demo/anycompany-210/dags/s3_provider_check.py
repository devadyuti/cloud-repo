"""Functional check of the Amazon provider against the environment's own bucket.

Purpose
-------
`upgrade_canary` proves the provider packages *import*. This DAG proves the
Amazon provider can actually make authenticated AWS calls with the environment's
execution role. Run it before and after the upgrade.

Deliberately READ-ONLY. The execution role that the MWAA console creates for you
grants Get/List on the environment's own S3 bucket but typically does NOT grant
PutObject. A write round-trip would fail with AccessDenied for permission
reasons that have nothing to do with the upgrade, which is exactly the kind of
false signal we want to avoid during a rehearsal.

Compatibility: imports are Airflow 2 style and valid on 2.10.3 and 2.11.2.
"""

from __future__ import annotations

from datetime import datetime

from airflow import DAG

# AIRFLOW 3 MIGRATION: moves to airflow.providers.standard.operators.python
from airflow.operators.python import PythonOperator

# AIRFLOW 3 MIGRATION: Variable access moves to the Task SDK in Airflow 3
from airflow.models import Variable
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

DAG_ID = "anycompany_s3_provider_check"

# Defaults to this environment's own DAGs bucket. Override with an Airflow
# Variable named `anycompany_dags_bucket` if the bucket name differs.
DEFAULT_BUCKET = "anycompany-mwaa-210-dags-123456789012"


def _bucket() -> str:
    return Variable.get("anycompany_dags_bucket", default_var=DEFAULT_BUCKET)


def list_dags_prefix(**context) -> int:
    """List objects under dags/ — proves ListBucket works."""
    hook = S3Hook()
    bucket = _bucket()

    keys = hook.list_keys(bucket_name=bucket, prefix="dags/") or []
    print(f"bucket={bucket}")
    print(f"objects under dags/: {len(keys)}")
    for key in sorted(keys):
        print(f"  {key}")

    if not keys:
        raise RuntimeError(
            f"No objects found under s3://{bucket}/dags/. "
            "Either the bucket name is wrong or the DAGs were never uploaded."
        )
    return len(keys)


def read_requirements(**context) -> str:
    """Read requirements.txt back out of S3 — proves GetObject works.

    Also prints the constraint line, which is a useful cross-check: the
    constraint URL in the bucket should match the Airflow version the
    environment is actually running.
    """
    hook = S3Hook()
    bucket = _bucket()
    key = "requirements.txt"

    if not hook.check_for_key(key=key, bucket_name=bucket):
        raise RuntimeError(f"s3://{bucket}/{key} not found")

    body = hook.read_key(key=key, bucket_name=bucket)

    print(f"--- s3://{bucket}/{key} ---")
    print(body)
    print("--- end ---")

    constraint_lines = [
        line.strip()
        for line in body.splitlines()
        if line.strip().startswith("--constraint")
    ]
    if constraint_lines:
        for line in constraint_lines:
            print(f"CONSTRAINT_IN_BUCKET={line}")
    else:
        print(
            "WARNING: no --constraint line found. Airflow 2.7.2+ on MWAA expects "
            "one; without it MWAA picks a constraint set for you."
        )

    return constraint_lines[0] if constraint_lines else "none"


def report_identity(**context) -> str:
    """Print the caller identity the environment is using."""
    hook = S3Hook()
    sts = hook.get_session().client("sts")
    identity = sts.get_caller_identity()
    print(f"account : {identity['Account']}")
    print(f"arn     : {identity['Arn']}")
    return identity["Arn"]


default_args = {
    "owner": "anycompany-platform",
    "depends_on_past": False,
    "retries": 1,
}

with DAG(
    dag_id=DAG_ID,
    description="Read-only AWS calls proving the Amazon provider works end to end.",
    default_args=default_args,
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["anycompany", "diagnostic", "upgrade"],
) as dag:
    identity = PythonOperator(
        task_id="report_identity",
        python_callable=report_identity,
    )

    listing = PythonOperator(
        task_id="list_dags_prefix",
        python_callable=list_dags_prefix,
    )

    requirements = PythonOperator(
        task_id="read_requirements",
        python_callable=read_requirements,
    )

    identity >> listing >> requirements
