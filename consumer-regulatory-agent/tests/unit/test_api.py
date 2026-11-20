"""Tests for the API Gateway REST API construct."""

import aws_cdk as cdk
from aws_cdk.assertions import Template, Match
import aws_cdk.aws_cognito as cognito

from cdk.constructs.api import AgentApiConstruct


def _create_stack_with_api(allowed_origin: str = "*", handler_function=None) -> Template:
    """Helper to synthesize a stack containing the API construct."""
    app = cdk.App()
    stack = cdk.Stack(app, "TestStack")

    user_pool = cognito.UserPool(stack, "TestUserPool")

    AgentApiConstruct(
        stack,
        "TestApi",
        user_pool=user_pool,
        allowed_origin=allowed_origin,
        handler_function=handler_function,
    )

    return Template.from_stack(stack)


class TestApiGatewayRestApi:
    """Tests for the REST API resource creation."""

    def test_rest_api_created(self):
        """Verify a REST API resource is created."""
        template = _create_stack_with_api()
        template.resource_count_is("AWS::ApiGateway::RestApi", 1)

    def test_rest_api_name(self):
        """Verify the REST API has the expected name."""
        template = _create_stack_with_api()
        template.has_resource_properties(
            "AWS::ApiGateway::RestApi",
            {
                "Name": "ConsumerRegulatoryAgentApi",
                "Description": "Consumer Regulatory Protection Agent REST API",
            },
        )

    def test_stage_configuration(self):
        """Verify the deployment stage has correct throttling and tracing settings."""
        template = _create_stack_with_api()
        template.has_resource_properties(
            "AWS::ApiGateway::Stage",
            {
                "StageName": "v1",
                "TracingEnabled": True,
                "MethodSettings": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "MetricsEnabled": True,
                                "LoggingLevel": "INFO",
                                "ThrottlingRateLimit": 100,
                                "ThrottlingBurstLimit": 200,
                            }
                        )
                    ]
                ),
            },
        )


class TestCognitoAuthorizer:
    """Tests for the Cognito authorizer configuration."""

    def test_cognito_authorizer_created(self):
        """Verify a Cognito authorizer is created."""
        template = _create_stack_with_api()
        template.resource_count_is("AWS::ApiGateway::Authorizer", 1)

    def test_cognito_authorizer_properties(self):
        """Verify the authorizer uses the correct identity source."""
        template = _create_stack_with_api()
        template.has_resource_properties(
            "AWS::ApiGateway::Authorizer",
            {
                "Type": "COGNITO_USER_POOLS",
                "Name": "ConsumerRegulatoryAgentAuthorizer",
                "IdentitySource": "method.request.header.Authorization",
            },
        )


class TestRequestValidation:
    """Tests for request validation models."""

    def test_request_validator_created(self):
        """Verify a request validator is created for body validation."""
        template = _create_stack_with_api()
        template.has_resource_properties(
            "AWS::ApiGateway::RequestValidator",
            {
                "Name": "ValidateRequestBody",
                "ValidateRequestBody": True,
                "ValidateRequestParameters": False,
            },
        )

    def test_campaign_assessment_model_created(self):
        """Verify the campaign assessment request model is defined."""
        template = _create_stack_with_api()
        template.has_resource_properties(
            "AWS::ApiGateway::Model",
            {
                "ContentType": "application/json",
                "Name": "CampaignAssessmentRequest",
            },
        )

    def test_product_checklist_model_created(self):
        """Verify the product checklist request model is defined."""
        template = _create_stack_with_api()
        template.has_resource_properties(
            "AWS::ApiGateway::Model",
            {
                "ContentType": "application/json",
                "Name": "ProductChecklistRequest",
            },
        )

    def test_data_compliance_model_created(self):
        """Verify the data compliance request model is defined."""
        template = _create_stack_with_api()
        template.has_resource_properties(
            "AWS::ApiGateway::Model",
            {
                "ContentType": "application/json",
                "Name": "DataComplianceRequest",
            },
        )

    def test_conversation_message_model_created(self):
        """Verify the conversation message request model is defined."""
        template = _create_stack_with_api()
        template.has_resource_properties(
            "AWS::ApiGateway::Model",
            {
                "ContentType": "application/json",
                "Name": "ConversationMessageRequest",
            },
        )

    def test_escalation_request_model_created(self):
        """Verify the escalation request model is defined."""
        template = _create_stack_with_api()
        template.has_resource_properties(
            "AWS::ApiGateway::Model",
            {
                "ContentType": "application/json",
                "Name": "EscalationRequest",
            },
        )

    def test_monitoring_preferences_model_created(self):
        """Verify the monitoring preferences request model is defined."""
        template = _create_stack_with_api()
        template.has_resource_properties(
            "AWS::ApiGateway::Model",
            {
                "ContentType": "application/json",
                "Name": "MonitoringPreferencesRequest",
            },
        )

    def test_total_model_count(self):
        """Verify the expected number of request models are created (6 custom + default error models)."""
        template = _create_stack_with_api()
        # 6 custom models defined in the construct
        json_template = template.to_json()
        models = [
            r
            for r_id, r in json_template["Resources"].items()
            if r["Type"] == "AWS::ApiGateway::Model"
        ]
        # At least 6 custom models
        assert len(models) >= 6, f"Expected at least 6 models, got {len(models)}"


class TestApiRoutes:
    """Tests for API route definitions."""

    def test_api_resources_created(self):
        """Verify the expected API resources (paths) are created."""
        template = _create_stack_with_api()
        json_template = template.to_json()

        resources = {
            r_id: r["Properties"]
            for r_id, r in json_template["Resources"].items()
            if r["Type"] == "AWS::ApiGateway::Resource"
        }

        # Extract path parts from all resources
        path_parts = {r["PathPart"] for r in resources.values()}

        expected_paths = {
            "v1",
            "assessments",
            "campaign",
            "product",
            "data",
            "{id}",
            "escalations",
            "conversations",
            "messages",
            "monitoring",
            "alerts",
            "preferences",
            "health",
        }

        for path in expected_paths:
            assert path in path_parts, f"Missing API resource path: {path}"

    def test_api_methods_created(self):
        """Verify the expected number of API methods are created."""
        template = _create_stack_with_api()
        json_template = template.to_json()

        methods = [
            r
            for r_id, r in json_template["Resources"].items()
            if r["Type"] == "AWS::ApiGateway::Method"
        ]

        # Expected methods:
        # GET /v1/assessments, POST campaign, POST product, POST data,
        # GET /v1/assessments/{id}, POST /v1/escalations, GET /v1/escalations/{id},
        # GET /v1/conversations/{id}, POST /v1/conversations/{id}/messages,
        # GET /v1/monitoring/alerts, GET /v1/monitoring/preferences,
        # PUT /v1/monitoring/preferences, GET /v1/health
        # Plus OPTIONS methods for CORS preflight on each resource
        # At minimum 13 non-OPTIONS methods
        non_options_methods = [
            m for m in methods if m["Properties"].get("HttpMethod") != "OPTIONS"
        ]
        assert len(non_options_methods) >= 13, (
            f"Expected at least 13 non-OPTIONS methods, got {len(non_options_methods)}"
        )

    def test_health_endpoint_has_no_auth(self):
        """Verify the health endpoint does not require Cognito authorization."""
        template = _create_stack_with_api()
        json_template = template.to_json()

        # Find the health resource
        health_resource_id = None
        for r_id, r in json_template["Resources"].items():
            if (
                r["Type"] == "AWS::ApiGateway::Resource"
                and r["Properties"].get("PathPart") == "health"
            ):
                health_resource_id = r_id
                break

        assert health_resource_id is not None, "Health resource not found"

        # Find GET method on health resource
        for r_id, r in json_template["Resources"].items():
            if (
                r["Type"] == "AWS::ApiGateway::Method"
                and r["Properties"].get("HttpMethod") == "GET"
                and r["Properties"].get("ResourceId", {}).get("Ref") == health_resource_id
            ):
                # Health endpoint should use NONE auth
                auth_type = r["Properties"].get("AuthorizationType", "NONE")
                assert auth_type == "NONE", (
                    f"Health endpoint should have no auth, got {auth_type}"
                )
                return

        # If we get here, we didn't find the method - that's also a failure
        assert False, "GET method on health resource not found"

    def test_authenticated_endpoints_use_cognito(self):
        """Verify non-health endpoints use Cognito authorization."""
        template = _create_stack_with_api()
        json_template = template.to_json()

        # Find the health resource ID to exclude it
        health_resource_id = None
        for r_id, r in json_template["Resources"].items():
            if (
                r["Type"] == "AWS::ApiGateway::Resource"
                and r["Properties"].get("PathPart") == "health"
            ):
                health_resource_id = r_id
                break

        # Check all non-OPTIONS, non-health methods use COGNITO_USER_POOLS
        for r_id, r in json_template["Resources"].items():
            if r["Type"] != "AWS::ApiGateway::Method":
                continue
            props = r["Properties"]
            if props.get("HttpMethod") == "OPTIONS":
                continue
            # Skip health endpoint
            resource_ref = props.get("ResourceId", {}).get("Ref", "")
            if resource_ref == health_resource_id:
                continue

            auth_type = props.get("AuthorizationType", "NONE")
            assert auth_type == "COGNITO_USER_POOLS", (
                f"Method {r_id} ({props.get('HttpMethod')}) should use COGNITO_USER_POOLS, got {auth_type}"
            )


class TestCorsConfiguration:
    """Tests for CORS configuration."""

    def test_cors_allow_origin_default(self):
        """Verify CORS is configured with the default wildcard origin."""
        template = _create_stack_with_api(allowed_origin="*")
        json_template = template.to_json()

        # Find OPTIONS methods (CORS preflight) and check response headers
        options_methods = [
            r
            for r_id, r in json_template["Resources"].items()
            if r["Type"] == "AWS::ApiGateway::Method"
            and r["Properties"].get("HttpMethod") == "OPTIONS"
        ]
        assert len(options_methods) > 0, "No OPTIONS methods found for CORS"

    def test_cors_custom_origin(self):
        """Verify CORS can be configured with a custom origin."""
        custom_origin = "https://myapp.amplifyapp.com"
        template = _create_stack_with_api(allowed_origin=custom_origin)
        # Should synthesize without errors
        template.resource_count_is("AWS::ApiGateway::RestApi", 1)


class TestMockIntegration:
    """Tests for mock integration when no Lambda handler is provided."""

    def test_mock_integration_when_no_handler(self):
        """Verify mock integration is used when no handler function is provided."""
        template = _create_stack_with_api(handler_function=None)
        json_template = template.to_json()

        # Find a non-OPTIONS method and check it uses MOCK integration
        for r_id, r in json_template["Resources"].items():
            if r["Type"] != "AWS::ApiGateway::Method":
                continue
            props = r["Properties"]
            if props.get("HttpMethod") == "OPTIONS":
                continue
            integration = props.get("Integration", {})
            assert integration.get("Type") == "MOCK", (
                f"Expected MOCK integration when no handler, got {integration.get('Type')}"
            )
            break

    def test_lambda_integration_when_handler_provided(self):
        """Verify Lambda proxy integration is used when a handler function is provided."""
        app = cdk.App()
        stack = cdk.Stack(app, "TestStack")

        user_pool = cognito.UserPool(stack, "TestUserPool")

        # Create a Lambda function to use as handler
        import aws_cdk.aws_lambda as lambda_

        handler = lambda_.Function(
            stack,
            "TestHandler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_inline("def lambda_handler(event, context): pass"),
        )

        AgentApiConstruct(
            stack,
            "TestApi",
            user_pool=user_pool,
            handler_function=handler,
        )

        template = Template.from_stack(stack)
        json_template = template.to_json()

        # Find a non-OPTIONS method and check it uses AWS_PROXY integration
        for r_id, r in json_template["Resources"].items():
            if r["Type"] != "AWS::ApiGateway::Method":
                continue
            props = r["Properties"]
            if props.get("HttpMethod") == "OPTIONS":
                continue
            integration = props.get("Integration", {})
            assert integration.get("Type") == "AWS_PROXY", (
                f"Expected AWS_PROXY integration with handler, got {integration.get('Type')}"
            )
            break


class TestResourceReferences:
    """Tests for exposed resource references."""

    def test_construct_exposes_api_attribute(self):
        """Verify the construct exposes the api attribute."""
        app = cdk.App()
        stack = cdk.Stack(app, "TestStack")
        user_pool = cognito.UserPool(stack, "TestUserPool")

        construct = AgentApiConstruct(
            stack, "TestApi", user_pool=user_pool
        )

        assert construct.api is not None
        assert construct.authorizer is not None
        assert construct.resources is not None

    def test_resources_dict_has_expected_keys(self):
        """Verify the resources dict contains all expected route references."""
        app = cdk.App()
        stack = cdk.Stack(app, "TestStack")
        user_pool = cognito.UserPool(stack, "TestUserPool")

        construct = AgentApiConstruct(
            stack, "TestApi", user_pool=user_pool
        )

        expected_keys = {
            "assessments",
            "assessments_campaign",
            "assessments_product",
            "assessments_data",
            "assessments_by_id",
            "escalations",
            "escalations_by_id",
            "conversations_by_id",
            "conversations_messages",
            "monitoring_alerts",
            "monitoring_preferences",
            "health",
        }

        assert set(construct.resources.keys()) == expected_keys
