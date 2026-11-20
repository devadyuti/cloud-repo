"""Tests for deploy.config module.

Validates default values, environment variable overrides via from_env(),
and helper methods (ecr_image_uri, role_arn).
"""

import os
from unittest.mock import patch

import pytest

from deploy.config import AgentCoreConfig


# ---------------------------------------------------------------------------
# Default Values
# ---------------------------------------------------------------------------


class TestDefaults:
    def test_gateway_role_name_default(self):
        """gateway_role_name defaults to AgentCoreGatewayRole."""
        config = AgentCoreConfig()
        assert config.gateway_role_name == "AgentCoreGatewayRole"

    def test_s3_tables_role_name_default(self):
        config = AgentCoreConfig()
        assert config.s3_tables_role_name == "AgentCoreS3TablesRole"

    def test_redshift_role_name_default(self):
        config = AgentCoreConfig()
        assert config.redshift_role_name == "AgentCoreRedshiftRole"

    def test_region_default(self):
        config = AgentCoreConfig()
        assert config.region == "eu-west-1"

    def test_gateway_name_default(self):
        config = AgentCoreConfig()
        assert config.gateway_name == "da-analytics-gateway"


# ---------------------------------------------------------------------------
# from_env() — Environment Variable Overrides
# ---------------------------------------------------------------------------


class TestFromEnv:
    def test_gateway_role_name_from_env(self):
        """AGENTCORE_GATEWAY_ROLE_NAME overrides gateway_role_name."""
        env = {"AGENTCORE_GATEWAY_ROLE_NAME": "CustomGatewayRole"}
        with patch.dict(os.environ, env, clear=False):
            config = AgentCoreConfig.from_env()
        assert config.gateway_role_name == "CustomGatewayRole"

    def test_gateway_role_name_uses_default_when_env_unset(self):
        """Without AGENTCORE_GATEWAY_ROLE_NAME, uses the default."""
        env_vars_to_remove = ["AGENTCORE_GATEWAY_ROLE_NAME"]
        with patch.dict(os.environ, {}, clear=False):
            for var in env_vars_to_remove:
                os.environ.pop(var, None)
            config = AgentCoreConfig.from_env()
        assert config.gateway_role_name == "AgentCoreGatewayRole"

    def test_s3_tables_role_name_from_env(self):
        env = {"AGENTCORE_S3_TABLES_ROLE_NAME": "MyS3Role"}
        with patch.dict(os.environ, env, clear=False):
            config = AgentCoreConfig.from_env()
        assert config.s3_tables_role_name == "MyS3Role"

    def test_redshift_role_name_from_env(self):
        env = {"AGENTCORE_REDSHIFT_ROLE_NAME": "MyRedshiftRole"}
        with patch.dict(os.environ, env, clear=False):
            config = AgentCoreConfig.from_env()
        assert config.redshift_role_name == "MyRedshiftRole"

    def test_region_from_env(self):
        env = {"AGENTCORE_REGION": "us-east-1"}
        with patch.dict(os.environ, env, clear=False):
            config = AgentCoreConfig.from_env()
        assert config.region == "us-east-1"

    def test_vpc_subnet_ids_from_env(self):
        env = {"AGENTCORE_VPC_SUBNET_IDS": "subnet-aaa, subnet-bbb"}
        with patch.dict(os.environ, env, clear=False):
            config = AgentCoreConfig.from_env()
        assert config.vpc_subnet_ids == ["subnet-aaa", "subnet-bbb"]

    def test_vpc_subnet_ids_empty_string_uses_default(self):
        env = {"AGENTCORE_VPC_SUBNET_IDS": ""}
        with patch.dict(os.environ, env, clear=False):
            config = AgentCoreConfig.from_env()
        assert config.vpc_subnet_ids == []


# ---------------------------------------------------------------------------
# Helper Methods
# ---------------------------------------------------------------------------


class TestRoleArn:
    def test_role_arn_for_gateway_role(self):
        """role_arn() constructs correct ARN for gateway_role_name."""
        config = AgentCoreConfig(account_id="123456789012")
        arn = config.role_arn(config.gateway_role_name)
        assert arn == "arn:aws:iam::123456789012:role/AgentCoreGatewayRole"

    def test_role_arn_for_s3_tables_role(self):
        config = AgentCoreConfig(account_id="111222333444")
        arn = config.role_arn(config.s3_tables_role_name)
        assert arn == "arn:aws:iam::111222333444:role/AgentCoreS3TablesRole"

    def test_role_arn_for_redshift_role(self):
        config = AgentCoreConfig(account_id="111222333444")
        arn = config.role_arn(config.redshift_role_name)
        assert arn == "arn:aws:iam::111222333444:role/AgentCoreRedshiftRole"


class TestEcrImageUri:
    def test_default_tag(self):
        config = AgentCoreConfig(account_id="123456789012", region="eu-west-1")
        uri = config.ecr_image_uri("s3-tables-mcp-server")
        assert uri == "123456789012.dkr.ecr.eu-west-1.amazonaws.com/s3-tables-mcp-server:latest"

    def test_custom_tag(self):
        config = AgentCoreConfig(account_id="123456789012", region="eu-west-1")
        uri = config.ecr_image_uri("redshift-mcp-server", tag="v1.2.3")
        assert uri == "123456789012.dkr.ecr.eu-west-1.amazonaws.com/redshift-mcp-server:v1.2.3"
