"""Tests for deploy.deploy_agent module.

Uses unittest.mock to stub the bedrock-agentcore-control boto3 client since
moto does not support this service.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from deploy.config import AgentCoreConfig
from deploy.deploy_agent import (
    get_client,
    load_gateway_config,
    save_outputs,
    verify_gateway_status,
    verify_gateway_targets,
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
        agent_name="da-analytics-agent",
        agent_model="anthropic.claude-sonnet-4-20250514",
    )


@pytest.fixture
def gateway_config():
    """Sample gateway configuration dict as saved by deploy_gateway.py."""
    return {
        "gateway_id": "gw-abc123",
        "gateway_url": "https://gateway.example.com/mcp",
        "s3_tables_target_id": "tgt-s3tables-001",
        "redshift_target_id": "tgt-redshift-002",
    }


@pytest.fixture
def mock_client():
    """Mocked bedrock-agentcore-control client."""
    client = MagicMock()
    return client


# ---------------------------------------------------------------------------
# get_client
# ---------------------------------------------------------------------------


class TestGetClient:
    @patch("deploy.deploy_agent.boto3.client")
    def test_creates_correct_client(self, mock_boto3_client, config):
        get_client(config)
        mock_boto3_client.assert_called_once_with(
            "bedrock-agentcore-control", region_name="eu-west-1"
        )


# ---------------------------------------------------------------------------
# load_gateway_config
# ---------------------------------------------------------------------------


class TestLoadGatewayConfig:
    def test_loads_valid_gateway_config(self, tmp_path, gateway_config):
        gateway_file = tmp_path / "gateway.json"
        gateway_file.write_text(json.dumps(gateway_config))

        with patch("deploy.deploy_agent.GATEWAY_FILE", gateway_file):
            result = load_gateway_config()

        assert result == gateway_config

    def test_raises_file_not_found_when_missing(self, tmp_path):
        gateway_file = tmp_path / "gateway.json"

        with patch("deploy.deploy_agent.GATEWAY_FILE", gateway_file):
            with pytest.raises(FileNotFoundError, match="Gateway outputs not found"):
                load_gateway_config()

    def test_raises_key_error_when_gateway_id_missing(self, tmp_path):
        gateway_file = tmp_path / "gateway.json"
        gateway_file.write_text(json.dumps({"gateway_url": "https://example.com"}))

        with patch("deploy.deploy_agent.GATEWAY_FILE", gateway_file):
            with pytest.raises(KeyError, match="Missing key 'gateway_id'"):
                load_gateway_config()

    def test_raises_key_error_when_gateway_url_missing(self, tmp_path):
        gateway_file = tmp_path / "gateway.json"
        gateway_file.write_text(json.dumps({"gateway_id": "gw-123"}))

        with patch("deploy.deploy_agent.GATEWAY_FILE", gateway_file):
            with pytest.raises(KeyError, match="Missing key 'gateway_url'"):
                load_gateway_config()

    def test_raises_key_error_when_target_ids_missing(self, tmp_path):
        gateway_file = tmp_path / "gateway.json"
        gateway_file.write_text(json.dumps({
            "gateway_id": "gw-123",
            "gateway_url": "https://example.com",
        }))

        with patch("deploy.deploy_agent.GATEWAY_FILE", gateway_file):
            with pytest.raises(KeyError, match="Missing key 's3_tables_target_id'"):
                load_gateway_config()


# ---------------------------------------------------------------------------
# verify_gateway_status
# ---------------------------------------------------------------------------


class TestVerifyGatewayStatus:
    def test_returns_response_when_ready(self, mock_client):
        mock_client.get_gateway.return_value = {
            "gatewayId": "gw-abc123",
            "status": "READY",
        }

        result = verify_gateway_status(mock_client, "gw-abc123")

        assert result["status"] == "READY"
        mock_client.get_gateway.assert_called_once_with(gatewayIdentifier="gw-abc123")

    def test_returns_response_when_active(self, mock_client):
        mock_client.get_gateway.return_value = {
            "gatewayId": "gw-abc123",
            "status": "ACTIVE",
        }

        result = verify_gateway_status(mock_client, "gw-abc123")

        assert result["status"] == "ACTIVE"

    def test_returns_response_when_updating(self, mock_client):
        mock_client.get_gateway.return_value = {
            "gatewayId": "gw-abc123",
            "status": "UPDATING",
        }

        result = verify_gateway_status(mock_client, "gw-abc123")

        assert result["status"] == "UPDATING"

    def test_raises_runtime_error_when_not_found(self, mock_client):
        mock_client.get_gateway.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}},
            "GetGateway",
        )

        with pytest.raises(RuntimeError, match="not found"):
            verify_gateway_status(mock_client, "gw-missing")

    def test_raises_runtime_error_on_invalid_state(self, mock_client):
        mock_client.get_gateway.return_value = {
            "gatewayId": "gw-abc123",
            "status": "FAILED",
        }

        with pytest.raises(RuntimeError, match="FAILED.*state"):
            verify_gateway_status(mock_client, "gw-abc123")

    def test_raises_runtime_error_on_creating_state(self, mock_client):
        mock_client.get_gateway.return_value = {
            "gatewayId": "gw-abc123",
            "status": "CREATING",
        }

        with pytest.raises(RuntimeError, match="CREATING.*state"):
            verify_gateway_status(mock_client, "gw-abc123")

    def test_reraises_unexpected_client_error(self, mock_client):
        mock_client.get_gateway.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Denied"}},
            "GetGateway",
        )

        with pytest.raises(ClientError):
            verify_gateway_status(mock_client, "gw-abc123")


# ---------------------------------------------------------------------------
# verify_gateway_targets
# ---------------------------------------------------------------------------


class TestVerifyGatewayTargets:
    def test_returns_targets_when_all_found(self, mock_client):
        targets = [
            {"targetId": "tgt-s3tables-001", "name": "s3-tables", "status": "ACTIVE"},
            {"targetId": "tgt-redshift-002", "name": "redshift", "status": "ACTIVE"},
        ]
        paginator = MagicMock()
        paginator.paginate.return_value = [{"items": targets}]
        mock_client.get_paginator.return_value = paginator

        result = verify_gateway_targets(
            mock_client, "gw-abc123", ["tgt-s3tables-001", "tgt-redshift-002"]
        )

        assert len(result) == 2
        mock_client.get_paginator.assert_called_once_with("list_gateway_targets")

    def test_raises_runtime_error_when_target_missing(self, mock_client):
        targets = [
            {"targetId": "tgt-s3tables-001", "name": "s3-tables", "status": "ACTIVE"},
        ]
        paginator = MagicMock()
        paginator.paginate.return_value = [{"items": targets}]
        mock_client.get_paginator.return_value = paginator

        with pytest.raises(RuntimeError, match="Missing gateway targets.*tgt-redshift-002"):
            verify_gateway_targets(
                mock_client, "gw-abc123", ["tgt-s3tables-001", "tgt-redshift-002"]
            )

    def test_raises_runtime_error_when_gateway_not_found(self, mock_client):
        paginator = MagicMock()
        paginator.paginate.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}},
            "ListGatewayTargets",
        )
        mock_client.get_paginator.return_value = paginator

        with pytest.raises(RuntimeError, match="not found when listing targets"):
            verify_gateway_targets(mock_client, "gw-missing", ["tgt-1"])

    def test_reraises_unexpected_client_error(self, mock_client):
        paginator = MagicMock()
        paginator.paginate.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Denied"}},
            "ListGatewayTargets",
        )
        mock_client.get_paginator.return_value = paginator

        with pytest.raises(ClientError):
            verify_gateway_targets(mock_client, "gw-abc123", ["tgt-1"])

    def test_fallback_to_direct_list_on_paginator_failure(self, mock_client):
        """If paginator raises a non-ClientError, falls back to list_gateway_targets."""
        paginator = MagicMock()
        paginator.paginate.side_effect = Exception("Paginator not available")
        mock_client.get_paginator.return_value = paginator

        mock_client.list_gateway_targets.return_value = {
            "items": [
                {"targetId": "tgt-001", "name": "s3-tables", "status": "ACTIVE"},
            ]
        }

        result = verify_gateway_targets(mock_client, "gw-abc123", ["tgt-001"])

        assert len(result) == 1
        mock_client.list_gateway_targets.assert_called_once_with(
            gatewayIdentifier="gw-abc123"
        )

    def test_raises_runtime_error_when_fallback_also_fails(self, mock_client):
        paginator = MagicMock()
        paginator.paginate.side_effect = Exception("Paginator not available")
        mock_client.get_paginator.return_value = paginator

        mock_client.list_gateway_targets.side_effect = Exception("Service unavailable")

        with pytest.raises(RuntimeError, match="Failed to list gateway targets"):
            verify_gateway_targets(mock_client, "gw-abc123", ["tgt-001"])

    def test_handles_multiple_pages(self, mock_client):
        page1 = {"items": [{"targetId": "tgt-001", "name": "s3-tables", "status": "ACTIVE"}]}
        page2 = {"items": [{"targetId": "tgt-002", "name": "redshift", "status": "ACTIVE"}]}
        paginator = MagicMock()
        paginator.paginate.return_value = [page1, page2]
        mock_client.get_paginator.return_value = paginator

        result = verify_gateway_targets(
            mock_client, "gw-abc123", ["tgt-001", "tgt-002"]
        )

        assert len(result) == 2


# ---------------------------------------------------------------------------
# save_outputs
# ---------------------------------------------------------------------------


class TestSaveOutputs:
    def test_writes_json_with_agent_config(self, tmp_path, config, gateway_config):
        agent_file = tmp_path / "agent.json"

        with patch("deploy.deploy_agent.OUTPUTS_DIR", tmp_path):
            with patch("deploy.deploy_agent.AGENT_FILE", agent_file):
                save_outputs(config, gateway_config)

        data = json.loads(agent_file.read_text())
        assert data == {
            "agent_type": "strands-local",
            "gateway_id": "gw-abc123",
            "gateway_url": "https://gateway.example.com/mcp",
            "model_id": "anthropic.claude-sonnet-4-20250514",
            "agent_name": "da-analytics-agent",
        }

    def test_creates_output_directory(self, tmp_path, config, gateway_config):
        nested_dir = tmp_path / "nested" / "outputs"
        agent_file = nested_dir / "agent.json"

        with patch("deploy.deploy_agent.OUTPUTS_DIR", nested_dir):
            with patch("deploy.deploy_agent.AGENT_FILE", agent_file):
                save_outputs(config, gateway_config)

        assert nested_dir.exists()
        assert agent_file.exists()

    def test_output_file_ends_with_newline(self, tmp_path, config, gateway_config):
        agent_file = tmp_path / "agent.json"

        with patch("deploy.deploy_agent.OUTPUTS_DIR", tmp_path):
            with patch("deploy.deploy_agent.AGENT_FILE", agent_file):
                save_outputs(config, gateway_config)

        raw = agent_file.read_text()
        assert raw.endswith("\n")
