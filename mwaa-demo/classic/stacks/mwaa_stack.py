"""MWAA Classic Stack — S3 bucket, IAM role, and classic MWAA environment with worker scaling."""

from pathlib import Path

from aws_cdk import (
    Aws,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_mwaa as mwaa,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
)
from constructs import Construct

# mwaa-demo/classic/ — holds requirements.txt and startup.sh
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class MwaaStack(Stack):
    """Creates a classic MWAA environment with full worker control, scheduler settings, and supporting resources."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        mwaa_sg: ec2.ISecurityGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- S3 Bucket for DAGs, plugins, requirements ---
        self._dags_bucket = s3.Bucket(
            self,
            "DagsBucket",
            bucket_name=f"any-company-mwaa-demo-dags-{Aws.ACCOUNT_ID}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
        )

        # Upload the files MWAA validates at create/update time. requirements.txt and
        # startup.sh are read from the project root so a `cdk deploy` never overwrites
        # them in S3 with stale content. startup.sh installs dbt Core into an isolated venv.
        self._initial_deploy = s3deploy.BucketDeployment(
            self,
            "InitialBucketContent",
            sources=[
                s3deploy.Source.data("dags/.gitkeep", ""),
                s3deploy.Source.data("plugins/.gitkeep", ""),
                s3deploy.Source.data(
                    "requirements.txt", (PROJECT_ROOT / "requirements.txt").read_text()
                ),
                s3deploy.Source.data(
                    "startup.sh", (PROJECT_ROOT / "startup.sh").read_text()
                ),
            ],
            destination_bucket=self._dags_bucket,
            destination_key_prefix="",
            prune=False,
        )

        # --- IAM Execution Role ---
        execution_role = iam.Role(
            self,
            "MwaaExecutionRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("airflow-env.amazonaws.com"),
                iam.ServicePrincipal("airflow.amazonaws.com"),
            ),
            description="Execution role for classic MWAA environment any-company-mwaa-demo",
        )

        # S3 — full access to the DAGs bucket
        execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3BucketAccess",
                actions=[
                    "s3:GetObject*",
                    "s3:PutObject*",
                    "s3:DeleteObject*",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                    "s3:GetBucketPublicAccessBlock",
                    "s3:GetAccountPublicAccessBlock",
                ],
                resources=[
                    self._dags_bucket.bucket_arn,
                    f"{self._dags_bucket.bucket_arn}/*",
                    "*",
                ],
            )
        )

        # Glue — StartJobRun, GetJobRun, GetJob
        execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="GlueAccess",
                actions=["glue:StartJobRun", "glue:GetJobRun", "glue:GetJob"],
                resources=["*"],
            )
        )

        # Redshift Data API
        execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="RedshiftDataApiAccess",
                actions=[
                    "redshift-data:ExecuteStatement",
                    "redshift-data:DescribeStatement",
                    "redshift-data:GetStatementResult",
                ],
                resources=["*"],
            )
        )

        # SNS — Publish
        execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="SnsPublish",
                actions=["sns:Publish"],
                resources=["*"],
            )
        )

        # ECS — RunTask, DescribeTask, StopTask (+ PassRole for task execution)
        execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="EcsAccess",
                actions=[
                    "ecs:RunTask",
                    "ecs:DescribeTasks",
                    "ecs:StopTask",
                    "iam:PassRole",
                ],
                resources=["*"],
            )
        )

        # CloudWatch Logs
        execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="CloudWatchLogsAccess",
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                    "logs:GetLogEvents",
                    "logs:GetLogRecord",
                    "logs:GetLogGroupFields",
                    "logs:GetQueryResults",
                    "logs:DescribeLogGroups",
                ],
                resources=["*"],
            )
        )

        # SQS — for Celery executor backend
        execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="SqsAccess",
                actions=[
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:GetQueueUrl",
                    "sqs:ChangeMessageVisibility",
                ],
                resources=["*"],
            )
        )

        # KMS — required for SQS encryption (Celery broker queue is KMS-encrypted)
        execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="KmsAccess",
                actions=[
                    "kms:Decrypt",
                    "kms:Encrypt",
                    "kms:GenerateDataKey",
                    "kms:DescribeKey",
                ],
                resources=["*"],
            )
        )

        # Secrets Manager — for external system connections
        execution_role.add_to_policy(
            iam.PolicyStatement(
                sid="SecretsManagerAccess",
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                ],
                resources=[
                    f"arn:aws:secretsmanager:{Aws.REGION}:{Aws.ACCOUNT_ID}:secret:airflow/*",
                ],
            )
        )

        # --- Network Configuration ---
        private_subnets = vpc.select_subnets(
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
        )

        # --- Classic MWAA Environment ---
        self._mwaa_env = mwaa.CfnEnvironment(
            self,
            "MwaaEnvironment",
            name="any-company-mwaa-demo",
            source_bucket_arn=self._dags_bucket.bucket_arn,
            dag_s3_path="dags/",
            requirements_s3_path="requirements.txt",
            startup_script_s3_path="startup.sh",
            execution_role_arn=execution_role.role_arn,
            # Classic environment configuration
            environment_class="mw1.small",
            max_workers=5,
            min_workers=1,
            schedulers=2,
            airflow_version="3.2.1",
            webserver_access_mode="PUBLIC_ONLY",
            # Logging configuration — all log types enabled
            logging_configuration=mwaa.CfnEnvironment.LoggingConfigurationProperty(
                dag_processing_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True,
                    log_level="INFO",
                ),
                scheduler_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True,
                    log_level="INFO",
                ),
                task_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True,
                    log_level="INFO",
                ),
                webserver_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True,
                    log_level="WARNING",
                ),
                worker_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True,
                    log_level="INFO",
                ),
            ),
            network_configuration=mwaa.CfnEnvironment.NetworkConfigurationProperty(
                subnet_ids=private_subnets.subnet_ids[:2],
                security_group_ids=[mwaa_sg.security_group_id],
            ),
            # Airflow configuration overrides
            airflow_configuration_options={
                "core.default_task_retries": "2",
                "core.parallelism": "32",
                "celery.worker_autoscale": "5,1",
                "scheduler.catchup_by_default": "False",
                "secrets.backend": "airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend",
                "secrets.backend_kwargs": '{"connections_prefix": "airflow/connections", "variables_prefix": "airflow/variables"}',
            },
        )

        # MWAA validates requirements.txt exists — wait for bucket content upload
        self._mwaa_env.node.add_dependency(self._initial_deploy)

    @property
    def environment_name(self) -> str:
        """The MWAA environment name."""
        return self._mwaa_env.name

    @property
    def dags_bucket(self) -> s3.IBucket:
        """The MWAA DAGs S3 bucket."""
        return self._dags_bucket
