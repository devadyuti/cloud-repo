"""Lambda compute construct for the Consumer Regulatory Protection Agent."""

import aws_cdk as cdk
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_kms as kms
import aws_cdk.aws_dynamodb as dynamodb
import aws_cdk.aws_s3 as s3
from constructs import Construct


class AgentComputeConstruct(Construct):
    """Lambda functions for orchestrator, async processor, and ingestion with least-privilege IAM."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        table: dynamodb.ITable,
        table_encryption_key: kms.IKey,
        corpus_bucket: s3.IBucket,
        bucket_encryption_key: kms.IKey,
        allowed_origin: str = "*",
    ) -> None:
        super().__init__(scope, construct_id)

        # Security group for Lambda functions - allows outbound HTTPS to VPC endpoints
        self.lambda_security_group = ec2.SecurityGroup(
            self,
            "LambdaSg",
            vpc=vpc,
            description="Security group for Lambda functions - outbound HTTPS to VPC endpoints",
            allow_all_outbound=False,
        )

        # Allow outbound HTTPS (port 443) for VPC endpoint communication
        self.lambda_security_group.add_egress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS to VPC endpoints",
        )

        # VPC subnet selection for Lambda functions
        vpc_subnets = ec2.SubnetSelection(
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
        )

        # Shared Lambda layer with common dependencies
        self.shared_layer = lambda_.LayerVersion(
            self,
            "SharedLayer",
            code=lambda_.Code.from_asset("lambdas/shared"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Shared layer with boto3, aws-xray-sdk, strands-agents dependencies",
            layer_version_name="consumer-regulatory-agent-shared",
        )

        # --- Orchestrator Lambda ---
        self.orchestrator_function = lambda_.Function(
            self,
            "OrchestratorFunction",
            function_name="consumer-regulatory-agent-orchestrator",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambdas/orchestrator"),
            memory_size=512,
            timeout=cdk.Duration.seconds(60),
            vpc=vpc,
            vpc_subnets=vpc_subnets,
            security_groups=[self.lambda_security_group],
            layers=[self.shared_layer],
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                "TABLE_NAME": table.table_name,
                "MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0",
                "KNOWLEDGE_BASE_ID": "placeholder-kb-id",
                "GUARDRAIL_ID": "placeholder-guardrail-id",
                "ALLOWED_ORIGIN": allowed_origin,
            },
        )

        # --- Async Processor Lambda ---
        self.async_processor_function = lambda_.Function(
            self,
            "AsyncProcessorFunction",
            function_name="consumer-regulatory-agent-async-processor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambdas/async_processor"),
            memory_size=256,
            timeout=cdk.Duration.seconds(300),
            vpc=vpc,
            vpc_subnets=vpc_subnets,
            security_groups=[self.lambda_security_group],
            layers=[self.shared_layer],
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                "TABLE_NAME": table.table_name,
                "MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0",
                "KNOWLEDGE_BASE_ID": "placeholder-kb-id",
            },
        )

        # --- Ingestion Lambda ---
        self.ingestion_function = lambda_.Function(
            self,
            "IngestionFunction",
            function_name="consumer-regulatory-agent-ingestion",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambdas/ingestion"),
            memory_size=256,
            timeout=cdk.Duration.seconds(300),
            vpc=vpc,
            vpc_subnets=vpc_subnets,
            security_groups=[self.lambda_security_group],
            layers=[self.shared_layer],
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                "TABLE_NAME": table.table_name,
                "KNOWLEDGE_BASE_ID": "placeholder-kb-id",
                "CORPUS_BUCKET_NAME": corpus_bucket.bucket_name,
            },
        )

        # --- IAM Permissions ---
        self._grant_orchestrator_permissions(
            table, table_encryption_key
        )
        self._grant_async_processor_permissions(
            table, table_encryption_key
        )
        self._grant_ingestion_permissions(
            table, table_encryption_key, corpus_bucket, bucket_encryption_key
        )

    def _grant_orchestrator_permissions(
        self,
        table: dynamodb.ITable,
        table_encryption_key: kms.IKey,
    ) -> None:
        """Grant least-privilege permissions to the orchestrator Lambda."""

        # DynamoDB read/write on table and GSI
        table.grant_read_write_data(self.orchestrator_function)

        # KMS decrypt/encrypt for DynamoDB encryption key
        table_encryption_key.grant_encrypt_decrypt(self.orchestrator_function)

        # Bedrock InvokeModel and InvokeModelWithResponseStream
        self.orchestrator_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="BedrockInvokeModel",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["arn:aws:bedrock:*::foundation-model/*"],
            )
        )

        # Bedrock Agent Retrieve (Knowledge Base)
        self.orchestrator_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="BedrockKBRetrieve",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:Retrieve",
                ],
                resources=["*"],  # KB ARN not known at synth time
            )
        )

        # Bedrock Guardrails
        self.orchestrator_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="BedrockGuardrails",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:ApplyGuardrail",
                ],
                resources=["*"],  # Guardrail ARN not known at synth time
            )
        )

        # CloudWatch PutMetricData
        self.orchestrator_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="CloudWatchMetrics",
                effect=iam.Effect.ALLOW,
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )

        # X-Ray tracing
        self.orchestrator_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="XRayTracing",
                effect=iam.Effect.ALLOW,
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                resources=["*"],
            )
        )

    def _grant_async_processor_permissions(
        self,
        table: dynamodb.ITable,
        table_encryption_key: kms.IKey,
    ) -> None:
        """Grant least-privilege permissions to the async processor Lambda."""

        # DynamoDB read/write
        table.grant_read_write_data(self.async_processor_function)

        # KMS decrypt/encrypt for DynamoDB encryption key
        table_encryption_key.grant_encrypt_decrypt(self.async_processor_function)

        # Bedrock InvokeModel
        self.async_processor_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="BedrockInvokeModel",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                resources=["arn:aws:bedrock:*::foundation-model/*"],
            )
        )

        # Bedrock Agent Retrieve (Knowledge Base)
        self.async_processor_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="BedrockKBRetrieve",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:Retrieve",
                ],
                resources=["*"],
            )
        )

        # CloudWatch PutMetricData
        self.async_processor_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="CloudWatchMetrics",
                effect=iam.Effect.ALLOW,
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )

        # X-Ray tracing
        self.async_processor_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="XRayTracing",
                effect=iam.Effect.ALLOW,
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                resources=["*"],
            )
        )

    def _grant_ingestion_permissions(
        self,
        table: dynamodb.ITable,
        table_encryption_key: kms.IKey,
        corpus_bucket: s3.IBucket,
        bucket_encryption_key: kms.IKey,
    ) -> None:
        """Grant least-privilege permissions to the ingestion Lambda."""

        # S3 read on corpus bucket
        corpus_bucket.grant_read(self.ingestion_function)

        # KMS decrypt for S3 bucket encryption key
        bucket_encryption_key.grant_decrypt(self.ingestion_function)

        # DynamoDB write (ingestion only writes metadata records)
        table.grant_write_data(self.ingestion_function)

        # KMS decrypt/encrypt for DynamoDB encryption key
        table_encryption_key.grant_encrypt_decrypt(self.ingestion_function)

        # Bedrock Agent StartIngestionJob
        self.ingestion_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="BedrockStartIngestion",
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:StartIngestionJob",
                    "bedrock:GetIngestionJob",
                    "bedrock:ListIngestionJobs",
                ],
                resources=["*"],
            )
        )

        # CloudWatch PutMetricData
        self.ingestion_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="CloudWatchMetrics",
                effect=iam.Effect.ALLOW,
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )

        # X-Ray tracing
        self.ingestion_function.add_to_role_policy(
            iam.PolicyStatement(
                sid="XRayTracing",
                effect=iam.Effect.ALLOW,
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                resources=["*"],
            )
        )
