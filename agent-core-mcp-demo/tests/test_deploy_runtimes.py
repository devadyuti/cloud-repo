"""Tests for deploy.deploy_runtimes module.

Uses unittest.mock to stub the bedrock-agentcore-control boto3 client since
moto does not support this service.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from deploy.config import AgentCoreConfig
from deploy.deploy_runtimes import (
    deploy_redshift_runtime,
    deploy_s3_tables_runtime,
    find_existing_runtime,
    save_outputs,
    wait_for_runtime_active,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config():
    """Minimal AgentCoreConfig for testing."""
    return AgentCoreConfig(
        region="eu-west-1",
        account_id="123456789012",
        s3_tables_repo_name="s3-tables-mcp-server",
        redshift_repo_name="redshift-mcp-server",
        s3_tables_runtime_name="s3-tables-mcp-server",
        redshift_runtime_name="redshift-mcp-server",
        s3_tables_role_name="AgentCoreS3TablesRole",
        redshift_role_name="AgentCoreRedshiftRole",
        vpc_subnet_ids=[],
        vpc_security_group_ids=[],
    )


@pytest.fixture
def config_with_vpc(config):
    """Config with VPC subnet and security group IDs set."""
    config.vpc_subnet_ids = ["subnet-aaa", "subnet-bbb"]
    config.vpc_security_group_ids = ["sg-111", "sg-222"]
    return config


@pytest.fixture
def mock_client():
    """Mocked bedrock-agentcore-control client."""
    client = MagicMock()
    # Default: paginator returns empty list (no existing runtimes)
    paginator = MagicMock()
    paginator.paginate.return_value = [{"runtimeSummaries": []}]
    client.get_paginator.return_value = paginator
    return client


# ---------------------------------------------------------------------------
# find_existing_runtime
# ---------------------------------------------------------------------------


class TestFindExistingRuntime:
    def test_returns_none_when_no_runtimes_exist(self, mock_client):
        result = find_existing_runtime(mock_client, "my-runtime")
        assert result is None
        mock_client.get_paginator.assert_called_once_with("list_agent_runtimes")

    def test_returns_runtime_when_matched_by_name(self, mock_client):
        runtime_entry = {
            "name": "my-runtime",
            "agentRuntimeId": "rt-123",
            "agentRuntimeArn": "arn:aws:bedrock:eu-west-1:123:runtime/rt-123",
        }
        paginator = MagicMock()
        paginator.paginate.return_value = [{"runtimeSummaries": [runtime_entry]}]
        mock_client.get_paginator.return_value = paginator

        result = find_existing_runtime(mock_client, "my-runtime")
        assert result == runtime_entry

    def test_returns_runtime_when_matched_by_agentRuntimeName(self, mock_client):
        runtime_entry = {
            "agentRuntimeName": "my-runtime",
            "agentRuntimeId": "rt-456",
            "agentRuntimeArn": "arn:aws:bedrock:eu-west-1:123:runtime/rt-456",
        }
        paginator = MagicMock()
        paginator.paginate.return_value = [{"runtimeSummaries": [runtime_entry]}]
        mock_client.get_paginator.return_value = paginator

        result = find_existing_runtime(mock_client, "my-runtime")
        assert result == runtime_entry

    def test_returns_none_on_resource_not_found(self, mock_client):
        mock_client.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}},
            "ListAgentRuntimes",
        )
        result = find_existing_runtime(mock_client, "my-runtime")
        assert result is None

    def test_returns_none_on_validation_exception(self, mock_client):
        mock_client.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid"}},
            "ListAgentRuntimes",
        )
        result = find_existing_runtime(mock_client, "my-runtime")
        assert result is None

    def test_raises_on_unexpected_client_error(self, mock_client):
        mock_client.get_paginator.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Denied"}},
            "ListAgentRuntimes",
        )
        with pytest.raises(ClientError):
            find_existing_runtime(mock_client, "my-runtime")

    def test_fallback_to_direct_list_on_paginator_failure(self, mock_client):
        """If paginator raises a non-ClientError, falls back to list_agent_runtimes."""
        mock_client.get_paginator.side_effect = Exception("Paginator not available")
        mock_client.list_agent_runtimes.return_value = {
            "runtimeSummaries": [
                {
                    "agentRuntimeName": "my-runtime",
                    "agentRuntimeId": "rt-789",
                    "agentRuntimeArn": "arn:aws:bedrock:eu-west-1:123:runtime/rt-789",
                }
            ]
        }

        result = find_existing_runtime(mock_client, "my-runtime")
        assert result is not None
        assert result["agentRuntimeId"] == "rt-789"


# ---------------------------------------------------------------------------
# deploy_s3_tables_runtime
# ---------------------------------------------------------------------------


class TestDeployS3TablesRuntime:
    def test_returns_existing_runtime_arn_and_id(self, mock_client, config):
        """If runtime already exists, returns its ARN and ID without creating."""
        existing = {
            "agentRuntimeName": config.s3_tables_runtime_name,
            "agentRuntimeArn": "arn:aws:bedrock:eu-west-1:123:runtime/rt-existing",
            "agentRuntimeId": "rt-existing",
        }
        paginator = MagicMock()
        paginator.paginate.return_value = [{"runtimeSummaries": [existing]}]
        mock_client.get_paginator.return_value = paginator

        arn, rid = deploy_s3_tables_runtime(mock_client, config)

        assert arn == "arn:aws:bedrock:eu-west-1:123:runtime/rt-existing"
        assert rid == "rt-existing"
        mock_client.create_agent_runtime.assert_not_called()

    def test_creates_runtime_with_correct_params(self, mock_client, config):
        """Creates a new runtime with PUBLIC network mode."""
        mock_client.create_agent_runtime.return_value = {
            "agentRuntimeArn": "arn:aws:bedrock:eu-west-1:123:runtime/rt-new",
            "agentRuntimeId": "rt-new",
        }

        arn, rid = deploy_s3_tables_runtime(mock_client, config)

        assert arn == "arn:aws:bedrock:eu-west-1:123:runtime/rt-new"
        assert rid == "rt-new"

        call_kwargs = mock_client.create_agent_runtime.call_args[1]
        assert call_kwargs["agentRuntimeName"] == "s3-tables-mcp-server"
        assert call_kwargs["roleArn"] == "arn:aws:iam::123456789012:role/AgentCoreS3TablesRole"
        assert call_kwargs["agentRuntimeArtifact"] == {
            "containerConfiguration": {
                "containerUri": "123456789012.dkr.ecr.eu-west-1.amazonaws.com/s3-tables-mcp-server:latest",
            }
        }
        assert call_kwargs["environmentVariables"] == {
            "AWS_REGION": "eu-west-1",
            "FASTMCP_LOG_LEVEL": "INFO",
        }
        assert call_kwargs["protocolConfiguration"] == {"serverProtocol": "MCP"}
        assert call_kwargs["networkConfiguration"] == {"networkMode": "PUBLIC"}


# ---------------------------------------------------------------------------
# deploy_redshift_runtime
# ---------------------------------------------------------------------------


class TestDeployRedshiftRuntime:
    def test_returns_existing_runtime_arn_and_id(self, mock_client, config):
        existing = {
            "agentRuntimeName": config.redshift_runtime_name,
            "agentRuntimeArn": "arn:aws:bedrock:eu-west-1:123:runtime/rt-rs-exist",
            "agentRuntimeId": "rt-rs-exist",
        }
        paginator = MagicMock()
        paginator.paginate.return_value = [{"runtimeSummaries": [existing]}]
        mock_client.get_paginator.return_value = paginator

        arn, rid = deploy_redshift_runtime(mock_client, config)

        assert arn == "arn:aws:bedrock:eu-west-1:123:runtime/rt-rs-exist"
        assert rid == "rt-rs-exist"
        mock_client.create_agent_runtime.assert_not_called()

    def test_creates_runtime_public_mode_without_vpc(self, mock_client, config):
        """Without VPC IDs, falls back to PUBLIC network mode."""
        mock_client.create_agent_runtime.return_value = {
            "agentRuntimeArn": "arn:aws:bedrock:eu-west-1:123:runtime/rt-rs-new",
            "agentRuntimeId": "rt-rs-new",
        }

        arn, rid = deploy_redshift_runtime(mock_client, config)

        assert arn == "arn:aws:bedrock:eu-west-1:123:runtime/rt-rs-new"
        assert rid == "rt-rs-new"

        call_kwargs = mock_client.create_agent_runtime.call_args[1]
        assert call_kwargs["networkConfiguration"] == {"networkMode": "PUBLIC"}

    def test_creates_runtime_vpc_mode_with_vpc_config(self, mock_client, config_with_vpc):
        """With VPC IDs set, uses VPC network mode with subnets/security groups."""
        mock_client.create_agent_runtime.return_value = {
            "agentRuntimeArn": "arn:aws:bedrock:eu-west-1:123:runtime/rt-rs-vpc",
            "agentRuntimeId": "rt-rs-vpc",
        }

        arn, rid = deploy_redshift_runtime(mock_client, config_with_vpc)

        assert rid == "rt-rs-vpc"

        call_kwargs = mock_client.create_agent_runtime.call_args[1]
        assert call_kwargs["networkConfiguration"] == {
            "networkMode": "VPC",
            "networkModeConfig": {
                "subnets": ["subnet-aaa", "subnet-bbb"],
                "securityGroups": ["sg-111", "sg-222"],
            },
        }

    def test_redshift_runtime_params_structure(self, mock_client, config):
        """Verify full parameter structure for Redshift runtime creation."""
        mock_client.create_agent_runtime.return_value = {
            "agentRuntimeArn": "arn:aws:bedrock:eu-west-1:123:runtime/rt-rs",
            "agentRuntimeId": "rt-rs",
        }

        deploy_redshift_runtime(mock_client, config)

        call_kwargs = mock_client.create_agent_runtime.call_args[1]
        assert call_kwargs["agentRuntimeName"] == "redshift-mcp-server"
        assert call_kwargs["roleArn"] == "arn:aws:iam::123456789012:role/AgentCoreRedshiftRole"
        assert call_kwargs["agentRuntimeArtifact"] == {
            "containerConfiguration": {
                "containerUri": "123456789012.dkr.ecr.eu-west-1.amazonaws.com/redshift-mcp-server:latest",
            }
        }
        assert call_kwargs["protocolConfiguration"] == {"serverProtocol": "MCP"}


# ---------------------------------------------------------------------------
# wait_for_runtime_active
# ---------------------------------------------------------------------------


class TestWaitForRuntimeActive:
    def test_returns_active_immediately(self, mock_client):
        mock_client.get_agent_runtime.return_value = {"status": "ACTIVE"}

        status = wait_for_runtime_active(mock_client, "rt-123", "my-runtime")

        assert status == "ACTIVE"
        mock_client.get_agent_runtime.assert_called_once_with(agentRuntimeId="rt-123")

    def test_polls_until_active(self, mock_client):
        mock_client.get_agent_runtime.side_effect = [
            {"status": "CREATING"},
            {"status": "CREATING"},
            {"status": "ACTIVE"},
        ]

        with patch("deploy.deploy_runtimes.time.sleep"):
            status = wait_for_runtime_active(mock_client, "rt-123", "my-runtime")

        assert status == "ACTIVE"
        assert mock_client.get_agent_runtime.call_count == 3

    def test_raises_runtime_error_on_failed(self, mock_client):
        mock_client.get_agent_runtime.return_value = {
            "status": "FAILED",
            "statusReason": "Image pull failed",
        }

        with pytest.raises(RuntimeError, match="FAILED.*Image pull failed"):
            wait_for_runtime_active(mock_client, "rt-123", "my-runtime")

    def test_raises_timeout_error(self, mock_client):
        mock_client.get_agent_runtime.return_value = {"status": "CREATING"}

        with patch("deploy.deploy_runtimes.time.sleep"):
            with patch("deploy.deploy_runtimes.MAX_POLL_ATTEMPTS", 3):
                with pytest.raises(TimeoutError, match="did not reach ACTIVE"):
                    wait_for_runtime_active(mock_client, "rt-123", "my-runtime")


# ---------------------------------------------------------------------------
# save_outputs
# ---------------------------------------------------------------------------


class TestSaveOutputs:
    def test_writes_json_with_arns_and_ids(self, tmp_path):
        outputs_file = tmp_path / "runtimes.json"

        with patch("deploy.deploy_runtimes.OUTPUTS_DIR", tmp_path):
            with patch("deploy.deploy_runtimes.OUTPUTS_FILE", outputs_file):
                save_outputs(
                    s3_tables_arn="arn:s3tables",
                    s3_tables_id="rt-s3t",
                    redshift_arn="arn:redshift",
                    redshift_id="rt-rs",
                )

        data = json.loads(outputs_file.read_text())
        assert data == {
            "s3_tables_runtime_arn": "arn:s3tables",
            "s3_tables_runtime_id": "rt-s3t",
            "redshift_runtime_arn": "arn:redshift",
            "redshift_runtime_id": "rt-rs",
        }

    def test_creates_output_directory(self, tmp_path):
        nested_dir = tmp_path / "nested" / "outputs"
        outputs_file = nested_dir / "runtimes.json"

        with patch("deploy.deploy_runtimes.OUTPUTS_DIR", nested_dir):
            with patch("deploy.deploy_runtimes.OUTPUTS_FILE", outputs_file):
                save_outputs("arn1", "id1", "arn2", "id2")

        assert nested_dir.exists()
        assert outputs_file.exists()
