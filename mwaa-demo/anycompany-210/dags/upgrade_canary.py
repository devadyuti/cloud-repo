"""Upgrade canary — the single most useful DAG for this rehearsal.

Purpose
-------
Run this DAG on the environment BEFORE the 2.10.3 -> 2.11.2 upgrade and again
AFTER it. The task log prints the Airflow version, the Python interpreter
version, and the resolved version of every provider package we pin. The
before/after pair is the evidence that the upgrade did what it claimed:

    before:  Airflow 2.10.3 / Python 3.11.x / amazon 9.0.0  / http 4.13.2
    after:   Airflow 2.11.2 / Python 3.12.x / amazon 9.22.0 / http 6.0.0

It has NO external AWS dependencies, so it works on a bare environment and
cannot fail for reasons unrelated to the upgrade. If this DAG goes red, the
environment itself is unhealthy — not your pipeline code.

Compatibility: imports are Airflow 2 style and valid on 2.10.3 and 2.11.2.
"""

from __future__ import annotations

import sys
from datetime import datetime

from airflow import DAG

# AIRFLOW 3 MIGRATION: in Airflow 3 this moves to
#   from airflow.providers.standard.operators.python import PythonOperator
from airflow.operators.python import PythonOperator

DAG_ID = "anycompany_upgrade_canary"

# Packages whose versions we want on the record. Keep this list aligned with
# requirements-2.10.3.txt / requirements-2.11.2.txt.
TRACKED_DISTRIBUTIONS = [
    "apache-airflow",
    "apache-airflow-providers-amazon",
    "apache-airflow-providers-http",
    "apache-airflow-providers-common-sql",
    "boto3",
    "botocore",
    "pydantic",
]


def report_environment(**context) -> dict:
    """Log the runtime fingerprint of this environment and return it."""
    # importlib.metadata is stdlib on both 3.11 and 3.12.
    from importlib.metadata import PackageNotFoundError, version

    import airflow

    fingerprint: dict[str, str] = {
        "airflow_version": airflow.__version__,
        "python_version": sys.version.split()[0],
        "python_version_info": ".".join(str(p) for p in sys.version_info[:3]),
        "executable": sys.executable,
    }

    for dist in TRACKED_DISTRIBUTIONS:
        try:
            fingerprint[dist] = version(dist)
        except PackageNotFoundError:
            fingerprint[dist] = "NOT INSTALLED"

    width = max(len(k) for k in fingerprint)
    print("=" * (width + 40))
    print("ENVIRONMENT FINGERPRINT")
    print("=" * (width + 40))
    for key, value in fingerprint.items():
        print(f"{key.ljust(width)} : {value}")
    print("=" * (width + 40))

    # Loud, greppable assertion of the Python minor version. This is the
    # boundary that breaks MWAA upgrades: 2.10.x is Python 3.11,
    # 2.11.x and 3.x are Python 3.12.
    major_minor = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"PYTHON_MINOR={major_minor}")
    print(f"AIRFLOW_VERSION={airflow.__version__}")

    return fingerprint


def verify_provider_imports(**context) -> str:
    """Import the operators our real DAGs depend on.

    This is the cheapest possible early-warning for a broken requirements
    install after the upgrade. A requirements failure usually shows up as an
    ImportError here long before anyone notices a pipeline misbehaving.
    """
    checks: list[tuple[str, bool, str]] = []

    def check(label: str, fn) -> None:
        try:
            fn()
            checks.append((label, True, ""))
        except Exception as exc:  # noqa: BLE001 - we want the reason verbatim
            checks.append((label, False, f"{type(exc).__name__}: {exc}"))

    check(
        "amazon: S3Hook",
        lambda: __import__(
            "airflow.providers.amazon.aws.hooks.s3", fromlist=["S3Hook"]
        ).S3Hook,
    )
    check(
        "amazon: GlueJobOperator",
        lambda: __import__(
            "airflow.providers.amazon.aws.operators.glue", fromlist=["GlueJobOperator"]
        ).GlueJobOperator,
    )
    check(
        "amazon: SnsPublishOperator",
        lambda: __import__(
            "airflow.providers.amazon.aws.operators.sns", fromlist=["SnsPublishOperator"]
        ).SnsPublishOperator,
    )
    check(
        "amazon: S3KeySensor",
        lambda: __import__(
            "airflow.providers.amazon.aws.sensors.s3", fromlist=["S3KeySensor"]
        ).S3KeySensor,
    )
    check(
        "http: HttpOperator",
        lambda: __import__(
            "airflow.providers.http.operators.http", fromlist=["HttpOperator"]
        ).HttpOperator,
    )
    check(
        "http: HttpSensor",
        lambda: __import__(
            "airflow.providers.http.sensors.http", fromlist=["HttpSensor"]
        ).HttpSensor,
    )

    for label, ok, detail in checks:
        status = "OK  " if ok else "FAIL"
        print(f"[{status}] {label}{'' if ok else '  -> ' + detail}")

    failures = [c for c in checks if not c[1]]
    if failures:
        raise RuntimeError(
            f"{len(failures)} provider import(s) failed: "
            + ", ".join(label for label, _, _ in failures)
        )

    return f"all {len(checks)} provider imports OK"


default_args = {
    "owner": "anycompany-platform",
    "depends_on_past": False,
    "retries": 0,
}

with DAG(
    dag_id=DAG_ID,
    description="Reports Airflow/Python/provider versions. Run before and after upgrade.",
    default_args=default_args,
    # Manual trigger only - this is a diagnostic, not a schedule.
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["anycompany", "diagnostic", "upgrade"],
) as dag:
    fingerprint = PythonOperator(
        task_id="report_environment",
        python_callable=report_environment,
    )

    imports = PythonOperator(
        task_id="verify_provider_imports",
        python_callable=verify_provider_imports,
    )

    fingerprint >> imports
