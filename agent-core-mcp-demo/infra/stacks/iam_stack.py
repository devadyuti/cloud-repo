"""IAM stack for AgentCore MCP Demo runtime roles."""

from aws_cdk import Stack, CfnOutput
from aws_cdk import aws_iam as iam
from constructs import Construct


class IAMStack(Stack):
    """Defines IAM roles assumed by AgentCore runtimes for data access."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # AgentCore S3 Tables Runtime Role
        self.s3_tables_role = iam.Role(
            self,
            "AgentCoreS3TablesRole",
            role_name="AgentCoreS3TablesRole",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            description="IAM role for AgentCore S3 Tables MCP server runtime",
        )

        self.s3_tables_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3TablesFullAccess",
                effect=iam.Effect.ALLOW,
                actions=["s3tables:*"],
                resources=["*"],
            )
        )

        self.s3_tables_role.add_to_policy(
            iam.PolicyStatement(
                sid="S3ReadAccess",
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=["*"],
            )
        )

        self.s3_tables_role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRPullAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchCheckLayerAvailability",
                ],
                resources=["*"],
            )
        )

        # AgentCore Redshift Runtime Role
        self.redshift_role = iam.Role(
            self,
            "AgentCoreRedshiftRole",
            role_name="AgentCoreRedshiftRole",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            description="IAM role for AgentCore Redshift MCP server runtime",
        )

        self.redshift_role.add_to_policy(
            iam.PolicyStatement(
                sid="RedshiftDataAPIAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "redshift:DescribeClusters",
                    "redshift:GetClusterCredentials",
                    "redshift-serverless:ListWorkgroups",
                    "redshift-serverless:GetWorkgroup",
                    "redshift-data:ExecuteStatement",
                    "redshift-data:GetStatementResult",
                    "redshift-data:DescribeStatement",
                    "redshift-data:ListStatements",
                ],
                resources=["*"],
            )
        )

        self.redshift_role.add_to_policy(
            iam.PolicyStatement(
                sid="ECRPullAccess",
                effect=iam.Effect.ALLOW,
                actions=[
                    "ecr:GetAuthorizationToken",
                    "ecr:BatchGetImage",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:BatchCheckLayerAvailability",
                ],
                resources=["*"],
            )
        )

        # CloudFormation exports
        CfnOutput(
            self,
            "S3TablesRoleArn",
            value=self.s3_tables_role.role_arn,
            export_name="AgentCoreMCPDemo-S3TablesRoleArn",
            description="ARN of the IAM role for S3 Tables AgentCore runtime",
        )

        CfnOutput(
            self,
            "RedshiftRoleArn",
            value=self.redshift_role.role_arn,
            export_name="AgentCoreMCPDemo-RedshiftRoleArn",
            description="ARN of the IAM role for Redshift AgentCore runtime",
        )
