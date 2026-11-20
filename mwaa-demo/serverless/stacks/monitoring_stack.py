"""Monitoring Stack — CloudWatch log group dashboard for MWAA Serverless workflows."""

from aws_cdk import (
    Stack,
    aws_cloudwatch as cloudwatch,
)
from constructs import Construct


class MonitoringStack(Stack):
    """Creates a CloudWatch dashboard with Logs Insights queries for the serverless trigger."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        lambda_function_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        lambda_log_group = f"/aws/lambda/{lambda_function_name}"

        # =====================================================================
        # Dashboard — Log Groups Only
        # =====================================================================
        self._dashboard = cloudwatch.Dashboard(
            self,
            "ServerlessDashboard",
            dashboard_name="mwaa-serverless-dashboard",
            widgets=[
                [
                    cloudwatch.TextWidget(
                        markdown="# MWAA Serverless — Trigger Logs",
                        width=24,
                        height=1,
                    ),
                ],
                [
                    cloudwatch.LogQueryWidget(
                        title="Recent Trigger Invocations",
                        log_group_names=[lambda_log_group],
                        query_string=(
                            "fields @timestamp, @message\n"
                            "| filter @message like /workflow|WorkflowArn|start_workflow_run/\n"
                            "| sort @timestamp desc\n"
                            "| limit 50"
                        ),
                        width=24,
                        height=6,
                    ),
                ],
                [
                    cloudwatch.LogQueryWidget(
                        title="Errors & Failures",
                        log_group_names=[lambda_log_group],
                        query_string=(
                            "fields @timestamp, @message\n"
                            "| filter @message like /(?i)(error|exception|fail|traceback)/\n"
                            "| sort @timestamp desc\n"
                            "| limit 25"
                        ),
                        width=24,
                        height=6,
                    ),
                ],
                [
                    cloudwatch.LogQueryWidget(
                        title="Invocation Volume (5-min buckets)",
                        log_group_names=[lambda_log_group],
                        query_string=(
                            "filter @type = \"REPORT\"\n"
                            "| stats count() as invocations, "
                            "avg(@duration) as avgDurationMs, "
                            "max(@duration) as maxDurationMs "
                            "by bin(5m)"
                        ),
                        width=24,
                        height=6,
                    ),
                ],
            ],
        )
