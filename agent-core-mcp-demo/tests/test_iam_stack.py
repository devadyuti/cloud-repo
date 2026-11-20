"""Tests for infra.stacks.iam_stack CDK construct.

Synthesizes the IAMStack and verifies the IAM roles, policies, and outputs
match the expected configuration.
"""

import json

import pytest
from aws_cdk import App
from aws_cdk.assertions import Match, Template

from infra.stacks.iam_stack import IAMStack


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def template():
    """Synthesize IAMStack and return its CloudFormation template."""
    app = App()
    stack = IAMStack(app, "TestIAMStack")
    return Template.from_stack(stack)


# ---------------------------------------------------------------------------
# S3 Tables Role
# ---------------------------------------------------------------------------


class TestS3TablesRole:
    def test_role_exists_with_correct_trust_policy(self, template):
        """S3 Tables role is assumed by bedrock-agentcore service."""
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "RoleName": "AgentCoreS3TablesRole",
                "AssumeRolePolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Effect": "Allow",
                                    "Principal": {
                                        "Service": "bedrock-agentcore.amazonaws.com"
                                    },
                                    "Action": "sts:AssumeRole",
                                }
                            )
                        ]
                    ),
                },
            },
        )

    def test_s3_tables_full_access_policy(self, template):
        """S3 Tables role includes S3TablesFullAccess policy statement."""
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Sid": "S3TablesFullAccess",
                                    "Effect": "Allow",
                                    "Action": "s3tables:*",
                                    "Resource": "*",
                                }
                            )
                        ]
                    ),
                },
            },
        )

    def test_s3_read_access_policy(self, template):
        """S3 Tables role includes S3ReadAccess policy statement."""
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Sid": "S3ReadAccess",
                                    "Effect": "Allow",
                                    "Action": ["s3:GetObject", "s3:ListBucket"],
                                    "Resource": "*",
                                }
                            )
                        ]
                    ),
                },
            },
        )

    def test_ecr_pull_access_policy(self, template):
        """S3 Tables role includes ECRPullAccess policy for container image pulls."""
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Sid": "ECRPullAccess",
                                    "Effect": "Allow",
                                    "Action": [
                                        "ecr:GetAuthorizationToken",
                                        "ecr:BatchGetImage",
                                        "ecr:GetDownloadUrlForLayer",
                                        "ecr:BatchCheckLayerAvailability",
                                    ],
                                    "Resource": "*",
                                }
                            )
                        ]
                    ),
                },
            },
        )


# ---------------------------------------------------------------------------
# Redshift Role
# ---------------------------------------------------------------------------


class TestRedshiftRole:
    def test_role_exists_with_correct_trust_policy(self, template):
        """Redshift role is assumed by bedrock-agentcore service."""
        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "RoleName": "AgentCoreRedshiftRole",
                "AssumeRolePolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Effect": "Allow",
                                    "Principal": {
                                        "Service": "bedrock-agentcore.amazonaws.com"
                                    },
                                    "Action": "sts:AssumeRole",
                                }
                            )
                        ]
                    ),
                },
            },
        )

    def test_redshift_data_api_access_policy(self, template):
        """Redshift role includes RedshiftDataAPIAccess policy statement."""
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Sid": "RedshiftDataAPIAccess",
                                    "Effect": "Allow",
                                    "Action": Match.array_with(
                                        [
                                            "redshift:DescribeClusters",
                                            "redshift-data:ExecuteStatement",
                                        ]
                                    ),
                                    "Resource": "*",
                                }
                            )
                        ]
                    ),
                },
            },
        )

    def test_ecr_pull_access_policy(self, template):
        """Redshift role also includes ECRPullAccess for container image pulls."""
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Sid": "ECRPullAccess",
                                    "Effect": "Allow",
                                    "Action": [
                                        "ecr:GetAuthorizationToken",
                                        "ecr:BatchGetImage",
                                        "ecr:GetDownloadUrlForLayer",
                                        "ecr:BatchCheckLayerAvailability",
                                    ],
                                    "Resource": "*",
                                }
                            )
                        ]
                    ),
                },
            },
        )


# ---------------------------------------------------------------------------
# CloudFormation Outputs
# ---------------------------------------------------------------------------


class TestOutputs:
    def test_s3_tables_role_arn_exported(self, template):
        """S3 Tables role ARN is exported."""
        template.has_output(
            "S3TablesRoleArn",
            {
                "Export": {"Name": "AgentCoreMCPDemo-S3TablesRoleArn"},
            },
        )

    def test_redshift_role_arn_exported(self, template):
        """Redshift role ARN is exported."""
        template.has_output(
            "RedshiftRoleArn",
            {
                "Export": {"Name": "AgentCoreMCPDemo-RedshiftRoleArn"},
            },
        )
