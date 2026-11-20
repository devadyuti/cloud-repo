#!/usr/bin/env python3
"""CDK application entry point for the Consumer Regulatory Protection Agent."""

import aws_cdk as cdk

from cdk.consumer_regulatory_agent_stack import ConsumerRegulatoryAgentStack

app = cdk.App()

ConsumerRegulatoryAgentStack(
    app,
    "ConsumerRegulatoryAgentStack",
    description="Consumer Regulatory Protection Agent - Bedrock AgentCore compliance assessment system",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
)

app.synth()
