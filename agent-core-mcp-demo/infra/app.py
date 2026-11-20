#!/usr/bin/env python3
"""CDK app entry point for AgentCore MCP Demo infrastructure."""

import aws_cdk as cdk

from stacks.ecr_stack import ECRStack
from stacks.iam_stack import IAMStack
from stacks.cognito_stack import CognitoStack
from stacks.vpc_stack import VPCStack


app = cdk.App()

# Read configurable parameters from CDK context
account_id = app.node.try_get_context("account_id") or ""
region = app.node.try_get_context("region") or "eu-west-1"
vpc_subnet_ids = app.node.try_get_context("vpc_subnet_ids") or []
vpc_security_group_ids = app.node.try_get_context("vpc_security_group_ids") or []

env = cdk.Environment(account=account_id, region=region)

# Infrastructure stacks
ecr_stack = ECRStack(app, "AgentCoreMCPDemo-ECR", env=env)

iam_stack = IAMStack(app, "AgentCoreMCPDemo-IAM", env=env)

cognito_stack = CognitoStack(app, "AgentCoreMCPDemo-Cognito", env=env)

vpc_stack = VPCStack(
    app,
    "AgentCoreMCPDemo-VPC",
    vpc_subnet_ids=vpc_subnet_ids,
    vpc_security_group_ids=vpc_security_group_ids,
    env=env,
)

app.synth()
