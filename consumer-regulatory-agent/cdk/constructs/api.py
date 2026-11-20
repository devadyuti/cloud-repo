"""API Gateway REST API construct with Cognito authorizer and CORS."""

import aws_cdk as cdk
import aws_cdk.aws_apigateway as apigw
import aws_cdk.aws_cognito as cognito
import aws_cdk.aws_lambda as lambda_
from constructs import Construct

from typing import Optional


class AgentApiConstruct(Construct):
    """REST API with Cognito authorizer, CORS, request validation, and all assessment routes."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        user_pool: cognito.IUserPool,
        allowed_origin: str = "*",
        handler_function: Optional[lambda_.IFunction] = None,
    ) -> None:
        super().__init__(scope, construct_id)

        # REST API
        self.api = apigw.RestApi(
            self,
            "ConsumerRegulatoryApi",
            rest_api_name="ConsumerRegulatoryAgentApi",
            description="Consumer Regulatory Protection Agent REST API",
            deploy_options=apigw.StageOptions(
                stage_name="v1",
                throttling_rate_limit=100,
                throttling_burst_limit=200,
                logging_level=apigw.MethodLoggingLevel.INFO,
                metrics_enabled=True,
                tracing_enabled=True,
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=[allowed_origin],
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    "Content-Type",
                    "Authorization",
                    "X-Amz-Date",
                    "X-Api-Key",
                    "X-Amz-Security-Token",
                ],
                allow_credentials=True,
                max_age=cdk.Duration.hours(1),
            ),
        )

        # Cognito authorizer
        self.authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "CognitoAuthorizer",
            cognito_user_pools=[user_pool],
            authorizer_name="ConsumerRegulatoryAgentAuthorizer",
            identity_source="method.request.header.Authorization",
        )

        # Request validator for body validation
        self.request_validator = apigw.RequestValidator(
            self,
            "RequestBodyValidator",
            rest_api=self.api,
            request_validator_name="ValidateRequestBody",
            validate_request_body=True,
            validate_request_parameters=False,
        )

        # --- Request validation models ---

        # Campaign assessment request model
        self.campaign_assessment_model = self.api.add_model(
            "CampaignAssessmentModel",
            content_type="application/json",
            model_name="CampaignAssessmentRequest",
            schema=apigw.JsonSchema(
                schema=apigw.JsonSchemaVersion.DRAFT4,
                title="CampaignAssessmentRequest",
                type=apigw.JsonSchemaType.OBJECT,
                required=["campaign_copy", "jurisdictions"],
                properties={
                    "campaign_copy": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        min_length=1,
                        description="Marketing campaign copy to assess",
                    ),
                    "jurisdictions": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.ARRAY,
                        items=apigw.JsonSchema(type=apigw.JsonSchemaType.STRING),
                        min_items=1,
                        description="Target jurisdictions for assessment",
                    ),
                    "target_demographics": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.ARRAY,
                        items=apigw.JsonSchema(type=apigw.JsonSchemaType.STRING),
                        description="Optional target demographics",
                    ),
                },
            ),
        )

        # Product checklist request model
        self.product_checklist_model = self.api.add_model(
            "ProductChecklistModel",
            content_type="application/json",
            model_name="ProductChecklistRequest",
            schema=apigw.JsonSchema(
                schema=apigw.JsonSchemaVersion.DRAFT4,
                title="ProductChecklistRequest",
                type=apigw.JsonSchemaType.OBJECT,
                required=["product_category", "jurisdictions"],
                properties={
                    "product_category": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        min_length=1,
                        description="Product category for checklist generation",
                    ),
                    "jurisdictions": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.ARRAY,
                        items=apigw.JsonSchema(type=apigw.JsonSchemaType.STRING),
                        min_items=1,
                        description="Target jurisdictions for checklist",
                    ),
                    "product_claims": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.ARRAY,
                        items=apigw.JsonSchema(type=apigw.JsonSchemaType.STRING),
                        description="Optional product claims to validate",
                    ),
                },
            ),
        )

        # Data compliance request model
        self.data_compliance_model = self.api.add_model(
            "DataComplianceModel",
            content_type="application/json",
            model_name="DataComplianceRequest",
            schema=apigw.JsonSchema(
                schema=apigw.JsonSchemaVersion.DRAFT4,
                title="DataComplianceRequest",
                type=apigw.JsonSchemaType.OBJECT,
                required=["data_collection_description", "jurisdictions"],
                properties={
                    "data_collection_description": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        min_length=1,
                        description="Description of data collection mechanism",
                    ),
                    "jurisdictions": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.ARRAY,
                        items=apigw.JsonSchema(type=apigw.JsonSchemaType.STRING),
                        min_items=1,
                        description="Target jurisdictions for data compliance",
                    ),
                    "consent_mechanisms": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.ARRAY,
                        items=apigw.JsonSchema(type=apigw.JsonSchemaType.STRING),
                        description="Optional consent mechanism descriptions",
                    ),
                },
            ),
        )

        # Conversation message request model
        self.conversation_message_model = self.api.add_model(
            "ConversationMessageModel",
            content_type="application/json",
            model_name="ConversationMessageRequest",
            schema=apigw.JsonSchema(
                schema=apigw.JsonSchemaVersion.DRAFT4,
                title="ConversationMessageRequest",
                type=apigw.JsonSchemaType.OBJECT,
                required=["message"],
                properties={
                    "message": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        min_length=1,
                        description="Follow-up message content",
                    ),
                },
            ),
        )

        # Escalation request model
        self.escalation_request_model = self.api.add_model(
            "EscalationRequestModel",
            content_type="application/json",
            model_name="EscalationRequest",
            schema=apigw.JsonSchema(
                schema=apigw.JsonSchemaVersion.DRAFT4,
                title="EscalationRequest",
                type=apigw.JsonSchemaType.OBJECT,
                required=["assessment_id"],
                properties={
                    "assessment_id": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        min_length=1,
                        description="Assessment ID to escalate",
                    ),
                    "notes": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        description="Optional notes for the legal team",
                    ),
                },
            ),
        )

        # Monitoring preferences request model
        self.monitoring_preferences_model = self.api.add_model(
            "MonitoringPreferencesModel",
            content_type="application/json",
            model_name="MonitoringPreferencesRequest",
            schema=apigw.JsonSchema(
                schema=apigw.JsonSchemaVersion.DRAFT4,
                title="MonitoringPreferencesRequest",
                type=apigw.JsonSchemaType.OBJECT,
                required=["sector", "jurisdictions"],
                properties={
                    "sector": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        min_length=1,
                        description="User's business sector",
                    ),
                    "jurisdictions": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.ARRAY,
                        items=apigw.JsonSchema(type=apigw.JsonSchemaType.STRING),
                        min_items=1,
                        description="Jurisdictions to monitor",
                    ),
                    "notification_channel": apigw.JsonSchema(
                        type=apigw.JsonSchemaType.STRING,
                        description="Preferred notification channel",
                    ),
                },
            ),
        )

        # Store handler function reference for integration
        self._handler_function = handler_function

        # --- Define API resources and methods ---
        self._define_routes()

    def _define_routes(self) -> None:
        """Define all API routes with Cognito authorization."""

        # Common method options with Cognito auth
        auth_method_options = apigw.MethodOptions(
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=self.authorizer,
        )

        # Use Lambda proxy integration if handler provided, otherwise mock
        if self._handler_function:
            integration = apigw.LambdaIntegration(
                self._handler_function,
                proxy=True,
            )
        else:
            integration = apigw.MockIntegration(
                integration_responses=[
                    apigw.IntegrationResponse(
                        status_code="200",
                        response_templates={"application/json": '{"message": "not yet implemented"}'},
                    )
                ],
                request_templates={"application/json": '{"statusCode": 200}'},
            )

        mock_response = apigw.MethodResponse(status_code="200")

        # Method response options - only needed for mock integration
        method_response_opts = {} if self._handler_function else {"method_responses": [mock_response]}

        # /v1/assessments
        v1 = self.api.root.add_resource("v1")
        assessments = v1.add_resource("assessments")

        # GET /v1/assessments - list assessments
        assessments.add_method(
            "GET",
            integration,
            **method_response_opts,
            **self._auth_options(),
        )

        # POST /v1/assessments/campaign
        campaign = assessments.add_resource("campaign")
        campaign.add_method(
            "POST",
            integration,
            **method_response_opts,
            request_models={"application/json": self.campaign_assessment_model},
            request_validator=self.request_validator,
            **self._auth_options(),
        )

        # POST /v1/assessments/product
        product = assessments.add_resource("product")
        product.add_method(
            "POST",
            integration,
            **method_response_opts,
            request_models={"application/json": self.product_checklist_model},
            request_validator=self.request_validator,
            **self._auth_options(),
        )

        # POST /v1/assessments/data
        data = assessments.add_resource("data")
        data.add_method(
            "POST",
            integration,
            **method_response_opts,
            request_models={"application/json": self.data_compliance_model},
            request_validator=self.request_validator,
            **self._auth_options(),
        )

        # GET /v1/assessments/{id}
        assessment_by_id = assessments.add_resource("{id}")
        assessment_by_id.add_method(
            "GET",
            integration,
            **method_response_opts,
            **self._auth_options(),
        )

        # /v1/escalations
        escalations = v1.add_resource("escalations")

        # POST /v1/escalations
        escalations.add_method(
            "POST",
            integration,
            **method_response_opts,
            request_models={"application/json": self.escalation_request_model},
            request_validator=self.request_validator,
            **self._auth_options(),
        )

        # GET /v1/escalations/{id}
        escalation_by_id = escalations.add_resource("{id}")
        escalation_by_id.add_method(
            "GET",
            integration,
            **method_response_opts,
            **self._auth_options(),
        )

        # /v1/conversations/{id}
        conversations = v1.add_resource("conversations")
        conversation_by_id = conversations.add_resource("{id}")

        # GET /v1/conversations/{id}
        conversation_by_id.add_method(
            "GET",
            integration,
            **method_response_opts,
            **self._auth_options(),
        )

        # POST /v1/conversations/{id}/messages
        messages = conversation_by_id.add_resource("messages")
        messages.add_method(
            "POST",
            integration,
            **method_response_opts,
            request_models={"application/json": self.conversation_message_model},
            request_validator=self.request_validator,
            **self._auth_options(),
        )

        # /v1/monitoring
        monitoring = v1.add_resource("monitoring")

        # GET /v1/monitoring/alerts
        alerts = monitoring.add_resource("alerts")
        alerts.add_method(
            "GET",
            integration,
            **method_response_opts,
            **self._auth_options(),
        )

        # GET/PUT /v1/monitoring/preferences
        preferences = monitoring.add_resource("preferences")
        preferences.add_method(
            "GET",
            integration,
            **method_response_opts,
            **self._auth_options(),
        )
        preferences.add_method(
            "PUT",
            integration,
            **method_response_opts,
            request_models={"application/json": self.monitoring_preferences_model},
            request_validator=self.request_validator,
            **self._auth_options(),
        )

        # GET /v1/health (no auth required)
        health = v1.add_resource("health")
        health.add_method(
            "GET",
            integration,
            **method_response_opts,
        )

        # Store resource references for Lambda integration in task 7.7
        self.resources = {
            "assessments": assessments,
            "assessments_campaign": campaign,
            "assessments_product": product,
            "assessments_data": data,
            "assessments_by_id": assessment_by_id,
            "escalations": escalations,
            "escalations_by_id": escalation_by_id,
            "conversations_by_id": conversation_by_id,
            "conversations_messages": messages,
            "monitoring_alerts": alerts,
            "monitoring_preferences": preferences,
            "health": health,
        }

    def _auth_options(self) -> dict:
        """Return common authorization method options."""
        return {
            "authorization_type": apigw.AuthorizationType.COGNITO,
            "authorizer": self.authorizer,
        }
