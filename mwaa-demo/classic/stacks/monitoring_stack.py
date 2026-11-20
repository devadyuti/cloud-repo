"""Monitoring Stack — CloudWatch dashboard for classic MWAA environment health."""

from aws_cdk import (
    Duration,
    Stack,
    aws_cloudwatch as cloudwatch,
)
from constructs import Construct


class MonitoringStack(Stack):
    """Creates a CloudWatch dashboard with classic MWAA health metrics, ECS task metrics, and alarms."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        mwaa_environment_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # =====================================================================
        # MWAA Environment Health Metrics
        # =====================================================================
        queued_tasks = cloudwatch.Metric(
            namespace="AWS/MWAA",
            metric_name="QueuedTasks",
            dimensions_map={"Environment": mwaa_environment_name},
            statistic="Average",
            period=Duration.minutes(1),
        )

        running_tasks = cloudwatch.Metric(
            namespace="AWS/MWAA",
            metric_name="RunningTasks",
            dimensions_map={"Environment": mwaa_environment_name},
            statistic="Average",
            period=Duration.minutes(1),
        )

        scheduler_heartbeat = cloudwatch.Metric(
            namespace="AWS/MWAA",
            metric_name="SchedulerHeartbeat",
            dimensions_map={"Environment": mwaa_environment_name},
            statistic="Average",
            period=Duration.minutes(1),
        )

        task_instance_failures = cloudwatch.Metric(
            namespace="AWS/MWAA",
            metric_name="TaskInstanceFailures",
            dimensions_map={"Environment": mwaa_environment_name},
            statistic="Sum",
            period=Duration.minutes(5),
        )

        task_instance_successes = cloudwatch.Metric(
            namespace="AWS/MWAA",
            metric_name="TaskInstanceSuccesses",
            dimensions_map={"Environment": mwaa_environment_name},
            statistic="Sum",
            period=Duration.minutes(5),
        )

        # =====================================================================
        # Worker Scaling Metrics
        # =====================================================================
        total_workers = cloudwatch.Metric(
            namespace="AWS/MWAA",
            metric_name="NumWorkers",
            dimensions_map={"Environment": mwaa_environment_name},
            statistic="Average",
            period=Duration.minutes(1),
        )

        # =====================================================================
        # ECS Task Metrics (container execution DAG)
        # =====================================================================
        ecs_running_tasks = cloudwatch.Metric(
            namespace="AWS/ECS",
            metric_name="RunningTaskCount",
            dimensions_map={
                "ClusterName": "any-company-demo-cluster",
            },
            statistic="Average",
            period=Duration.minutes(1),
        )

        ecs_cpu_utilization = cloudwatch.Metric(
            namespace="AWS/ECS",
            metric_name="CPUUtilization",
            dimensions_map={
                "ClusterName": "any-company-demo-cluster",
            },
            statistic="Average",
            period=Duration.minutes(1),
        )

        # =====================================================================
        # Logs Insights — Task execution logs
        # =====================================================================
        task_logs_query = (
            "fields @timestamp, @message\n"
            '| filter @message like /(?i)(error|fail|success|completed)/\n'
            "| stats count() as eventCount by bin(5m)\n"
            "| sort @timestamp desc"
        )

        # =====================================================================
        # Dashboard Assembly
        # =====================================================================
        self._dashboard = cloudwatch.Dashboard(
            self,
            "MwaaDashboard",
            dashboard_name="mwaa-classic-dashboard",
            widgets=[
                # --- Section: Environment Health ---
                [
                    cloudwatch.TextWidget(
                        markdown="# MWAA Classic Environment Health",
                        width=24,
                        height=1,
                    ),
                ],
                # Row 1: Task queue and execution
                [
                    cloudwatch.GraphWidget(
                        title="Queued Tasks",
                        left=[queued_tasks],
                        width=8,
                        height=6,
                    ),
                    cloudwatch.GraphWidget(
                        title="Running Tasks",
                        left=[running_tasks],
                        width=8,
                        height=6,
                    ),
                    cloudwatch.GraphWidget(
                        title="Workers Active",
                        left=[total_workers],
                        width=8,
                        height=6,
                    ),
                ],
                # Row 2: Scheduler and task outcomes
                [
                    cloudwatch.GraphWidget(
                        title="Scheduler Heartbeat",
                        left=[scheduler_heartbeat],
                        width=8,
                        height=6,
                    ),
                    cloudwatch.GraphWidget(
                        title="Task Successes vs Failures",
                        left=[task_instance_successes],
                        right=[task_instance_failures],
                        width=8,
                        height=6,
                    ),
                    cloudwatch.SingleValueWidget(
                        title="Task Failures (last 5m)",
                        metrics=[task_instance_failures],
                        width=8,
                        height=6,
                    ),
                ],
                # --- Section: ECS Container Tasks ---
                [
                    cloudwatch.TextWidget(
                        markdown="# ECS Container Workloads",
                        width=24,
                        height=1,
                    ),
                ],
                # Row 3: ECS metrics
                [
                    cloudwatch.GraphWidget(
                        title="ECS Running Tasks",
                        left=[ecs_running_tasks],
                        width=12,
                        height=6,
                    ),
                    cloudwatch.GraphWidget(
                        title="ECS CPU Utilization (%)",
                        left=[ecs_cpu_utilization],
                        width=12,
                        height=6,
                    ),
                ],
                # --- Section: Logs ---
                [
                    cloudwatch.TextWidget(
                        markdown="# Task Execution Logs",
                        width=24,
                        height=1,
                    ),
                ],
                # Row 4: Logs Insights
                [
                    cloudwatch.LogQueryWidget(
                        title="Task Log Events (errors/successes)",
                        log_group_names=[
                            f"airflow-{mwaa_environment_name}-Task",
                            "/ecs/any-company-etl-task",
                        ],
                        query_string=task_logs_query,
                        width=24,
                        height=6,
                    ),
                ],
            ],
        )
