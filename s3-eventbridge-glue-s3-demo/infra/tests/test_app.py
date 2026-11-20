"""Tests for CDK app entry point."""
import aws_cdk as cdk
from aws_cdk import assertions
import pytest
from unittest.mock import patch, MagicMock


def test_app_creates_pipeline_stack():
    """Verify the CDK app instantiates the PipelineStack with correct props."""
    # We mock PipelineStack since its module doesn't exist yet
    with patch.dict("sys.modules", {"stacks": MagicMock(), "stacks.pipeline_stack": MagicMock()}):
        import importlib
        import sys

        # Remove cached app module if present
        sys.modules.pop("app", None)

        # Mock the PipelineStack class
        mock_module = sys.modules["stacks.pipeline_stack"]
        mock_stack_class = MagicMock()
        mock_module.PipelineStack = mock_stack_class

        # Import and run app
        import app  # noqa: F401

        # Verify PipelineStack was called once
        mock_stack_class.assert_called_once()

        # Verify the stack ID and environment
        call_args = mock_stack_class.call_args
        assert call_args[0][1] == "S3EventBridgeGluePipelineStack"

        # Verify region is eu-west-1
        env = call_args[1]["env"]
        assert env.region == "eu-west-1"


def test_app_creates_cdk_app_instance():
    """Verify app.synth() is callable (CDK app is valid)."""
    with patch.dict("sys.modules", {"stacks": MagicMock(), "stacks.pipeline_stack": MagicMock()}):
        import sys

        sys.modules.pop("app", None)
        mock_module = sys.modules["stacks.pipeline_stack"]
        mock_module.PipelineStack = MagicMock()

        import app  # noqa: F401

        # If we got here without error, the CDK app was created and synth'd successfully
