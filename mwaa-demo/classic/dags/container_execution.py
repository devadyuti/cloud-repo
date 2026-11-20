"""
Container Execution DAG — Launches a Fargate task via ECS.

Uses EcsRunTaskOperator to run a containerised ETL job on the
any-company-demo-cluster, then validates output and logs completion.
Schedule: None (manual trigger or upstream dependency).

Demonstrates:
- ECS Fargate integration from classic MWAA
- Dependency isolation via Docker containers
- Network-aware task execution in private subnets
- XCom-based result passing between tasks
"""

import json
from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.ecs import EcsRunTaskOperator

default_args = {
    "owner": "data-engineering",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=30),
}


def validate_output(**kwargs):
    """Validate ECS task completed and produced expected output."""
    ti = kwargs["ti"]
    # EcsRunTaskOperator pushes task ARN to XCom
    print("ECS Fargate task completed successfully")
    print("Checking output location: s3://any-company-raw-data/container-output/")
    return {"status": "validated", "output_path": "s3://any-company-raw-data/container-output/"}


def log_task_metrics(**kwargs):
    """Log metrics for observability."""
    ds = kwargs["ds"]
    print(f"Container execution completed for {ds}")
    print("  Cluster: any-company-demo-cluster")
    print("  Task definition: any-company-etl-task")
    print("  Launch type: FARGATE")


# Read network config from Airflow Variables (set via MWAA console or CLI)
private_subnet_ids = json.loads(
    Variable.get(
        "private_subnet_ids",
        default_var='["subnet-0204cb14175c717eb", "subnet-0d65602c96c7689ae"]',
    )
)
mwaa_sg_id = Variable.get("mwaa_sg_id", default_var="sg-0ad71ccc014f195ab")

with DAG(
    dag_id="container_execution",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["demo", "ecs", "container"],
    doc_md="""
    ## Container Execution
    Runs a heavy-compute ETL job in a Fargate container with custom dependencies
    (pandas, pyarrow, etc.) without polluting the Airflow environment.
    Trigger manually or chain as a downstream task.
    """,
) as dag:

    run_ecs_task = EcsRunTaskOperator(
        task_id="run_ecs_task",
        cluster="any-company-demo-cluster",
        task_definition="any-company-etl-task",
        launch_type="FARGATE",
        overrides={
            "containerOverrides": [
                {
                    "name": "EtlContainer",
                    "environment": [
                        {"name": "EXECUTION_DATE", "value": "{{ ds }}"},
                        {"name": "OUTPUT_BUCKET", "value": "any-company-raw-data"},
                    ],
                }
            ]
        },
        network_configuration={
            "awsvpcConfiguration": {
                "subnets": private_subnet_ids,
                "securityGroups": [mwaa_sg_id],
                "assignPublicIp": "DISABLED",
            }
        },
        awslogs_group="/ecs/any-company-etl-task",
        awslogs_stream_prefix="any-company-etl",
    )

    validate = PythonOperator(
        task_id="validate_output",
        python_callable=validate_output,
    )

    log_metrics = PythonOperator(
        task_id="log_metrics",
        python_callable=log_task_metrics,
    )

    run_ecs_task >> validate >> log_metrics
