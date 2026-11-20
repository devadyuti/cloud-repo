"""Unit tests for VpcStack."""

import aws_cdk as cdk
from aws_cdk import assertions

from stacks.vpc_stack import VpcStack


class TestVpcStack:
    """Tests for the VPC stack."""

    def test_falls_back_to_vpc_name_when_vpc_id_missing(self):
        """VpcStack falls back to VPC name lookup when vpc_id is not provided."""
        app = cdk.App(context={})
        # Should NOT raise — falls back to Vpc.from_lookup by name
        stack = VpcStack(app, "TestVpcStack", env=cdk.Environment(
            account="123456789012", region="eu-west-1"
        ))
        assert stack.vpc is not None

    def test_uses_vpc_id_when_provided(self):
        """VpcStack uses vpc_id for lookup when provided in context."""
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        stack = VpcStack(app, "TestVpcStack", env=cdk.Environment(
            account="123456789012", region="eu-west-1"
        ))
        assert stack.vpc is not None

    def test_security_group_created(self):
        """VpcStack creates the mwaa-demo-sg security group."""
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        stack = VpcStack(app, "TestVpcStack", env=cdk.Environment(
            account="123456789012", region="eu-west-1"
        ))
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::EC2::SecurityGroup", {
            "GroupDescription": "Security group for MWAA Serverless ENIs",
            "GroupName": "mwaa-demo-sg",
        })

    def test_security_group_self_referencing_ingress(self):
        """VpcStack SG has a self-referencing ingress rule."""
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        stack = VpcStack(app, "TestVpcStack", env=cdk.Environment(
            account="123456789012", region="eu-west-1"
        ))
        template = assertions.Template.from_stack(stack)

        # Self-referencing ingress rule uses SourceSecurityGroupId
        template.has_resource_properties("AWS::EC2::SecurityGroupIngress", {
            "IpProtocol": "-1",
            "Description": "Allow all traffic from self (MWAA ENI communication)",
        })

    def test_exposes_vpc_property(self):
        """VpcStack exposes a vpc property."""
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        stack = VpcStack(app, "TestVpcStack", env=cdk.Environment(
            account="123456789012", region="eu-west-1"
        ))
        assert stack.vpc is not None

    def test_exposes_private_subnets_property(self):
        """VpcStack exposes a private_subnets property."""
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        stack = VpcStack(app, "TestVpcStack", env=cdk.Environment(
            account="123456789012", region="eu-west-1"
        ))
        assert stack.private_subnets is not None

    def test_exposes_mwaa_sg_property(self):
        """VpcStack exposes a mwaa_sg property."""
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        stack = VpcStack(app, "TestVpcStack", env=cdk.Environment(
            account="123456789012", region="eu-west-1"
        ))
        assert stack.mwaa_sg is not None

    def test_explicit_subnet_ids_from_context(self):
        """VpcStack uses explicit subnet IDs when private_subnet_ids provided."""
        app = cdk.App(context={
            "vpc_id": "vpc-12345",
            "private_subnet_ids": "subnet-aaa,subnet-bbb",
        })
        stack = VpcStack(app, "TestVpcStack", env=cdk.Environment(
            account="123456789012", region="eu-west-1"
        ))
        # Should produce a SubnetSelection (not raise)
        assert stack.private_subnets is not None

    def test_redshift_ingress_scoped_to_mwaa_sg_on_5439(self):
        """With redshift_sg_id set, MWAA SG may reach Redshift on TCP 5439 only — no CIDR."""
        app = cdk.App(context={"vpc_id": "vpc-12345", "redshift_sg_id": "sg-0redshift"})
        stack = VpcStack(app, "TestVpcStack", env=cdk.Environment(
            account="123456789012", region="eu-west-1"
        ))
        template = assertions.Template.from_stack(stack)
        rules = template.find_resources("AWS::EC2::SecurityGroupIngress", {
            "Properties": {"GroupId": "sg-0redshift"},
        })
        assert len(rules) == 1
        props = next(iter(rules.values()))["Properties"]
        assert props["IpProtocol"] == "tcp"
        assert props["FromPort"] == 5439 and props["ToPort"] == 5439
        assert "SourceSecurityGroupId" in props
        assert "CidrIp" not in props

    def test_no_redshift_ingress_without_context(self):
        """No rule is added to any external SG when redshift_sg_id is not configured."""
        app = cdk.App(context={"vpc_id": "vpc-12345"})
        stack = VpcStack(app, "TestVpcStack", env=cdk.Environment(
            account="123456789012", region="eu-west-1"
        ))
        template = assertions.Template.from_stack(stack)
        rules = template.find_resources("AWS::EC2::SecurityGroupIngress", {
            "Properties": {"FromPort": 5439},
        })
        assert rules == {}
