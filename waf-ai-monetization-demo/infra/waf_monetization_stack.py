"""CDK Stack — AWS WAF AI Traffic Monetization demo.

Provisions an end-to-end demo of AWS WAF AI traffic monetization for a
publisher (AnyCompany Media):

- Private S3 bucket serving sample "premium" articles across content zones
- CloudFront distribution (S3 origin via Origin Access Control)
- WAF Web ACL (scope CLOUDFRONT) with:
    * AWS Managed Rules Bot Control (COMMON) to classify AI bot traffic
    * Monetize rules that return HTTP 402 + x402 price manifest for AI bots,
      with differentiated pricing per content path via PriceMultiplier
    * Allow as the default action (browsers / search crawlers pass free)

Pricing model (per the AWS WAF monetization API):
    base price lives in MonetizationConfig (minimum $0.001 USDC);
    each Monetize rule multiplies it via PriceMultiplier (1-100).

    base = $0.001 USDC
      /medical/*     -> x10 -> $0.010   (premium content)
      /automotive/*  -> x5  -> $0.005
      /marketing/*   -> x3  -> $0.003

NOTE: AI traffic monetization Web ACLs are CLOUDFRONT-scoped and MUST be
created in us-east-1.
"""

import os

from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    Duration,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_wafv2 as wafv2,
)
from constructs import Construct

# Base price ($0.001 = the documented minimum). Per-path price is this value
# multiplied by each rule's PriceMultiplier below.
BASE_PRICE_USDC = "0.001"

# Bot Control label applied to requests classified as AI bots/agents.
# Verify against your account's Bot Control output — adjust if the category
# label differs for your inspection level.
AI_BOT_LABEL = "awswaf:managed:aws:bot-control:bot:category:ai"

# Per-path price multipliers (string, 1-100).
PATH_PRICING = [
    {"name": "Medical", "path": "/medical/", "multiplier": "10"},
    {"name": "Automotive", "path": "/automotive/", "multiplier": "5"},
    {"name": "Marketing", "path": "/marketing/", "multiplier": "3"},
]


class WafMonetizationStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Test wallet address (Base Sepolia). Provide all-lowercase to bypass
        # EIP-55 checksum validation. Override via WALLET_ADDRESS env var.
        wallet_address = os.environ.get(
            "WALLET_ADDRESS",
            "0x000000000000000000000000000000000000dead",
        ).lower()

        # ─── S3 Origin Bucket (private) ───────────────────────────────────
        content_bucket = s3.Bucket(
            self,
            "ContentBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ─── WAF Web ACL (CLOUDFRONT scope — must be us-east-1) ────────────
        web_acl = wafv2.CfnWebACL(
            self,
            "MonetizeWebAcl",
            name="waf-ai-monetization-demo",
            scope="CLOUDFRONT",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="wafAiMonetizationDemo",
                sampled_requests_enabled=True,
            ),
        )

        # Rule 0: Bot Control (COMMON) — override to Count so it only labels
        # traffic (incl. AI bot classification) without terminating, letting
        # the Monetize rules below act on the labels.
        bot_control_rule = {
            "Name": "AWS-BotControl",
            "Priority": 0,
            "OverrideAction": {"Count": {}},
            "Statement": {
                "ManagedRuleGroupStatement": {
                    "VendorName": "AWS",
                    "Name": "AWSManagedRulesBotControlRuleSet",
                    "ManagedRuleGroupConfigs": [
                        {"AWSManagedRulesBotControlRuleSet": {"InspectionLevel": "COMMON"}}
                    ],
                }
            },
            "VisibilityConfig": {
                "CloudWatchMetricsEnabled": True,
                "MetricName": "botControl",
                "SampledRequestsEnabled": True,
            },
        }

        # Rules 1..n: Monetize AI bot requests, priced per content path.
        # Each matches (AI bot label) AND (URI path prefix).
        monetize_rules = []
        for idx, cfg in enumerate(PATH_PRICING, start=1):
            monetize_rules.append(
                {
                    "Name": f"Monetize{cfg['name']}",
                    "Priority": idx,
                    "Action": {"Monetize": {"PriceMultiplier": cfg["multiplier"]}},
                    "Statement": {
                        "AndStatement": {
                            "Statements": [
                                {
                                    "LabelMatchStatement": {
                                        "Scope": "LABEL",
                                        "Key": AI_BOT_LABEL,
                                    }
                                },
                                {
                                    "ByteMatchStatement": {
                                        "SearchString": cfg["path"],
                                        "FieldToMatch": {"UriPath": {}},
                                        "PositionalConstraint": "STARTS_WITH",
                                        "TextTransformations": [
                                            {"Priority": 0, "Type": "NONE"}
                                        ],
                                    }
                                },
                            ]
                        }
                    },
                    "VisibilityConfig": {
                        "CloudWatchMetricsEnabled": True,
                        "MetricName": f"monetize{cfg['name']}",
                        "SampledRequestsEnabled": True,
                    },
                }
            )

        # Apply Rules + MonetizationConfig via raw property overrides so the
        # template is exact regardless of the installed aws-cdk-lib version's
        # typed support for the (new) monetization properties.
        web_acl.add_property_override("Rules", [bot_control_rule] + monetize_rules)
        web_acl.add_property_override(
            "MonetizationConfig",
            {
                "CurrencyMode": "TEST",
                "CryptoConfig": {
                    "PaymentNetworks": [
                        {
                            "Chain": "BASE_SEPOLIA",
                            "WalletAddress": wallet_address,
                            "Prices": [{"Amount": BASE_PRICE_USDC, "Currency": "USDC"}],
                        }
                    ]
                },
            },
        )

        # ─── CloudFront Distribution (S3 origin via OAC) ───────────────────
        distribution = cloudfront.Distribution(
            self,
            "Distribution",
            comment="WAF AI Monetization demo — AnyCompany premium content",
            default_root_object="index.html",
            web_acl_id=web_acl.attr_arn,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(content_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
            ),
        )

        # ─── Deploy sample content to the bucket ───────────────────────────
        content_path = os.path.join(os.path.dirname(__file__), "..", "content")
        s3deploy.BucketDeployment(
            self,
            "DeployContent",
            sources=[s3deploy.Source.asset(content_path)],
            destination_bucket=content_bucket,
            distribution=distribution,
            distribution_paths=["/*"],
        )

        # ─── Outputs ───────────────────────────────────────────────────────
        CfnOutput(
            self,
            "DistributionUrl",
            value=f"https://{distribution.distribution_domain_name}",
            description="CloudFront URL — pass to scripts/test-demo.sh",
        )
        CfnOutput(self, "WebAclArn", value=web_acl.attr_arn)
        CfnOutput(self, "ContentBucketName", value=content_bucket.bucket_name)
