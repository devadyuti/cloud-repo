#!/usr/bin/env python3
"""CDK entry point for the MWAA Serverless Demo (Lambda trigger + monitoring)."""

import aws_cdk as cdk

from stacks.lambda_stack import LambdaStack
from stacks.monitoring_stack import MonitoringStack

app = cdk.App()

env = cdk.Environment(
    account="123456789012",
    region="eu-west-1",
)

# The serverless stack references the classic MWAA environment by name
mwaa_environment_name = app.node.try_get_context("mwaa_environment_name") or "any-company-mwaa-demo"
dags_bucket_name = app.node.try_get_context("dags_bucket_name") or f"any-company-mwaa-demo-dags-123456789012"

lambda_stack = LambdaStack(
    app,
    "MwaaServerlessLambdaStack",
    mwaa_environment_name=mwaa_environment_name,
    dags_bucket_name=dags_bucket_name,
    env=env,
)

monitoring_stack = MonitoringStack(
    app,
    "MwaaServerlessMonitoringStack",
    lambda_function_name="mwaa-dag-trigger",
    env=env,
)
monitoring_stack.add_dependency(lambda_stack)

for stack in [lambda_stack, monitoring_stack]:
    cdk.Tags.of(stack).add("Project", "mwaa-demo-serverless")
    cdk.Tags.of(stack).add("Owner", "demo-owner")

app.synth()
