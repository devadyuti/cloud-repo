"""Lambda Stack — DAG trigger function for invoking MWAA DAGs via REST API."""

import os

from aws_cdk import (
    Aws,
    Duration,
    Stack,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
)
from constructs import Construct


class LambdaStack(Stack):
    """Creates a Lambda function that triggers MWAA DAGs programmatically."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        mwaa_environment_name: str,
        dags_bucket_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Import the bucket by name to avoid cross-stack cyclic dependency
        dags_bucket = s3.Bucket.from_bucket_name(
            self, "DagsBucket", dags_bucket_name
        )

        # --- Lambda Function ---
        self._function = _lambda.Function(
            self,
            "DagTriggerFunction",
            function_name="mwaa-dag-trigger",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="trigger_dag.handler",
            code=_lambda.Code.from_asset(
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "lambda")
            ),
            timeout=Duration.seconds(30),
            environment={
                "MWAA_ENV_NAME": mwaa_environment_name,
                "WORKFLOW_ARN": "arn:aws:airflow-serverless:eu-west-1:123456789012:workflow/s3-event-lambda-serverless-HvYwSyW3qO",
            },
        )

        # --- IAM Permissions ---
        # MWAA requires the resource to be the role ARN, not the environment ARN.
        # Format: arn:aws:airflow:{region}:{account}:role/{env-name}/{airflow-role}
        # Using Admin role to allow full DAG trigger access via REST API.
        mwaa_env_arn = (
            f"arn:aws:airflow:{Stack.of(self).region}:{Stack.of(self).account}"
            f":environment/{mwaa_environment_name}"
        )
        mwaa_role_arn = (
            f"arn:aws:airflow:{Stack.of(self).region}:{Stack.of(self).account}"
            f":role/{mwaa_environment_name}/Admin"
        )

        self._function.add_to_role_policy(
            iam.PolicyStatement(
                sid="MwaaCreateWebLoginToken",
                actions=[
                    "airflow:CreateWebLoginToken",
                    "airflow:CreateCliToken",
                ],
                resources=[mwaa_role_arn],
            )
        )

        self._function.add_to_role_policy(
            iam.PolicyStatement(
                sid="MwaaInvokeRestApi",
                actions=[
                    "airflow:InvokeRestApi",
                ],
                resources=[mwaa_env_arn, mwaa_role_arn],
            )
        )

        self._function.add_to_role_policy(
            iam.PolicyStatement(
                sid="MwaaServerlessStartWorkflow",
                actions=[
                    "airflow-serverless:StartWorkflowRun",
                    "airflow-serverless:GetWorkflowRun",
                ],
                resources=["arn:aws:airflow-serverless:eu-west-1:123456789012:workflow/*"],
            )
        )

        # Allow Lambda to publish custom metrics for the serverless dashboard
        self._function.add_to_role_policy(
            iam.PolicyStatement(
                sid="CloudWatchPutMetrics",
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "cloudwatch:namespace": "MWAADemo/Serverless",
                    }
                },
            )
        )

        # --- MWAA Serverless Workflow Execution Role ---
        # This role is assumed by the airflow-serverless service to execute
        # workflow tasks (e.g. S3CreateObjectOperator writing to the bucket).
        self._workflow_role = iam.Role(
            self,
            "MwaaServerlessWorkflowRole",
            role_name="MwaaServerlessWorkflowRole",
            assumed_by=iam.ServicePrincipal("airflow-serverless.amazonaws.com"),
            description="Execution role for MWAA Serverless workflows",
        )

        # Workflow writes output files to the dags bucket (serverless/output/)
        self._workflow_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3WriteWorkflowOutput",
                actions=[
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:ListBucket",
                ],
                resources=[
                    dags_bucket.bucket_arn,
                    f"{dags_bucket.bucket_arn}/serverless/*",
                ],
            )
        )

        # Workflow needs to read its own definition from S3
        self._workflow_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3ReadWorkflowDefinition",
                actions=["s3:GetObject"],
                resources=[
                    f"{dags_bucket.bucket_arn}/dags/serverless-workflows/*",
                ],
            )
        )

        # Workflow needs CloudWatch Logs permissions for observability
        self._workflow_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudWatchLogsWrite",
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[
                    f"arn:aws:logs:{Aws.REGION}:{Aws.ACCOUNT_ID}:log-group:/aws/mwaa-serverless/*",
                ],
            )
        )

        # --- S3 Event Trigger ---
        # Auto-trigger ETL pipeline when files land in serverless/incoming/
        dags_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(self._function),
            s3.NotificationKeyFilter(prefix="serverless/incoming/"),
        )

    @property
    def function(self) -> _lambda.IFunction:
        """The DAG trigger Lambda function."""
        return self._function

    @property
    def workflow_role(self) -> iam.IRole:
        """The MWAA Serverless workflow execution role."""
        return self._workflow_role
