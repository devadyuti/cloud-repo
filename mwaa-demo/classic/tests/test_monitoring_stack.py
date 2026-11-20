"""Unit tests for MonitoringStack."""

import aws_cdk as cdk
from aws_cdk import assertions

from stacks.monitoring_stack import MonitoringStack


class TestMonitoringStack:
    """Tests for the Monitoring stack."""

    def _create_stack(self):
        """Helper to create a MonitoringStack for testing."""
        app = cdk.App()
        env = cdk.Environment(account="123456789012", region="eu-west-1")
        stack = MonitoringStack(
            app,
            "TestMonitoringStack",
            mwaa_environment_name="any-company-mwaa-demo",
            env=env,
        )
        return stack

    def test_dashboard_created(self):
        """MonitoringStack creates a CloudWatch dashboard named mwaa-demo-dashboard."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)

        template.has_resource_properties("AWS::CloudWatch::Dashboard", {
            "DashboardName": "mwaa-demo-dashboard",
        })

    @staticmethod
    def _parse_dashboard_body(template):
        """Helper to resolve Fn::Join with Ref placeholders and parse dashboard body."""
        import json

        resources = template.find_resources("AWS::CloudWatch::Dashboard")
        dashboard_resource = list(resources.values())[0]
        body_join = dashboard_resource["Properties"]["DashboardBody"]["Fn::Join"]
        # Replace Ref objects with a placeholder string before joining
        parts = [
            p if isinstance(p, str) else "eu-west-1"
            for p in body_join[1]
        ]
        return json.loads("".join(parts))

    def test_dashboard_has_classic_mwaa_widgets(self):
        """Dashboard contains the 4 classic MWAA metric widgets."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        widgets = body["widgets"]
        mwaa_graph_widgets = [
            w for w in widgets
            if w["type"] == "metric" and w.get("properties", {}).get("metrics")
            and any(
                m[0] == "AWS/MWAA" for m in w["properties"].get("metrics", [])
                if isinstance(m, list) and len(m) > 0
            )
        ]
        assert len(mwaa_graph_widgets) == 4

    def test_classic_widgets_use_correct_metrics(self):
        """Classic MWAA widgets reference the AWS/MWAA namespace with correct metrics."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        widgets = body["widgets"]
        expected_metrics = ["QueuedTasks", "RunningTasks", "SchedulerHeartbeat", "TaskInstanceFailures"]

        mwaa_widgets = [
            w for w in widgets
            if w["type"] == "metric" and w.get("properties", {}).get("metrics")
            and any(
                m[0] == "AWS/MWAA" for m in w["properties"].get("metrics", [])
                if isinstance(m, list) and len(m) > 0
            )
        ]

        found_metrics = []
        for widget in mwaa_widgets:
            props = widget["properties"]
            for metric_entry in props["metrics"]:
                if isinstance(metric_entry, list) and metric_entry[0] == "AWS/MWAA":
                    found_metrics.append(metric_entry[1])
                    assert metric_entry[2] == "Environment"
                    assert metric_entry[3] == "any-company-mwaa-demo"

        for expected in expected_metrics:
            assert expected in found_metrics, f"Missing metric: {expected}"

    def test_dashboard_has_lambda_widgets(self):
        """Dashboard includes Lambda metrics for the serverless trigger function."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        widgets = body["widgets"]
        lambda_widgets = [
            w for w in widgets
            if w["type"] == "metric" and w.get("properties", {}).get("metrics")
            and any(
                m[0] == "AWS/Lambda" for m in w["properties"].get("metrics", [])
                if isinstance(m, list) and len(m) > 0
            )
        ]
        # Should have at least 2 Lambda widgets (invocations/duration, errors/throttles)
        assert len(lambda_widgets) >= 2

    def test_dashboard_has_custom_serverless_metrics(self):
        """Dashboard includes custom MWAADemo/Serverless namespace widgets."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        widgets = body["widgets"]
        custom_widgets = [
            w for w in widgets
            if w["type"] == "metric" and w.get("properties", {}).get("metrics")
            and any(
                m[0] == "MWAADemo/Serverless" for m in w["properties"].get("metrics", [])
                if isinstance(m, list) and len(m) > 0
            )
        ]
        assert len(custom_widgets) >= 2

    def test_dashboard_has_logs_insights_widget(self):
        """Dashboard includes a Log Query widget for serverless task logs."""
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        widgets = body["widgets"]
        log_widgets = [w for w in widgets if w["type"] == "log"]
        assert len(log_widgets) >= 1

    def test_logs_widget_references_specific_workflow_log_groups(self):
        """Log Query widget references the specific serverless workflow log groups.

        CDK LogQueryWidget renders the first log group as the widget's implicit default
        source, and additional log groups as SOURCE directives in the query string.
        """
        stack = self._create_stack()
        template = assertions.Template.from_stack(stack)
        body = self._parse_dashboard_body(template)

        widgets = body["widgets"]
        log_widgets = [w for w in widgets if w["type"] == "log"]
        assert len(log_widgets) >= 1

        log_widget = log_widgets[0]
        query_string = log_widget["properties"].get("query", "")

        # The 2nd and 3rd log groups appear as SOURCE directives in the query
        assert "SOURCE '/aws/mwaa-serverless/s3-etl-workflow-serverless-qLobqQ5Dpk/'" in query_string
        assert "SOURCE '/aws/mwaa-serverless/s3-event-lambda-serverless-O6akUBJIvC/'" in query_string
