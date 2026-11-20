"""Unit tests for EcsStack."""

import aws_cdk as cdk
from aws_cdk import assertions, aws_ecr_assets as ecr_assets

from stacks.vpc_stack import VpcStack
from stacks.ecs_stack import EcsStack


class TestEcsStack:
    """Tests for the ECS stack."""

    def _create_stack(self):
        """Helper to create a VPC + ECS stack pair for testing."""
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        env = cdk.Environment(account="123456789012", region="eu-west-1")
        vpc_stack = VpcStack(app, "TestVpcStack", env=env)
        ecs_stack = EcsStack(app, "TestEcsStack", vpc=vpc_stack.vpc, env=env)
        return ecs_stack

    def test_ecs_cluster_created(self):
        """EcsStack creates a Fargate cluster named any-company-demo-cluster."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::ECS::Cluster", {
            "ClusterName": "any-company-demo-cluster",
        })

    def test_docker_image_asset_created(self):
        """EcsStack creates a Docker image asset (CDK asset backed by ECR)."""
        stack = self._create_stack()
        assert stack.image_asset is not None
        assert stack.image_asset.image_uri is not None

    def test_task_definition_created(self):
        """EcsStack creates a Fargate task definition with correct CPU/memory."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::ECS::TaskDefinition", {
            "Cpu": "512",
            "Memory": "1024",
            "Family": "any-company-etl-task",
            "NetworkMode": "awsvpc",
            "RequiresCompatibilities": ["FARGATE"],
        })

    def test_task_definition_runtime_platform(self):
        """EcsStack task definition specifies X86_64 Linux runtime platform."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::ECS::TaskDefinition", {
            "RuntimePlatform": {
                "CpuArchitecture": "X86_64",
                "OperatingSystemFamily": "LINUX",
            },
        })

    def test_task_definition_container_log_config(self):
        """EcsStack task definition has a container with awslogs log driver."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::ECS::TaskDefinition", {
            "ContainerDefinitions": assertions.Match.array_with([
                assertions.Match.object_like({
                    "LogConfiguration": {
                        "LogDriver": "awslogs",
                        "Options": assertions.Match.object_like({
                            "awslogs-stream-prefix": "any-company-etl",
                        }),
                    },
                }),
            ]),
        })

    def test_task_role_has_s3_policy(self):
        """EcsStack task role has S3 read/write permissions."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:ListBucket",
                            "s3:DeleteObject",
                        ],
                        "Effect": "Allow",
                    }),
                ]),
            },
        })

    def test_log_group_created(self):
        """EcsStack creates a CloudWatch log group for the ETL task."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        template.has_resource_properties("AWS::Logs::LogGroup", {
            "LogGroupName": "/ecs/any-company-etl-task",
        })

    def test_exposes_cluster_property(self):
        """EcsStack exposes a cluster property."""
        stack = self._create_stack()
        assert stack.cluster is not None

    def test_exposes_task_definition_property(self):
        """EcsStack exposes a task_definition property."""
        stack = self._create_stack()
        assert stack.task_definition is not None

    def test_exposes_ecr_repo_property(self):
        """EcsStack exposes an ecr_repo property (backed by Docker image asset)."""
        stack = self._create_stack()
        assert stack.ecr_repo is not None

    def test_exposes_image_asset_property(self):
        """EcsStack exposes an image_asset property."""
        stack = self._create_stack()
        assert stack.image_asset is not None

    def test_docker_image_asset_targets_linux_amd64(self):
        """EcsStack Docker image asset is configured for linux/amd64 platform.

        This ensures consistent builds regardless of the host architecture
        (e.g., building on ARM-based M-series Macs).
        """
        import json
        import os

        # Use a dedicated app instance for synthesis (avoids conflicts with
        # Template.from_stack used by other tests).
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        env = cdk.Environment(account="123456789012", region="eu-west-1")
        from stacks.vpc_stack import VpcStack as Vpc
        vpc_stack = Vpc(app, "PlatformTestVpc", env=env)
        ecs_stack = EcsStack(app, "PlatformTestEcs", vpc=vpc_stack.vpc, env=env)

        cloud_assembly = app.synth()

        # Read asset manifests and verify platform is linux/amd64
        found_platform = False
        for fname in os.listdir(cloud_assembly.directory):
            if fname.endswith(".assets.json"):
                manifest_path = os.path.join(cloud_assembly.directory, fname)
                with open(manifest_path) as f:
                    manifest = json.load(f)
                for _asset_id, entry in manifest.get("dockerImages", {}).items():
                    source = entry.get("source", {})
                    if source.get("platform") == "linux/amd64":
                        found_platform = True
                        break
                if found_platform:
                    break

        assert found_platform, (
            "Expected Docker image asset to target linux/amd64 platform in asset manifest"
        )
