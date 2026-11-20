"""VPC construct with private subnets and VPC endpoints for the Agent."""

import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
from constructs import Construct


class AgentVpcConstruct(Construct):
    """VPC with private subnets and VPC endpoints for Bedrock, DynamoDB, S3, and CloudWatch."""

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        # VPC with 2 AZs and private subnets only (isolated - no NAT gateway)
        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                )
            ],
        )

        # Security group for VPC endpoint access
        self.endpoint_security_group = ec2.SecurityGroup(
            self,
            "VpcEndpointSg",
            vpc=self.vpc,
            description="Security group for VPC endpoints",
            allow_all_outbound=False,
        )

        # Allow HTTPS inbound from VPC CIDR for endpoint access
        self.endpoint_security_group.add_ingress_rule(
            peer=ec2.Peer.ipv4(self.vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS from VPC CIDR",
        )

        # Interface VPC Endpoints (private DNS enabled)
        self.bedrock_runtime_endpoint = self.vpc.add_interface_endpoint(
            "BedrockRuntimeEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME,
            private_dns_enabled=True,
            security_groups=[self.endpoint_security_group],
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
        )

        self.bedrock_agent_runtime_endpoint = self.vpc.add_interface_endpoint(
            "BedrockAgentRuntimeEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_AGENT_RUNTIME,
            private_dns_enabled=True,
            security_groups=[self.endpoint_security_group],
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
        )

        self.logs_endpoint = self.vpc.add_interface_endpoint(
            "CloudWatchLogsEndpoint",
            service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,
            private_dns_enabled=True,
            security_groups=[self.endpoint_security_group],
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
        )

        # Gateway VPC Endpoints
        self.dynamodb_endpoint = self.vpc.add_gateway_endpoint(
            "DynamoDbEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
            subnets=[
                ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                )
            ],
        )

        self.s3_endpoint = self.vpc.add_gateway_endpoint(
            "S3Endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
            subnets=[
                ec2.SubnetSelection(
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                )
            ],
        )
