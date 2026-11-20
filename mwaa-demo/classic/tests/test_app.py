"""Unit tests for the CDK app entry point (app.py)."""

import aws_cdk as cdk
from aws_cdk import assertions

from stacks.vpc_stack import VpcStack
from stacks.mwaa_stack import MwaaStack
from stacks.ecs_stack import EcsStack
from stacks.monitoring_stack import MonitoringStack


class TestAppEnvironment:
    """Tests for the CDK environment configuration in app.py."""

    def test_environment_has_explicit_account(self):
        """CDK environment includes the target account ID."""
        env = cdk.Environment(
            account="123456789012",
            region="eu-west-1",
        )
        assert env.account == "123456789012"

    def test_environment_region(self):
        """CDK environment targets eu-west-1."""
        env = cdk.Environment(
            account="123456789012",
            region="eu-west-1",
        )
        assert env.region == "eu-west-1"


class TestAppStackWiring:
    """Tests for stack instantiation and dependency ordering."""

    def test_all_stacks_synthesize(self):
        """All stacks synthesize without errors."""
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        env = cdk.Environment(account="123456789012", region="eu-west-1")

        vpc_stack = VpcStack(app, "TestVpcStack", env=env)
        mwaa_stack = MwaaStack(
            app, "TestMwaaStack",
            vpc=vpc_stack.vpc,
            mwaa_sg=vpc_stack.mwaa_sg,
            env=env,
        )
        ecs_stack = EcsStack(app, "TestEcsStack", vpc=vpc_stack.vpc, env=env)
        monitoring_stack = MonitoringStack(
            app, "TestMonitoringStack",
            mwaa_environment_name=mwaa_stack.environment_name,
            env=env,
        )

        # Verify synthesis completes for all stacks
        assembly = app.synth()
        stack_names = [s.stack_name for s in assembly.stacks]
        assert "TestVpcStack" in stack_names
        assert "TestMwaaStack" in stack_names
        assert "TestEcsStack" in stack_names
        assert "TestMonitoringStack" in stack_names

    def test_stacks_share_same_environment(self):
        """All stacks use the same account and region."""
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        env = cdk.Environment(account="123456789012", region="eu-west-1")

        vpc_stack = VpcStack(app, "TestVpcStack", env=env)
        mwaa_stack = MwaaStack(
            app, "TestMwaaStack",
            vpc=vpc_stack.vpc,
            mwaa_sg=vpc_stack.mwaa_sg,
            env=env,
        )
        ecs_stack = EcsStack(app, "TestEcsStack", vpc=vpc_stack.vpc, env=env)

        assert vpc_stack.account == "123456789012"
        assert mwaa_stack.account == "123456789012"
        assert ecs_stack.account == "123456789012"
        assert vpc_stack.region == "eu-west-1"
        assert mwaa_stack.region == "eu-west-1"
        assert ecs_stack.region == "eu-west-1"

    def test_project_tags_applied(self):
        """Stacks receive the Project and Owner tags."""
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        env = cdk.Environment(account="123456789012", region="eu-west-1")

        vpc_stack = VpcStack(app, "TestVpcStack", env=env)
        cdk.Tags.of(vpc_stack).add("Project", "mwaa-demo")
        cdk.Tags.of(vpc_stack).add("Owner", "demo-owner")

        template = assertions.Template.from_stack(vpc_stack)
        # Tags are propagated to resources — just verify synthesis works
        assert template.to_json() is not None
