"""S3 bucket construct for the regulatory corpus."""

import aws_cdk as cdk
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_kms as kms
import aws_cdk.aws_iam as iam
from constructs import Construct


class RegulatoryCorpusBucketConstruct(Construct):
    """S3 bucket for storing the regulatory corpus with KMS encryption and versioning."""

    def __init__(self, scope: Construct, construct_id: str) -> None:
        super().__init__(scope, construct_id)

        # KMS customer-managed key for S3 encryption
        self.encryption_key = kms.Key(
            self,
            "BucketEncryptionKey",
            alias="consumer-regulatory-agent/s3-corpus",
            description="KMS key for regulatory corpus S3 bucket",
            enable_key_rotation=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

        # Regulatory corpus bucket
        self.bucket = s3.Bucket(
            self,
            "CorpusBucket",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.encryption_key,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            auto_delete_objects=False,
            minimum_tls_version=1.2,
        )

        # Restrict bucket access to Lambda execution roles and Bedrock service
        self.bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowBedrockServiceAccess",
                effect=iam.Effect.ALLOW,
                principals=[
                    iam.ServicePrincipal("bedrock.amazonaws.com"),
                ],
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket",
                ],
                resources=[
                    self.bucket.bucket_arn,
                    f"{self.bucket.bucket_arn}/*",
                ],
            )
        )

    def grant_lambda_read(self, role: iam.IRole) -> None:
        """Grant read access to a Lambda execution role."""
        self.bucket.grant_read(role)
        self.encryption_key.grant_decrypt(role)
