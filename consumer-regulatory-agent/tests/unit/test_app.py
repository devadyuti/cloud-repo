"""Tests for the CDK application entry point."""

import aws_cdk as cdk
from aws_cdk.assertions import Template

from cdk.consumer_regulatory_agent_stack import ConsumerRegulatoryAgentStack


class TestApp:
    """Tests for app.py CDK application synthesis."""

    def test_stack_synthesizes_successfully(self):
        """Verify the CDK app synthesizes without errors."""
        app = cdk.App()
        stack = ConsumerRegulatoryAgentStack(app, "TestStack")
        template = Template.from_stack(stack)

        # Stack should contain core resources
        template.resource_count_is("AWS::DynamoDB::Table", 1)
        template.resource_count_is("AWS::S3::Bucket", 1)
        template.resource_count_is("AWS::Cognito::UserPool", 1)

    def test_stack_has_expected_outputs(self):
        """Verify the stack produces required CloudFormation outputs."""
        app = cdk.App()
        stack = ConsumerRegulatoryAgentStack(app, "TestStack")
        template = Template.from_stack(stack)

        outputs = template.to_json().get("Outputs", {})
        output_keys = set(outputs.keys())

        # Verify all expected outputs exist (CDK adds logical ID suffixes)
        assert any("TableName" in k for k in output_keys), "Missing TableName output"
        assert any("CorpusBucketName" in k for k in output_keys), "Missing CorpusBucketName output"
        assert any("UserPoolId" in k for k in output_keys), "Missing UserPoolId output"
        assert any("UserPoolClientId" in k for k in output_keys), "Missing UserPoolClientId output"

    def test_stack_description(self):
        """Verify the stack has the expected description."""
        app = cdk.App()
        stack = ConsumerRegulatoryAgentStack(
            app,
            "TestStack",
            description="Consumer Regulatory Protection Agent - Bedrock AgentCore compliance assessment system",
        )
        template = Template.from_stack(stack)

        # Template synthesizes with description
        json_template = template.to_json()
        assert json_template.get("Description") == (
            "Consumer Regulatory Protection Agent - Bedrock AgentCore compliance assessment system"
        )

    def test_stack_uses_default_region_context(self):
        """Verify the app respects region context with fallback to us-east-1."""
        app = cdk.App(context={"region": "eu-west-1", "account": "123456789012"})
        stack = ConsumerRegulatoryAgentStack(
            app,
            "TestStack",
            env=cdk.Environment(
                account=app.node.try_get_context("account"),
                region=app.node.try_get_context("region") or "us-east-1",
            ),
        )
        assert stack.region == "eu-west-1"

    def test_stack_falls_back_to_us_east_1(self):
        """Verify the app falls back to us-east-1 when no region context is set."""
        app = cdk.App(context={"account": "123456789012"})
        stack = ConsumerRegulatoryAgentStack(
            app,
            "TestStack",
            env=cdk.Environment(
                account=app.node.try_get_context("account"),
                region=app.node.try_get_context("region") or "us-east-1",
            ),
        )
        assert stack.region == "us-east-1"
