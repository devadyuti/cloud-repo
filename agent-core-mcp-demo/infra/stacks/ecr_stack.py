"""CDK stack for ECR container image repositories.

Defines two ECR repositories for the S3 Tables and Redshift MCP server
container images used by AgentCore Runtime.
"""

from aws_cdk import Stack, CfnOutput, RemovalPolicy
from aws_cdk import aws_ecr as ecr
from constructs import Construct


class ECRStack(Stack):
    """ECR repositories for MCP server container images."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 Tables MCP Server repository
        self.s3_tables_repo = ecr.Repository(
            self,
            "S3TablesMCPServerRepo",
            repository_name="s3-tables-mcp-server",
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.DESTROY,
            empty_on_delete=True,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Retain last 5 images",
                    max_image_count=5,
                )
            ],
        )

        # Redshift MCP Server repository
        self.redshift_repo = ecr.Repository(
            self,
            "RedshiftMCPServerRepo",
            repository_name="redshift-mcp-server",
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.DESTROY,
            empty_on_delete=True,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Retain last 5 images",
                    max_image_count=5,
                )
            ],
        )

        # CloudFormation exports
        CfnOutput(
            self,
            "S3TablesMCPRepoUri",
            value=self.s3_tables_repo.repository_uri,
            export_name="AgentCore-S3TablesMCPRepoUri",
            description="ECR repository URI for S3 Tables MCP server",
        )

        CfnOutput(
            self,
            "RedshiftMCPRepoUri",
            value=self.redshift_repo.repository_uri,
            export_name="AgentCore-RedshiftMCPRepoUri",
            description="ECR repository URI for Redshift MCP server",
        )
