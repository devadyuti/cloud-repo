"""
dbt AnyCompany Analytics DAG — orchestrate a dbt Core project from classic MWAA with Astronomer Cosmos.

Pipeline: dbt seeds → staging models → mart models (each followed by its dbt tests) → SNS
Schedule: @daily
Tags: ["demo", "dbt", "cosmos", "redshift"]

Demonstrates:
- Cosmos renders every dbt seed/model as its own Airflow task, with that node's dbt tests
  run straight after it (TestBehavior.AFTER_EACH). A failing test stops only its downstream
  models, and a single model can be retried or cleared from the Airflow UI.
- Fast, connection-free DAG parsing from a pre-compiled manifest (LoadMode.DBT_MANIFEST,
  built by scripts/build_dbt_manifest.sh).
- dbt Core runs from an isolated virtualenv created by startup.sh, so dbt's dependency
  pins never conflict with Airflow's constraints.
- Redshift credentials come from the existing Airflow connection `redshift_analytics_cluster`
  (Secrets Manager: airflow/connections/redshift_analytics_cluster). No profiles.yml or
  passwords live in the repo.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.providers.amazon.aws.operators.sns import SnsPublishOperator
from cosmos import (
    DbtTaskGroup,
    ExecutionConfig,
    LoadMode,
    ProfileConfig,
    ProjectConfig,
    RenderConfig,
    TestBehavior,
)
from cosmos.constants import TestIndirectSelection
from cosmos.profiles import RedshiftUserPasswordProfileMapping

SNS_TOPIC = "arn:aws:sns:eu-west-1:123456789012:mwaa-etl-notifications"
REDSHIFT_CONN_ID = "redshift_analytics_cluster"
DBT_TARGET_SCHEMA = "dbt_anycompany"

DBT_PROJECT_DIR = Path(__file__).resolve().parent / "dbt" / "anycompany_analytics"
DBT_MANIFEST_PATH = DBT_PROJECT_DIR / "target" / "manifest.json"

# startup.sh exports DBT_EXECUTABLE_PATH; fall back to the same default location.
DBT_EXECUTABLE_PATH = os.environ.get(
    "DBT_EXECUTABLE_PATH",
    f"{os.environ.get('AIRFLOW_HOME', '/usr/local/airflow')}/dbt_venv/bin/dbt",
)

profile_config = ProfileConfig(
    profile_name="anycompany_analytics",
    target_name="dev",
    profile_mapping=RedshiftUserPasswordProfileMapping(
        conn_id=REDSHIFT_CONN_ID,
        # Base schema; dbt_project.yml suffixes it per layer (_raw, _staging, _marts).
        profile_args={"schema": DBT_TARGET_SCHEMA, "threads": 4},
    ),
)

default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=30),
}


with DAG(
    dag_id="dbt_anycompany_analytics",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["demo", "dbt", "cosmos", "redshift"],
    doc_md="""
    ## dbt AnyCompany Analytics (Cosmos)
    Runs the `anycompany_analytics` dbt Core project against the provisioned Redshift cluster
    `analytics-cluster` (database `dev`, schemas `dbt_anycompany_raw` / `_staging` / `_marts`).

    Each dbt node is an Airflow task, and its tests run immediately after it.
    Retry a single model by clearing its task. Downstream models re-run on their own.
    """,
) as dag:

    anycompany_analytics = DbtTaskGroup(
        group_id="anycompany_analytics",
        project_config=ProjectConfig(
            dbt_project_path=DBT_PROJECT_DIR,
            manifest_path=DBT_MANIFEST_PATH,
            install_dbt_deps=False,  # no dbt packages — skip `dbt deps` on every task
        ),
        profile_config=profile_config,
        execution_config=ExecutionConfig(
            dbt_executable_path=DBT_EXECUTABLE_PATH,
            # A model's test task runs only tests whose parents are ALL selected. Without this,
            # `dbt test --select stg_customers` also picks up the stg_transactions ->
            # stg_customers relationships test and races the parallel stg_transactions branch.
            test_indirect_selection=TestIndirectSelection.CAUTIOUS,
        ),
        render_config=RenderConfig(
            load_method=LoadMode.DBT_MANIFEST,
            test_behavior=TestBehavior.AFTER_EACH,
            # Multi-parent tests (e.g. relationships) get their own task, downstream of every parent.
            should_detach_multiple_parents_tests=True,
            emit_datasets=False,
        ),
    )

    notify_success = SnsPublishOperator(
        task_id="notify_success",
        target_arn=SNS_TOPIC,
        subject="[MWAA Demo] dbt anycompany_analytics complete - {{ ds }}",
        message=(
            "dbt project anycompany_analytics built and tested successfully for {{ ds }}.\n"
            "Redshift cluster: analytics-cluster / dev\n"
            "Schemas: dbt_anycompany_raw, dbt_anycompany_staging, dbt_anycompany_marts"
        ),
    )

    anycompany_analytics >> notify_success
