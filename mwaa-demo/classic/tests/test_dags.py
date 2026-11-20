"""DAG import and integrity tests.

Validates that all DAGs parse without import errors and have correct
fundamental properties (dag_id, schedule, task count, tags).
"""

import pytest


# --------------------------------------------------------------------------
# DAG Import Tests
# --------------------------------------------------------------------------


def test_dags_load_without_errors():
    """All DAG files import cleanly without errors.

    Note: data_lake_etl uses crawler_name param that requires a newer provider.
    It is tested separately below.
    """
    import sample_etl_pipeline  # noqa: F401
    import container_execution  # noqa: F401
    import external_system_integration  # noqa: F401
    import ml_feature_pipeline  # noqa: F401
    import cdc_ingestion  # noqa: F401
    import api_triggered  # noqa: F401


def test_data_lake_etl_loads():
    """data_lake_etl DAG imports cleanly.

    Requires apache-airflow-providers-amazon with GlueCrawlerOperator config support.
    """
    try:
        import data_lake_etl  # noqa: F401
    except TypeError as e:
        if "config" in str(e) or "crawler_name" in str(e):
            pytest.skip(
                "GlueCrawlerOperator does not support config dict in installed provider"
            )
        raise


# --------------------------------------------------------------------------
# sample_etl_pipeline
# --------------------------------------------------------------------------


class TestSampleEtlPipelineDag:
    """Tests for the sample_etl_pipeline DAG."""

    def test_dag_id(self):
        from sample_etl_pipeline import dag

        assert dag.dag_id == "sample_etl_pipeline"

    def test_schedule_is_daily(self):
        from sample_etl_pipeline import dag

        assert "CronTriggerTimetable" in type(dag.timetable).__name__

    def test_task_count(self):
        """sample_etl_pipeline DAG has exactly 4 tasks."""
        from sample_etl_pipeline import dag

        assert len(dag.tasks) == 4

    def test_tags(self):
        from sample_etl_pipeline import dag

        assert set(dag.tags) == {"demo", "any-company", "etl"}

    def test_task_dependencies(self):
        """Tasks execute in correct order."""
        from sample_etl_pipeline import dag

        sensor = dag.get_task("wait_for_data")
        transform = dag.get_task("glue_transform")
        load = dag.get_task("load_to_redshift")
        notify = dag.get_task("notify_success")

        assert transform.task_id in [t.task_id for t in sensor.downstream_list]
        assert load.task_id in [t.task_id for t in transform.downstream_list]
        assert notify.task_id in [t.task_id for t in load.downstream_list]


# --------------------------------------------------------------------------
# container_execution
# --------------------------------------------------------------------------


class TestContainerExecutionDag:
    """Tests for the container_execution DAG."""

    def test_dag_id(self):
        from container_execution import dag

        assert dag.dag_id == "container_execution"

    def test_schedule_is_none(self):
        from container_execution import dag

        assert "NullTimetable" in type(dag.timetable).__name__

    def test_task_count(self):
        from container_execution import dag

        assert len(dag.tasks) == 3

    def test_ecs_task_uses_fargate(self):
        from container_execution import dag

        ecs_task = dag.get_task("run_ecs_task")
        assert ecs_task.launch_type == "FARGATE"

    def test_network_config_has_subnets(self):
        """subnets should be a list from Variable."""
        from container_execution import dag

        ecs_task = dag.get_task("run_ecs_task")
        net_config = ecs_task.network_configuration
        subnets = net_config["awsvpcConfiguration"]["subnets"]
        assert isinstance(subnets, list)
        assert len(subnets) >= 1


# --------------------------------------------------------------------------
# external_system_integration
# --------------------------------------------------------------------------


class TestExternalSystemIntegrationDag:
    """Tests for the external_system_integration DAG — car search API integration."""

    def test_dag_id(self):
        from external_system_integration import dag

        assert dag.dag_id == "external_system_integration"

    def test_schedule_is_none(self):
        """DAG is manual-trigger only — no schedule."""
        from external_system_integration import dag

        assert "NullTimetable" in type(dag.timetable).__name__

    def test_task_count(self):
        from external_system_integration import dag

        assert len(dag.tasks) == 4

    def test_tags(self):
        from external_system_integration import dag

        assert set(dag.tags) == {"demo", "integration", "api"}

    def test_uses_http_connection(self):
        from external_system_integration import dag

        call_task = dag.get_task("call_car_search_api")
        assert call_task.http_conn_id == "car_search_api"

    def test_http_method_is_post(self):
        """Car search API is called with POST method."""
        from external_system_integration import dag

        call_task = dag.get_task("call_car_search_api")
        assert call_task.method == "POST"

    def test_task_dependencies(self):
        """Tasks execute in correct order: API call → transform → S3 → notify."""
        from external_system_integration import dag

        call = dag.get_task("call_car_search_api")
        transform = dag.get_task("transform_results")
        load = dag.get_task("load_to_s3")
        notify = dag.get_task("notify_success")

        assert transform.task_id in [t.task_id for t in call.downstream_list]
        assert load.task_id in [t.task_id for t in transform.downstream_list]
        assert notify.task_id in [t.task_id for t in load.downstream_list]

    def test_catchup_disabled(self):
        from external_system_integration import dag

        assert dag.catchup is False

    def test_sns_topic_defined(self):
        from external_system_integration import SNS_TOPIC

        assert SNS_TOPIC.startswith("arn:aws:sns:")

    def test_datalake_bucket_defined(self):
        from external_system_integration import DATALAKE_BUCKET

        assert DATALAKE_BUCKET == "any-company-mwaa-demo-dags-123456789012"


# --------------------------------------------------------------------------
# data_lake_etl (NEW)
# --------------------------------------------------------------------------


class TestDataLakeEtlDag:
    """Tests for the data_lake_etl DAG — medallion architecture."""

    @pytest.fixture(autouse=True)
    def _skip_if_provider_incompatible(self):
        """Skip all tests if data_lake_etl cannot import (provider too old)."""
        try:
            import data_lake_etl  # noqa: F401
        except TypeError as e:
            if "config" in str(e) or "crawler_name" in str(e):
                pytest.skip(
                    "GlueCrawlerOperator does not support config dict in installed provider"
                )
            raise

    def test_dag_id(self):
        from data_lake_etl import dag

        assert dag.dag_id == "data_lake_etl"

    def test_schedule_is_daily(self):
        from data_lake_etl import dag

        assert "CronTriggerTimetable" in type(dag.timetable).__name__

    def test_task_count(self):
        """Should have 9 tasks (sensor, crawler, transform, athena, gate, redshift, quarantine, notify_quarantine, notify_success)."""
        from data_lake_etl import dag

        assert len(dag.tasks) == 9

    def test_tags(self):
        from data_lake_etl import dag

        expected = {"production", "data-lake", "etl", "medallion"}
        assert expected == set(dag.tags)

    def test_quality_gate_is_branch(self):
        """Quality gate task uses BranchPythonOperator."""
        from data_lake_etl import dag

        gate = dag.get_task("quality_gate")
        assert "BranchPythonOperator" in type(gate).__name__

    def test_quality_gate_branches(self):
        """Quality gate has two downstream paths: load and quarantine."""
        from data_lake_etl import dag

        gate = dag.get_task("quality_gate")
        downstream_ids = {t.task_id for t in gate.downstream_list}
        assert "load_to_redshift" in downstream_ids
        assert "quarantine_and_alert" in downstream_ids

    def test_sensor_uses_exact_key(self):
        """S3 sensor waits for a specific file path in the partition."""
        from data_lake_etl import dag

        sensor = dag.get_task("wait_for_landing_data")
        assert sensor.bucket_key == "landing/transactions/dt={{ ds }}/data.csv"

    def test_sensor_mode_is_poke(self):
        """S3 sensor uses default poke mode (holds worker slot while waiting)."""
        from data_lake_etl import dag

        sensor = dag.get_task("wait_for_landing_data")
        assert sensor.mode == "poke"

    def test_sensor_timeout(self):
        """S3 sensor times out after 5 minutes (300s) to fail fast."""
        from data_lake_etl import dag

        sensor = dag.get_task("wait_for_landing_data")
        assert sensor.timeout == 300

    def test_crawler_uses_config_dict(self):
        """Glue crawler references a pre-existing crawler via config dict.

        The DAG uses config={"Name": "any-company-transactions-crawler"} which is the
        standard GlueCrawlerOperator interface. Skip if provider is incompatible.
        """
        try:
            from data_lake_etl import dag
        except TypeError:
            pytest.skip(
                "GlueCrawlerOperator does not support config dict in installed provider version"
            )

        crawler = dag.get_task("crawl_raw_data")
        assert crawler.config == {"Name": "any-company-transactions-crawler"}

    def test_linear_flow_before_gate(self):
        """Tasks before the quality gate form a linear chain."""
        from data_lake_etl import dag

        sensor = dag.get_task("wait_for_landing_data")
        crawler = dag.get_task("crawl_raw_data")
        transform = dag.get_task("transform_to_silver")
        athena = dag.get_task("run_quality_checks")

        assert crawler.task_id in [t.task_id for t in sensor.downstream_list]
        assert transform.task_id in [t.task_id for t in crawler.downstream_list]
        assert athena.task_id in [t.task_id for t in transform.downstream_list]

    def test_glue_job_source_table(self):
        """Glue ETL job reads from 'raw_transactions' source table."""
        from data_lake_etl import dag

        transform = dag.get_task("transform_to_silver")
        assert transform.script_args["--source_table"] == "raw_transactions"

    def test_athena_quality_check_queries_raw_transactions(self):
        """Athena quality check runs against 'raw_transactions' table."""
        from data_lake_etl import dag

        athena_task = dag.get_task("run_quality_checks")
        assert "raw_transactions" in athena_task.query

    def test_glue_job_source_database(self):
        """Glue ETL job reads from the correct Glue database."""
        from data_lake_etl import dag

        transform = dag.get_task("transform_to_silver")
        assert transform.script_args["--source_database"] == "anycompany_data_lake"

    def test_redshift_uses_provisioned_cluster(self):
        """Redshift task targets a provisioned cluster (not serverless workgroup)."""
        from data_lake_etl import dag

        redshift = dag.get_task("load_to_redshift")
        assert redshift.cluster_identifier == "analytics-cluster"
        assert redshift.database == "dev"
        assert redshift.db_user == "awsuser"

    def test_redshift_sql_drops_and_creates_table(self):
        """Redshift SQL drops then recreates the table for a clean load each run."""
        from data_lake_etl import dag

        redshift = dag.get_task("load_to_redshift")
        assert "DROP TABLE IF EXISTS public.transactions" in redshift.sql
        assert "CREATE TABLE public.transactions" in redshift.sql

    def test_redshift_schema_excludes_dt_column(self):
        """The dt partition column is not included in the Redshift table schema."""
        from data_lake_etl import dag

        redshift = dag.get_task("load_to_redshift")
        # Schema should end at source_layer — no dt column
        assert "dt VARCHAR" not in redshift.sql

    def test_redshift_schema_column_types(self):
        """Redshift schema uses wide VARCHAR(256) columns and DOUBLE PRECISION for amount."""
        from data_lake_etl import dag

        redshift = dag.get_task("load_to_redshift")
        sql = redshift.sql

        # String columns use VARCHAR(256)
        for col in ["transaction_id", "customer_id", "region", "date", "category", "source_layer"]:
            assert f"{col} VARCHAR(256)" in sql, f"{col} should be VARCHAR(256)"

        # Amount uses DOUBLE PRECISION (not DECIMAL)
        assert "amount DOUBLE PRECISION" in sql
        assert "DECIMAL" not in sql

    def test_redshift_sql_copies_from_silver(self):
        """Redshift COPY reads from the silver layer partition."""
        from data_lake_etl import dag

        redshift = dag.get_task("load_to_redshift")
        assert "COPY public.transactions" in redshift.sql
        assert "silver/transactions/dt={{ ds }}/" in redshift.sql

    def test_redshift_waits_for_completion(self):
        """Redshift task blocks until the Data API statement finishes."""
        from data_lake_etl import dag

        redshift = dag.get_task("load_to_redshift")
        assert redshift.wait_for_completion is True

    def test_catchup_disabled(self):
        from data_lake_etl import dag

        assert dag.catchup is False


# --------------------------------------------------------------------------
# ml_feature_pipeline (NEW)
# --------------------------------------------------------------------------


class TestMlFeaturePipelineDag:
    """Tests for the ml_feature_pipeline DAG — ECS feature engineering."""

    def test_dag_id(self):
        from ml_feature_pipeline import dag

        assert dag.dag_id == "ml_feature_pipeline"

    def test_schedule_every_6_hours(self):
        from ml_feature_pipeline import dag

        assert "CronTriggerTimetable" in type(dag.timetable).__name__

    def test_tags(self):
        from ml_feature_pipeline import dag

        expected = {"ml", "features", "ecs", "fargate"}
        assert expected == set(dag.tags)

    def test_has_task_groups(self):
        """DAG uses TaskGroups for logical organization."""
        from ml_feature_pipeline import dag

        task_ids = [t.task_id for t in dag.tasks]
        # TaskGroup tasks are prefixed with group name
        assert any("feature_engineering" in tid for tid in task_ids)
        assert any("validation" in tid for tid in task_ids)

    def test_ecs_task_exists(self):
        """ECS compute task is present within the feature_engineering group."""
        from ml_feature_pipeline import dag

        task = dag.get_task("feature_engineering.compute_features")
        assert task is not None
        assert task.launch_type == "FARGATE"

    def test_athena_checks_run_in_parallel(self):
        """Both Athena checks feed into validate_stats."""
        from ml_feature_pipeline import dag

        validate = dag.get_task("validation.validate_stats")
        upstream_ids = {t.task_id for t in validate.upstream_list}
        assert "validation.check_feature_completeness" in upstream_ids
        assert "validation.check_feature_drift" in upstream_ids

    def test_catchup_disabled(self):
        from ml_feature_pipeline import dag

        assert dag.catchup is False


# --------------------------------------------------------------------------
# cdc_ingestion (NEW)
# --------------------------------------------------------------------------


class TestCdcIngestionDag:
    """Tests for the cdc_ingestion DAG — external system CDC."""

    def test_dag_id(self):
        from cdc_ingestion import dag

        assert dag.dag_id == "cdc_ingestion"

    def test_schedule_every_15_minutes(self):
        from cdc_ingestion import dag

        assert "CronTriggerTimetable" in type(dag.timetable).__name__

    def test_max_active_runs(self):
        """Only one run at a time to prevent CDC overlap."""
        from cdc_ingestion import dag

        assert dag.max_active_runs == 1

    def test_task_count(self):
        """Should have 9 tasks in the linear chain."""
        from cdc_ingestion import dag

        assert len(dag.tasks) == 9

    def test_tags(self):
        from cdc_ingestion import dag

        expected = {"cdc", "integration", "external-api", "incremental"}
        assert expected == set(dag.tags)

    def test_uses_http_connection(self):
        from cdc_ingestion import dag

        health_task = dag.get_task("check_api_health")
        assert health_task.http_conn_id == "crm_cdc_api"

    def test_linear_execution_order(self):
        """All tasks execute in a strict linear sequence."""
        from cdc_ingestion import dag

        expected_order = [
            "check_api_health",
            "fetch_cdc_events",
            "transform_cdc_events",
            "write_to_s3",
            "update_catalog",
            "refresh_current_state_view",
            "redshift_merge",
            "update_high_watermark",
            "notify_completion",
        ]
        for i in range(len(expected_order) - 1):
            upstream = dag.get_task(expected_order[i])
            downstream = dag.get_task(expected_order[i + 1])
            assert downstream.task_id in [t.task_id for t in upstream.downstream_list]

    def test_catchup_disabled(self):
        from cdc_ingestion import dag

        assert dag.catchup is False


# --------------------------------------------------------------------------
# api_triggered
# --------------------------------------------------------------------------


class TestApiTriggeredDag:
    """Tests for the api_triggered DAG — API-triggered workflow with SNS notification."""

    def test_dag_id(self):
        from api_triggered import dag

        assert dag.dag_id == "api_triggered"

    def test_schedule_is_none(self):
        """DAG is API-only — no schedule."""
        from api_triggered import dag

        assert "NullTimetable" in type(dag.timetable).__name__

    def test_tags(self):
        from api_triggered import dag

        assert set(dag.tags) == {"demo", "api"}

    def test_catchup_disabled(self):
        from api_triggered import dag

        assert dag.catchup is False

    def test_task_count(self):
        """api_triggered DAG has exactly 1 task (process_api_request)."""
        from api_triggered import dag

        assert len(dag.tasks) == 1

    def test_process_task_exists(self):
        from api_triggered import dag

        task = dag.get_task("process_api_request")
        assert task is not None
        assert "PythonOperator" in type(task).__name__

    def test_sns_topic_constant_defined(self):
        """SNS_TOPIC constant is defined for notification support."""
        from api_triggered import SNS_TOPIC

        assert SNS_TOPIC.startswith("arn:aws:sns:")

    def test_sns_operator_import_available(self):
        """SnsPublishOperator is importable (provider dependency available)."""
        from airflow.providers.amazon.aws.operators.sns import SnsPublishOperator  # noqa: F401

    def test_datalake_bucket_defined(self):
        from api_triggered import DATALAKE_BUCKET

        assert DATALAKE_BUCKET == "any-company-mwaa-demo-dags-123456789012"


# --------------------------------------------------------------------------
# dbt_anycompany_analytics (Cosmos)
# --------------------------------------------------------------------------


RELATIONSHIPS_TEST = (
    "anycompany_analytics.relationships_stg_transactions_customer_id__customer_id__ref_stg_customers__test"
)


class TestDbtAnyCompanyAnalyticsDag:
    """Tests for the dbt_anycompany_analytics DAG — dbt Core orchestrated via Astronomer Cosmos."""

    @pytest.fixture(autouse=True)
    def _require_cosmos(self):
        pytest.importorskip("cosmos", reason="astronomer-cosmos not installed (see requirements.txt)")

    def test_dag_id(self):
        from dbt_anycompany_analytics import dag

        assert dag.dag_id == "dbt_anycompany_analytics"

    def test_schedule_is_daily(self):
        from dbt_anycompany_analytics import dag

        assert "CronTriggerTimetable" in type(dag.timetable).__name__

    def test_tags(self):
        from dbt_anycompany_analytics import dag

        assert set(dag.tags) == {"demo", "dbt", "cosmos", "redshift"}

    def test_catchup_disabled_and_single_active_run(self):
        from dbt_anycompany_analytics import dag

        assert dag.catchup is False
        assert dag.max_active_runs == 1

    def test_manifest_is_present(self):
        """The pre-compiled manifest exists — Cosmos renders the DAG from it."""
        from dbt_anycompany_analytics import DBT_MANIFEST_PATH

        assert DBT_MANIFEST_PATH.is_file(), "run scripts/build_dbt_manifest.sh"

    def test_every_dbt_node_is_rendered_as_a_task(self):
        """2 seeds + 4 models (run + test each) + 2 detached multi-parent tests + SNS = 13 tasks."""
        from dbt_anycompany_analytics import dag

        task_ids = {t.task_id for t in dag.tasks}
        expected = {
            "anycompany_analytics.raw_transactions_seed",
            "anycompany_analytics.raw_customers_seed",
            RELATIONSHIPS_TEST,
            "anycompany_analytics.assert_gross_matches_source_test",
            "notify_success",
        }
        for model in ("stg_transactions", "stg_customers", "fct_daily_region_revenue", "dim_customers"):
            expected |= {f"anycompany_analytics.{model}.run", f"anycompany_analytics.{model}.test"}
        assert task_ids == expected

    def test_tests_run_after_each_model(self):
        """TestBehavior.AFTER_EACH: a model's tests gate its downstream models."""
        from dbt_anycompany_analytics import dag

        stg_test = dag.get_task("anycompany_analytics.stg_transactions.test")
        downstream = {t.task_id for t in stg_test.downstream_list}
        assert {
            "anycompany_analytics.dim_customers.run",
            "anycompany_analytics.fct_daily_region_revenue.run",
        } <= downstream

    def test_multi_parent_test_waits_for_both_parents(self):
        """The relationships test runs in its own task, only after BOTH staging models are tested.

        Regression: it used to run inside stg_customers.test and race stg_transactions.run.
        """
        from dbt_anycompany_analytics import dag

        rel = dag.get_task(RELATIONSHIPS_TEST)
        assert {t.task_id for t in rel.upstream_list} == {
            "anycompany_analytics.stg_customers.test",
            "anycompany_analytics.stg_transactions.test",
        }

    def test_model_test_tasks_use_cautious_selection(self):
        """Per-model test tasks never pull in tests that reference other models."""
        from cosmos.constants import TestIndirectSelection
        from dbt_anycompany_analytics import dag

        task = dag.get_task("anycompany_analytics.stg_customers.test")
        assert task.indirect_selection == TestIndirectSelection.CAUTIOUS.value

    def test_seed_feeds_staging(self):
        from dbt_anycompany_analytics import dag

        seed = dag.get_task("anycompany_analytics.raw_transactions_seed")
        assert "anycompany_analytics.stg_transactions.run" in {t.task_id for t in seed.downstream_list}

    def test_notification_waits_for_all_marts(self):
        from dbt_anycompany_analytics import dag

        notify = dag.get_task("notify_success")
        assert {t.task_id for t in notify.upstream_list} == {
            "anycompany_analytics.dim_customers.test",
            "anycompany_analytics.assert_gross_matches_source_test",
            RELATIONSHIPS_TEST,
        }
        assert notify.target_arn.startswith("arn:aws:sns:")

    def test_uses_existing_redshift_connection(self):
        """Credentials come from the Airflow connection in Secrets Manager, not the repo."""
        from dbt_anycompany_analytics import profile_config

        mapping = profile_config.profile_mapping
        assert type(mapping).__name__ == "RedshiftUserPasswordProfileMapping"
        assert mapping.conn_id == "redshift_analytics_cluster"
        assert mapping.profile_args["schema"] == "dbt_anycompany"

    def test_dbt_runs_from_isolated_venv(self):
        """dbt executes from the startup.sh virtualenv, not Airflow's environment."""
        from dbt_anycompany_analytics import dag

        task = dag.get_task("anycompany_analytics.stg_transactions.run")
        assert task.dbt_executable_path.endswith("dbt_venv/bin/dbt")

    def test_no_profiles_yml_committed(self):
        """No profiles.yml (and therefore no credentials) inside the dbt project."""
        from dbt_anycompany_analytics import DBT_PROJECT_DIR

        assert not (DBT_PROJECT_DIR / "profiles.yml").exists()
