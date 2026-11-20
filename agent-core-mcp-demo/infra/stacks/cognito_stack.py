"""CDK stack for Cognito User Pool (JWT authentication).

Defines a Cognito User Pool and client used by the AgentCore Gateway
custom JWT authorizer for authenticating agent and tool invocations.
"""

from aws_cdk import Stack, CfnOutput
from aws_cdk import aws_cognito as cognito
from constructs import Construct


class CognitoStack(Stack):
    """Cognito User Pool for AgentCore Gateway JWT authentication."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # User Pool with email sign-in and password policy
        self.user_pool = cognito.UserPool(
            self,
            "DAAnalyticsPool",
            user_pool_name="da-analytics-pool",
            sign_in_aliases=cognito.SignInAliases(email=True),
            self_sign_up_enabled=False,
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
        )

        # User Pool Client for the gateway authorizer
        self.user_pool_client = cognito.UserPoolClient(
            self,
            "DAAnalyticsPoolClient",
            user_pool=self.user_pool,
            generate_secret=False,
            auth_flows=cognito.AuthFlow(
                user_password=True,
                admin_user_password=True,
            ),
        )

        # Issuer URL for JWT validation
        issuer_url = (
            f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool.user_pool_id}"
        )

        # CloudFormation exports
        CfnOutput(
            self,
            "UserPoolId",
            value=self.user_pool.user_pool_id,
            export_name="AgentCoreMCPDemo-UserPoolId",
            description="Cognito User Pool ID for AgentCore gateway auth",
        )

        CfnOutput(
            self,
            "UserPoolArn",
            value=self.user_pool.user_pool_arn,
            export_name="AgentCoreMCPDemo-UserPoolArn",
            description="Cognito User Pool ARN for AgentCore gateway auth",
        )

        CfnOutput(
            self,
            "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            export_name="AgentCoreMCPDemo-UserPoolClientId",
            description="Cognito User Pool Client ID for gateway authorizer",
        )

        CfnOutput(
            self,
            "IssuerUrl",
            value=issuer_url,
            export_name="AgentCoreMCPDemo-IssuerUrl",
            description="Cognito issuer URL for JWT validation",
        )
