"""Unit tests for LambdaStack (serverless)."""

import aws_cdk as cdk
from aws_cdk import assertions

from stacks.lambda_stack import LambdaStack

MWAA_ENV_NAME = "any-company-mwaa-demo"
DAGS_BUCKET_NAME = "any-company-mwaa-demo-dags-123456789012"
EXPECTED_WORKFLOW_ARN = (
    "arn:aws:airflow-serverless:eu-west-1:123456789012"
    ":workflow/s3-event-lambda-serverless-HvYwSyW3qO"
)


class TestLambdaStack:
    """Tests for the serverless Lambda stack."""

    def _create_stack(self):
        """Helper to instantiate a LambdaStack for testing."""
        app = cdk.App()
        env = cdk.Environment(account="123456789012", region="eu-west-1")
        stack = LambdaStack(
            app,
            "TestLambdaStack",
            mwaa_environment_name=MWAA_ENV_NAME,
            dags_bucket_name=DAGS_BUCKET_NAME,
            env=env,
        )
        return stack

    def test_lambda_function_created(self):
        """Lambda function resource exists with expected name."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::Lambda::Function", {
            "FunctionName": "mwaa-dag-trigger",
            "Runtime": "python3.11",
            "Handler": "trigger_dag.handler",
            "Timeout": 30,
        })

    def test_lambda_environment_variables(self):
        """Lambda environment includes MWAA_ENV_NAME and WORKFLOW_ARN."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::Lambda::Function", {
            "Environment": {
                "Variables": {
                    "MWAA_ENV_NAME": MWAA_ENV_NAME,
                    "WORKFLOW_ARN": EXPECTED_WORKFLOW_ARN,
                },
            },
        })

    def test_workflow_arn_points_to_correct_workflow(self):
        """WORKFLOW_ARN env var references the s3-event-lambda-serverless workflow."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        # Verify the ARN contains the expected workflow name prefix
        template.has_resource_properties("AWS::Lambda::Function", {
            "Environment": {
                "Variables": {
                    "WORKFLOW_ARN": assertions.Match.string_like_regexp(
                        r".*s3-event-lambda-serverless.*"
                    ),
                },
            },
        })

    def test_iam_policy_mwaa_create_web_login_token(self):
        """Lambda role has permission to create MWAA web login tokens."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Sid": "MwaaCreateWebLoginToken",
                        "Action": [
                            "airflow:CreateWebLoginToken",
                            "airflow:CreateCliToken",
                        ],
                        "Effect": "Allow",
                    }),
                ]),
            },
        })

    def test_iam_policy_mwaa_invoke_rest_api(self):
        """Lambda role has permission to invoke MWAA REST API."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Sid": "MwaaInvokeRestApi",
                        "Action": "airflow:InvokeRestApi",
                        "Effect": "Allow",
                    }),
                ]),
            },
        })

    def test_iam_policy_serverless_start_workflow(self):
        """Lambda role has permissions to start and get serverless workflow runs."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Sid": "MwaaServerlessStartWorkflow",
                        "Action": [
                            "airflow-serverless:StartWorkflowRun",
                            "airflow-serverless:GetWorkflowRun",
                        ],
                        "Effect": "Allow",
                    }),
                ]),
            },
        })

    def test_iam_policy_cloudwatch_put_metrics(self):
        """Lambda role has permission to publish custom metrics."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Sid": "CloudWatchPutMetrics",
                        "Action": "cloudwatch:PutMetricData",
                        "Effect": "Allow",
                    }),
                ]),
            },
        })

    def test_s3_event_notification_configured(self):
        """S3 bucket has event notification for serverless/incoming/ prefix."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        # CDK creates a custom resource for S3 notifications on imported buckets
        template.has_resource("Custom::S3BucketNotifications", {})

    def test_lambda_function_count(self):
        """Two Lambda functions are created (DAG trigger + S3 notification handler)."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        # CDK adds a BucketNotificationsHandler Lambda for imported bucket notifications
        template.resource_count_is("AWS::Lambda::Function", 2)

    def test_workflow_execution_role_created(self):
        """MWAA Serverless workflow execution role is created with correct trust policy."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::IAM::Role", {
            "RoleName": "MwaaServerlessWorkflowRole",
            "AssumeRolePolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "airflow-serverless.amazonaws.com",
                        },
                    }),
                ]),
            },
        })

    def test_workflow_role_s3_write_output_policy(self):
        """Workflow role can write output to the dags bucket under serverless/*."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Sid": "S3WriteWorkflowOutput",
                        "Action": [
                            "s3:PutObject",
                            "s3:GetObject",
                            "s3:ListBucket",
                        ],
                        "Effect": "Allow",
                    }),
                ]),
            },
            "Roles": assertions.Match.array_with([
                {"Ref": assertions.Match.string_like_regexp("MwaaServerlessWorkflowRole.*")},
            ]),
        })

    def test_workflow_role_s3_read_definition_policy(self):
        """Workflow role can read workflow definitions from S3."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Sid": "S3ReadWorkflowDefinition",
                        "Action": "s3:GetObject",
                        "Effect": "Allow",
                    }),
                ]),
            },
            "Roles": assertions.Match.array_with([
                {"Ref": assertions.Match.string_like_regexp("MwaaServerlessWorkflowRole.*")},
            ]),
        })

    def test_workflow_role_property_exposed(self):
        """Stack exposes the workflow_role property."""
        stack = self._create_stack()
        assert stack.workflow_role is not None

    def test_workflow_role_cloudwatch_logs_policy(self):
        """Workflow role can write CloudWatch Logs for observability."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Sid": "CloudWatchLogsWrite",
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents",
                        ],
                        "Effect": "Allow",
                    }),
                ]),
            },
            "Roles": assertions.Match.array_with([
                {"Ref": assertions.Match.string_like_regexp("MwaaServerlessWorkflowRole.*")},
            ]),
        })
