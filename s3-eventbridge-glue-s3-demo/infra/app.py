#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.pipeline_stack import PipelineStack

app = cdk.App()

PipelineStack(
    app,
    "S3EventBridgeGluePipelineStack",
    env=cdk.Environment(region="eu-west-1"),
)

app.synth()
