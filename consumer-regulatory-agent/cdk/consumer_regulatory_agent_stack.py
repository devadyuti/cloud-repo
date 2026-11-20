"""Main CDK stack for the Consumer Regulatory Protection Agent."""

import aws_cdk as cdk
from constructs import Construct

from cdk.constructs.vpc import AgentVpcConstruct
from cdk.constructs.database import AgentDatabaseConstruct
from cdk.constructs.storage import RegulatoryCorpusBucketConstruct
from cdk.constructs.auth import AgentAuthConstruct
from cdk.constructs.api import AgentApiConstruct
from cdk.constructs.compute import AgentComputeConstruct


class ConsumerRegulatoryAgentStack(cdk.Stack):
    """Root stack defining all infrastructure for the Consumer Regulatory Protection Agent."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC with private subnets and VPC endpoints
        self.vpc = AgentVpcConstruct(self, "AgentVpc")

        # DynamoDB single-table design
        self.database = AgentDatabaseConstruct(self, "AgentDatabase")

        # S3 regulatory corpus bucket
        self.corpus_bucket = RegulatoryCorpusBucketConstruct(self, "RegulatoryCorpus")

        # Cognito authentication
        self.auth = AgentAuthConstruct(
            self,
            "AgentAuth",
            saml_metadata_url=self.node.try_get_context("saml_metadata_url") or "",
        )

        # Lambda compute (orchestrator, async processor, ingestion)
        allowed_origin = self.node.try_get_context("allowed_origin") or "https://main.d1234567890.amplifyapp.com"

        self.compute = AgentComputeConstruct(
            self,
            "AgentCompute",
            vpc=self.vpc.vpc,
            table=self.database.table,
            table_encryption_key=self.database.encryption_key,
            corpus_bucket=self.corpus_bucket.bucket,
            bucket_encryption_key=self.corpus_bucket.encryption_key,
            allowed_origin=allowed_origin,
        )

        # API Gateway REST API with Cognito authorizer and Lambda integration
        self.api = AgentApiConstruct(
            self,
            "AgentApi",
            user_pool=self.auth.user_pool,
            allowed_origin=allowed_origin,
            handler_function=self.compute.orchestrator_function,
        )

        # Stack outputs
        cdk.CfnOutput(
            self,
            "TableName",
            value=self.database.table.table_name,
            description="DynamoDB table name",
        )
        cdk.CfnOutput(
            self,
            "CorpusBucketName",
            value=self.corpus_bucket.bucket.bucket_name,
            description="S3 regulatory corpus bucket name",
        )
        cdk.CfnOutput(
            self,
            "UserPoolId",
            value=self.auth.user_pool.user_pool_id,
            description="Cognito User Pool ID",
        )
        cdk.CfnOutput(
            self,
            "UserPoolClientId",
            value=self.auth.app_client.user_pool_client_id,
            description="Cognito App Client ID",
        )
        cdk.CfnOutput(
            self,
            "ApiEndpoint",
            value=self.api.api.url,
            description="API Gateway endpoint URL",
        )
        cdk.CfnOutput(
            self,
            "OrchestratorFunctionArn",
            value=self.compute.orchestrator_function.function_arn,
            description="Orchestrator Lambda function ARN",
        )
        cdk.CfnOutput(
            self,
            "AsyncProcessorFunctionArn",
            value=self.compute.async_processor_function.function_arn,
            description="Async processor Lambda function ARN",
        )
        cdk.CfnOutput(
            self,
            "IngestionFunctionArn",
            value=self.compute.ingestion_function.function_arn,
            description="Ingestion Lambda function ARN",
        )
