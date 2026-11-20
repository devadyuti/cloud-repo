"""VPC Stack — looks up an existing VPC and creates the MWAA security group."""

from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class VpcStack(Stack):
    """Looks up an existing VPC by ID and exposes networking resources for MWAA."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- VPC Lookup ---
        vpc_id = self.node.try_get_context("vpc_id")
        if vpc_id:
            self._vpc = ec2.Vpc.from_lookup(self, "Vpc", vpc_id=vpc_id)
        else:
            self._vpc = ec2.Vpc.from_lookup(
                self, "Vpc", vpc_name="Analytics Workshop VPC"
            )

        # --- Subnet Selection ---
        private_subnet_ids = self.node.try_get_context("private_subnet_ids")

        if private_subnet_ids:
            # Explicit subnet IDs provided (comma-separated list in context)
            if isinstance(private_subnet_ids, str):
                private_subnet_ids = [
                    s.strip() for s in private_subnet_ids.split(",")
                ]
            self._private_subnets = ec2.SubnetSelection(
                subnets=[
                    ec2.Subnet.from_subnet_id(self, f"Subnet{i}", subnet_id)
                    for i, subnet_id in enumerate(private_subnet_ids)
                ]
            )
        else:
            # Auto-select private subnets with egress (NAT)
            self._private_subnets = ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )

        # --- Security Group ---
        self._mwaa_sg = ec2.SecurityGroup(
            self,
            "MwaaSg",
            vpc=self._vpc,
            security_group_name="mwaa-demo-sg",
            description="Security group for MWAA Serverless ENIs",
            allow_all_outbound=True,
        )

        # Self-referencing ingress — all traffic from the same SG
        self._mwaa_sg.add_ingress_rule(
            peer=self._mwaa_sg,
            connection=ec2.Port.all_traffic(),
            description="Allow all traffic from self (MWAA ENI communication)",
        )

        # --- Redshift access for dbt ---
        # dbt-redshift connects over the Postgres wire protocol (5439), not the Data API.
        # The existing analytics-cluster SG only trusts itself, so allow the MWAA SG in —
        # TCP 5439 only, scoped to this one source SG. Skipped if no SG ID is configured.
        redshift_sg_id = self.node.try_get_context("redshift_sg_id")
        if redshift_sg_id:
            redshift_sg = ec2.SecurityGroup.from_security_group_id(
                self, "RedshiftSg", redshift_sg_id, mutable=True
            )
            redshift_sg.add_ingress_rule(
                peer=self._mwaa_sg,
                connection=ec2.Port.tcp(5439),
                # EC2 rule descriptions allow only a limited charset (no '>')
                description="dbt on MWAA to Redshift analytics-cluster",
            )

    @property
    def vpc(self) -> ec2.IVpc:
        """The looked-up VPC."""
        return self._vpc

    @property
    def private_subnets(self) -> ec2.SubnetSelection:
        """Private subnet selection for MWAA ENI placement."""
        return self._private_subnets

    @property
    def mwaa_sg(self) -> ec2.ISecurityGroup:
        """Security group for MWAA resources."""
        return self._mwaa_sg
