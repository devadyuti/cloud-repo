"""DynamoDB single-table construct for the Consumer Regulatory Protection Agent."""

import aws_cdk as cdk
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_kms as kms
from constructs import Construct


class AgentDatabaseConstruct(Construct):
    """DynamoDB single-table design with GSI for user-scoped queries."""

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        # KMS customer-managed key for DynamoDB encryption
        self.encryption_key = kms.Key(
            self,
            "TableEncryptionKey",
            alias="consumer-regulatory-agent/dynamodb",
            description="KMS key for Consumer Regulatory Agent DynamoDB table",
            enable_key_rotation=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        # Single-table design: ConsumerRegulatoryAgent
        self.table = dynamodb.Table(
            self,
            "AgentTable",
            table_name="ConsumerRegulatoryAgent",
            partition_key=dynamodb.Attribute(
                name="PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.encryption_key,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
            ),
            time_to_live_attribute="ttl",
        )

        # GSI1: User-scoped queries (assessments, conversations, escalations by user)
        self.table.add_global_secondary_index(
            index_name="GSI1",
            partition_key=dynamodb.Attribute(
                name="GSI1PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="GSI1SK", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )
