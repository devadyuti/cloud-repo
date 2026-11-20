#!/usr/bin/env python3
"""CDK entry point for the Classic MWAA Demo."""

import aws_cdk as cdk

from stacks.vpc_stack import VpcStack
from stacks.mwaa_stack import MwaaStack
from stacks.ecs_stack import EcsStack
from stacks.monitoring_stack import MonitoringStack

app = cdk.App()

env = cdk.Environment(
    account="123456789012",
    region="eu-west-1",
)

vpc_stack = VpcStack(app, "MwaaVpcStack", env=env)

mwaa_stack = MwaaStack(
    app,
    "MwaaStack",
    vpc=vpc_stack.vpc,
    mwaa_sg=vpc_stack.mwaa_sg,
    env=env,
)
mwaa_stack.add_dependency(vpc_stack)

ecs_stack = EcsStack(app, "MwaaEcsStack", vpc=vpc_stack.vpc, env=env)
ecs_stack.add_dependency(vpc_stack)

monitoring_stack = MonitoringStack(
    app,
    "MwaaMonitoringStack",
    mwaa_environment_name=mwaa_stack.environment_name,
    env=env,
)
monitoring_stack.add_dependency(mwaa_stack)

# Apply tags to all stacks
for stack in [vpc_stack, mwaa_stack, ecs_stack, monitoring_stack]:
    cdk.Tags.of(stack).add("Project", "mwaa-demo")
    cdk.Tags.of(stack).add("Owner", "demo-owner")

app.synth()
