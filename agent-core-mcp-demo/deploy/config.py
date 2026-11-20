"""Shared configuration for AgentCore MCP demo deployment.

All values have sensible defaults and can be overridden via environment variables
prefixed with AGENTCORE_ (e.g. AGENTCORE_REGION, AGENTCORE_ACCOUNT_ID).
"""

import os
from dataclasses import dataclass, field


@dataclass
class AgentCoreConfig:
    """Central configuration for AgentCore MCP demo resources."""

    region: str = "eu-west-1"
    account_id: str = ""  # Set via environment or CDK context

    # ECR
    s3_tables_repo_name: str = "s3-tables-mcp-server"
    redshift_repo_name: str = "redshift-mcp-server"

    # AgentCore Runtime (names must match [a-zA-Z][a-zA-Z0-9_]{0,47})
    s3_tables_runtime_name: str = "s3_tables_mcp_server"
    redshift_runtime_name: str = "redshift_mcp_server"

    # AgentCore Gateway
    gateway_name: str = "da-analytics-gateway"
    s3_tables_target_name: str = "s3-tables"
    redshift_target_name: str = "redshift-analytics"

    # Cognito
    cognito_pool_name: str = "da-analytics-pool"

    # Agent
    agent_name: str = "da-analytics-agent"
    agent_model: str = "anthropic.claude-sonnet-4-20250514"

    # IAM Roles
    s3_tables_role_name: str = "AgentCoreS3TablesRole"
    redshift_role_name: str = "AgentCoreRedshiftRole"
    gateway_role_name: str = "AgentCoreGatewayRole"

    # VPC (Redshift connectivity)
    vpc_subnet_ids: list = field(default_factory=list)
    vpc_security_group_ids: list = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "AgentCoreConfig":
        """Create config from environment variables, falling back to defaults.

        Environment variable mapping:
            AGENTCORE_REGION              -> region
            AGENTCORE_ACCOUNT_ID          -> account_id
            AGENTCORE_S3_TABLES_REPO_NAME -> s3_tables_repo_name
            AGENTCORE_REDSHIFT_REPO_NAME  -> redshift_repo_name
            AGENTCORE_S3_TABLES_RUNTIME_NAME -> s3_tables_runtime_name (must match [a-zA-Z][a-zA-Z0-9_]{0,47})
            AGENTCORE_REDSHIFT_RUNTIME_NAME  -> redshift_runtime_name (must match [a-zA-Z][a-zA-Z0-9_]{0,47})
            AGENTCORE_GATEWAY_NAME        -> gateway_name
            AGENTCORE_S3_TABLES_TARGET_NAME -> s3_tables_target_name
            AGENTCORE_REDSHIFT_TARGET_NAME  -> redshift_target_name
            AGENTCORE_COGNITO_POOL_NAME   -> cognito_pool_name
            AGENTCORE_AGENT_NAME          -> agent_name
            AGENTCORE_AGENT_MODEL         -> agent_model
            AGENTCORE_S3_TABLES_ROLE_NAME -> s3_tables_role_name
            AGENTCORE_REDSHIFT_ROLE_NAME  -> redshift_role_name
            AGENTCORE_GATEWAY_ROLE_NAME   -> gateway_role_name
            AGENTCORE_VPC_SUBNET_IDS      -> vpc_subnet_ids (comma-separated)
            AGENTCORE_VPC_SECURITY_GROUP_IDS -> vpc_security_group_ids (comma-separated)
        """
        defaults = cls()

        def _get(env_var, default):
            return os.environ.get(env_var, default)

        def _get_list(env_var, default):
            raw = os.environ.get(env_var, "")
            if raw.strip():
                return [item.strip() for item in raw.split(",") if item.strip()]
            return default

        return cls(
            region=_get("AGENTCORE_REGION", defaults.region),
            account_id=_get("AGENTCORE_ACCOUNT_ID", defaults.account_id),
            s3_tables_repo_name=_get("AGENTCORE_S3_TABLES_REPO_NAME", defaults.s3_tables_repo_name),
            redshift_repo_name=_get("AGENTCORE_REDSHIFT_REPO_NAME", defaults.redshift_repo_name),
            s3_tables_runtime_name=_get("AGENTCORE_S3_TABLES_RUNTIME_NAME", defaults.s3_tables_runtime_name),
            redshift_runtime_name=_get("AGENTCORE_REDSHIFT_RUNTIME_NAME", defaults.redshift_runtime_name),
            gateway_name=_get("AGENTCORE_GATEWAY_NAME", defaults.gateway_name),
            s3_tables_target_name=_get("AGENTCORE_S3_TABLES_TARGET_NAME", defaults.s3_tables_target_name),
            redshift_target_name=_get("AGENTCORE_REDSHIFT_TARGET_NAME", defaults.redshift_target_name),
            cognito_pool_name=_get("AGENTCORE_COGNITO_POOL_NAME", defaults.cognito_pool_name),
            agent_name=_get("AGENTCORE_AGENT_NAME", defaults.agent_name),
            agent_model=_get("AGENTCORE_AGENT_MODEL", defaults.agent_model),
            s3_tables_role_name=_get("AGENTCORE_S3_TABLES_ROLE_NAME", defaults.s3_tables_role_name),
            redshift_role_name=_get("AGENTCORE_REDSHIFT_ROLE_NAME", defaults.redshift_role_name),
            gateway_role_name=_get("AGENTCORE_GATEWAY_ROLE_NAME", defaults.gateway_role_name),
            vpc_subnet_ids=_get_list("AGENTCORE_VPC_SUBNET_IDS", defaults.vpc_subnet_ids),
            vpc_security_group_ids=_get_list("AGENTCORE_VPC_SECURITY_GROUP_IDS", defaults.vpc_security_group_ids),
        )

    def ecr_image_uri(self, repo_name: str, tag: str = "latest") -> str:
        """Construct a full ECR image URI for the given repository name.

        Args:
            repo_name: ECR repository name (e.g. 's3-tables-mcp-server')
            tag: Image tag, defaults to 'latest'

        Returns:
            Full ECR image URI like '<account>.dkr.ecr.<region>.amazonaws.com/<repo>:<tag>'
        """
        return f"{self.account_id}.dkr.ecr.{self.region}.amazonaws.com/{repo_name}:{tag}"

    def role_arn(self, role_name: str) -> str:
        """Construct a full IAM role ARN for the given role name.

        Args:
            role_name: IAM role name (e.g. 'AgentCoreS3TablesRole')

        Returns:
            Full IAM role ARN like 'arn:aws:iam::<account>:role/<role_name>'
        """
        return f"arn:aws:iam::{self.account_id}:role/{role_name}"
