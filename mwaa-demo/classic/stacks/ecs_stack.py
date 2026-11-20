"""ECS Stack — Fargate cluster, Docker image asset, and task definition for container workloads."""

import os

from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_ecr_assets as ecr_assets,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct


class EcsStack(Stack):
    """Creates ECS Fargate cluster, Docker image asset, and task definition for ETL containers."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- ECS Fargate Cluster ---
        self._cluster = ecs.Cluster(
            self,
            "EcsCluster",
            cluster_name="any-company-demo-cluster",
            vpc=vpc,
        )

        # --- Docker Image Asset (built locally and pushed to ECR during cdk deploy) ---
        docker_dir = os.path.join(os.path.dirname(__file__), "..", "docker")
        self._image_asset = ecr_assets.DockerImageAsset(
            self,
            "EtlImageAsset",
            directory=os.path.abspath(docker_dir),
            platform=ecr_assets.Platform.LINUX_AMD64,
        )

        # --- CloudWatch Log Group ---
        log_group = logs.LogGroup(
            self,
            "EtlLogGroup",
            log_group_name="/ecs/any-company-etl-task",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # --- Fargate Task Definition ---
        self._task_definition = ecs.FargateTaskDefinition(
            self,
            "EtlTaskDef",
            family="any-company-etl-task",
            cpu=512,
            memory_limit_mib=1024,
            runtime_platform=ecs.RuntimePlatform(
                cpu_architecture=ecs.CpuArchitecture.X86_64,
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
            ),
        )

        # Add container to task definition
        self._task_definition.add_container(
            "EtlContainer",
            image=ecs.ContainerImage.from_docker_image_asset(self._image_asset),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="any-company-etl",
                log_group=log_group,
            ),
        )

        # Grant task role S3 read/write permissions
        self._task_definition.task_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3ReadWrite",
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket",
                    "s3:DeleteObject",
                ],
                resources=["*"],
            )
        )

    @property
    def cluster(self) -> ecs.ICluster:
        """The ECS Fargate cluster."""
        return self._cluster

    @property
    def task_definition(self) -> ecs.FargateTaskDefinition:
        """The Fargate task definition for ETL workloads."""
        return self._task_definition

    @property
    def image_asset(self) -> ecr_assets.DockerImageAsset:
        """The Docker image asset for the ETL container."""
        return self._image_asset

    @property
    def ecr_repo(self):
        """The ECR repository backing the Docker image asset."""
        return self._image_asset.repository
