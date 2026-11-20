#!/usr/bin/env python3
"""CDK app entry point for the CI/CD pipeline infrastructure."""

import aws_cdk as cdk

from pipeline_stack import PipelineStack

app = cdk.App()

PipelineStack(
    app,
    "DemoOrdersApiPipelineStack",
    env=cdk.Environment(region="eu-west-1"),
    description="CI/CD pipeline for Demo Orders API — CodeBuild, CodePipeline, CodeDeploy (via SAM)",
)

app.synth()
