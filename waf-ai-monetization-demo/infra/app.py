#!/usr/bin/env python3
"""CDK app entry point for the WAF AI Traffic Monetization demo.

The Web ACL is CLOUDFRONT-scoped, so the stack MUST deploy to us-east-1.
"""

import aws_cdk as cdk

from waf_monetization_stack import WafMonetizationStack

app = cdk.App()

WafMonetizationStack(
    app,
    "WafAiMonetizationDemoStack",
    env=cdk.Environment(region="us-east-1"),
    description="AWS WAF AI traffic monetization demo — CloudFront + S3 + WAF Monetize (Base Sepolia TEST mode)",
)

app.synth()
