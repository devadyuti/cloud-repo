"""Cognito User Pool construct with SAML 2.0 federation."""

import aws_cdk as cdk
import aws_cdk.aws_cognito as cognito
from constructs import Construct


class AgentAuthConstruct(Construct):
    """Cognito User Pool with SAML 2.0 SSO, custom attributes, and OAuth 2.0 app client."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        saml_metadata_url: str = "",
    ) -> None:
        super().__init__(scope, construct_id)

        # Cognito User Pool
        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name="ConsumerRegulatoryAgentPool",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
                temp_password_validity=cdk.Duration.days(7),
            ),
            mfa=cognito.Mfa.REQUIRED,
            mfa_second_factor=cognito.MfaSecondFactor(
                sms=True,
                otp=True,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=cdk.RemovalPolicy.RETAIN,
            custom_attributes={
                "organisation_id": cognito.StringAttribute(
                    mutable=True, max_len=256
                ),
                "permitted_jurisdictions": cognito.StringAttribute(
                    mutable=True, max_len=256
                ),
                "role": cognito.StringAttribute(
                    mutable=True, max_len=64
                ),
            },
        )

        # SAML 2.0 Identity Provider (parameterized metadata URL)
        if saml_metadata_url:
            self.saml_provider = cognito.UserPoolIdentityProviderSaml(
                self,
                "SamlProvider",
                user_pool=self.user_pool,
                name="EnterpriseSSOProvider",
                metadata=cognito.UserPoolIdentityProviderSamlMetadata.url(
                    saml_metadata_url
                ),
                attribute_mapping=cognito.AttributeMapping(
                    email=cognito.ProviderAttribute.other(
                        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
                    ),
                    custom={
                        "custom:organisation_id": cognito.ProviderAttribute.other(
                            "organisationId"
                        ),
                        "custom:permitted_jurisdictions": cognito.ProviderAttribute.other(
                            "permittedJurisdictions"
                        ),
                        "custom:role": cognito.ProviderAttribute.other("role"),
                    },
                ),
            )

        # App Client for Next.js frontend with OAuth 2.0 flows
        self.app_client = self.user_pool.add_client(
            "FrontendAppClient",
            user_pool_client_name="ConsumerRegulatoryAgentFrontend",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(
                user_srp=True,
                user_password=False,
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=False,
                ),
                scopes=[
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PROFILE,
                ],
                callback_urls=["http://localhost:3000/api/auth/callback"],
                logout_urls=["http://localhost:3000/"],
            ),
            access_token_validity=cdk.Duration.hours(1),
            id_token_validity=cdk.Duration.hours(1),
            refresh_token_validity=cdk.Duration.days(30),
            prevent_user_existence_errors=True,
        )

        # User Pool Domain for hosted UI
        self.user_pool_domain = self.user_pool.add_domain(
            "UserPoolDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix="consumer-regulatory-agent",
            ),
        )
