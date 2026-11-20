"""CDK stack for VPC resources supporting Redshift connectivity.

Supports two modes:
- Existing VPC: accepts subnet IDs and security group IDs via constructor,
  passes them through as CloudFormation outputs without creating resources.
- New VPC: creates a VPC with 2 private subnets and a security group
  allowing inbound Redshift traffic on port 5439.
"""

from aws_cdk import Stack, CfnOutput
from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class VPCStack(Stack):
    """VPC networking for AgentCore Redshift MCP server runtime."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc_subnet_ids: list = None,
        vpc_security_group_ids: list = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        vpc_subnet_ids = vpc_subnet_ids or []
        vpc_security_group_ids = vpc_security_group_ids or []

        if vpc_subnet_ids:
            # Mode 1: Use existing VPC resources — no new infrastructure created
            self.subnet_ids = vpc_subnet_ids
            self.security_group_ids = vpc_security_group_ids
        else:
            # Mode 2: Create a new VPC with private subnets and Redshift SG
            vpc = ec2.Vpc(
                self,
                "AgentCoreVPC",
                vpc_name="agentcore-mcp-demo-vpc",
                max_azs=2,
                nat_gateways=1,
                subnet_configuration=[
                    ec2.SubnetConfiguration(
                        name="Private",
                        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                        cidr_mask=24,
                    ),
                    ec2.SubnetConfiguration(
                        name="Public",
                        subnet_type=ec2.SubnetType.PUBLIC,
                        cidr_mask=24,
                    ),
                ],
            )

            # Security group allowing Redshift port 5439
            redshift_sg = ec2.SecurityGroup(
                self,
                "RedshiftAccessSG",
                vpc=vpc,
                security_group_name="agentcore-redshift-access",
                description="Allow AgentCore runtime to connect to Redshift on port 5439",
                allow_all_outbound=True,
            )

            redshift_sg.add_ingress_rule(
                peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
                connection=ec2.Port.tcp(5439),
                description="Allow Redshift access from within VPC",
            )

            # Collect private subnet IDs for outputs
            self.subnet_ids = [
                subnet.subnet_id for subnet in vpc.private_subnets
            ]
            self.security_group_ids = [redshift_sg.security_group_id]

        # CloudFormation outputs
        CfnOutput(
            self,
            "SubnetIds",
            value=",".join(self.subnet_ids),
            export_name="AgentCoreMCPDemo-SubnetIds",
            description="Comma-separated subnet IDs for AgentCore Redshift runtime",
        )

        CfnOutput(
            self,
            "SecurityGroupIds",
            value=",".join(self.security_group_ids),
            export_name="AgentCoreMCPDemo-SecurityGroupIds",
            description="Comma-separated security group IDs for AgentCore Redshift runtime",
        )
