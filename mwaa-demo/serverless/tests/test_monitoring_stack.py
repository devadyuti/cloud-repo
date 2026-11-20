"""Unit tests for MonitoringStack (serverless)."""

import json

import aws_cdk as cdk
from aws_cdk import assertions

from stacks.monitoring_stack import MonitoringStack

LAMBDA_FUNCTION_NAME = "mwaa-dag-trigger"
EXPECTED_LOG_GROUP = f"/aws/lambda/{LAMBDA_FUNCTION_NAME}"


class TestMonitoringStack:
    """Tests for the serverless Monitoring stack."""

    def _create_stack(self):
        """Helper to create a MonitoringStack for testing."""
        app = cdk.App()
        env = cdk.Environment(account="123456789012", region="eu-west-1")
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            lambda_function_name=LAMBDA_FUNCTION_NAME,
            env=env,
        )
        return stack

    @staticmethod
    def _parse_dashboard_body(template):
        """Resolve Fn::Join in dashboard body and return the parsed JSON."""
        resources = template.find_resources("AWS::CloudWatch::Dashboard")
        dashboard_resource = list(resources.values())[0]
        body_join = dashboard_resource["Properties"]["DashboardBody"]["Fn::Join"]
        parts = [
            p if isinstance(p, str) else "placeholder"
            for p in body_join[1]
        ]
        return json.loads("".join(parts))

    def test_dashboard_created_with_correct_name(self):
        """Dashboard is created with name mwaa-serverless-dashboard."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::CloudWatch::Dashboard", {
            "DashboardName": "mwaa-serverless-dashboard",
        })

    def test_dashboard_has_text_header(self):
        """Dashboard contains a text widget with the expected header."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        text_widgets = [
            w for w in body["widgets"]
            if w["type"] == "text"
        ]
        assert len(text_widgets) >= 1
        header_text = text_widgets[0]["properties"]["markdown"]
        assert "MWAA Serverless" in header_text

    def test_dashboard_has_three_log_query_widgets(self):
        """Dashboard contains exactly 3 LogQueryWidgets."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        log_widgets = [w for w in body["widgets"] if w["type"] == "log"]
        assert len(log_widgets) == 3

    def test_log_widgets_reference_lambda_log_group(self):
        """All LogQueryWidgets reference the Lambda function log group."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        log_widgets = [w for w in body["widgets"] if w["type"] == "log"]
        for widget in log_widgets:
            query = widget["properties"].get("query", "")
            # CDK renders log group names as SOURCE directives or in the query
            # The log group should appear somewhere in the widget properties
            props = widget["properties"]
            # LogQueryWidget can store log groups in different places depending on CDK version
            sources = []
            if "query" in props:
                sources.append(props["query"])
            # Flatten all string values to check for log group reference
            all_text = json.dumps(props)
            assert EXPECTED_LOG_GROUP in all_text, (
                f"Expected log group '{EXPECTED_LOG_GROUP}' not found in widget: {props.get('title')}"
            )

    def test_recent_invocations_widget_query(self):
        """'Recent Trigger Invocations' widget filters for workflow-related messages."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        log_widgets = [w for w in body["widgets"] if w["type"] == "log"]
        invocation_widgets = [
            w for w in log_widgets
            if "Invocations" in w["properties"].get("title", "")
            or "invocation" in w["properties"].get("title", "").lower()
        ]
        assert len(invocation_widgets) >= 1
        query = invocation_widgets[0]["properties"]["query"]
        assert "workflow" in query or "WorkflowArn" in query or "start_workflow_run" in query

    def test_errors_widget_query(self):
        """'Errors & Failures' widget filters for error-related messages."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        log_widgets = [w for w in body["widgets"] if w["type"] == "log"]
        error_widgets = [
            w for w in log_widgets
            if "error" in w["properties"].get("title", "").lower()
            or "failure" in w["properties"].get("title", "").lower()
        ]
        assert len(error_widgets) >= 1
        query = error_widgets[0]["properties"]["query"]
        assert "error" in query.lower() or "exception" in query.lower()

    def test_volume_widget_uses_report_filter(self):
        """'Invocation Volume' widget uses REPORT log type for stats."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        log_widgets = [w for w in body["widgets"] if w["type"] == "log"]
        volume_widgets = [
            w for w in log_widgets
            if "volume" in w["properties"].get("title", "").lower()
        ]
        assert len(volume_widgets) >= 1
        query = volume_widgets[0]["properties"]["query"]
        assert "REPORT" in query
        assert "stats" in query

    def test_no_metric_graph_widgets(self):
        """Dashboard no longer contains metric-based GraphWidgets."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        metric_widgets = [w for w in body["widgets"] if w["type"] == "metric"]
        assert len(metric_widgets) == 0
