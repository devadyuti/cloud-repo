#!/usr/bin/env python3
"""Deploy AgentCore Gateway and register MCP server targets.

Creates an AgentCore Gateway with Custom JWT authentication (Cognito),
registers both the S3 Tables and Redshift MCP server runtimes as gateway
targets using DYNAMIC listing mode, and outputs the gateway URL and
target IDs for downstream scripts.

Outputs gateway details to deploy/outputs/gateway.json for downstream scripts.

Usage:
    python -m deploy.deploy_gateway          # Deploy gateway and targets
    python -m deploy.deploy_gateway --wait   # Deploy and poll until READY
"""

import argparse
import json
import logging
import os
import sys
import time
import urllib.parse
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from deploy.config import AgentCoreConfig

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

OUTPUTS_DIR = Path(__file__).parent / "outputs"
RUNTIMES_FILE = OUTPUTS_DIR / "runtimes.json"
COGNITO_FILE = OUTPUTS_DIR / "cognito.json"
GATEWAY_FILE = OUTPUTS_DIR / "gateway.json"

# Polling config for --wait flag
POLL_INTERVAL_SECONDS = 10
MAX_POLL_ATTEMPTS = 60  # 10 minutes max


def get_client(config: AgentCoreConfig):
    """Create a bedrock-agentcore-control boto3 client."""
    return boto3.client("bedrock-agentcore-control", region_name=config.region)


def load_runtime_arns() -> dict:
    """Load runtime ARNs from the runtimes deployment output file.

    Returns:
        Dict with keys 's3_tables_runtime_arn' and 'redshift_runtime_arn'.

    Raises:
        FileNotFoundError: If runtimes.json doesn't exist.
        KeyError: If expected keys are missing.
    """
    if not RUNTIMES_FILE.exists():
        raise FileNotFoundError(
            f"Runtime outputs not found at {RUNTIMES_FILE}. "
            "Run 'python -m deploy.deploy_runtimes' first."
        )

    data = json.loads(RUNTIMES_FILE.read_text())

    required_keys = ["s3_tables_runtime_arn", "redshift_runtime_arn"]
    for key in required_keys:
        if key not in data:
            raise KeyError(
                f"Missing key '{key}' in {RUNTIMES_FILE}. "
                "Re-run 'python -m deploy.deploy_runtimes' to regenerate."
            )

    return data


def load_cognito_config(config: AgentCoreConfig) -> dict:
    """Load Cognito configuration from file, environment, or CloudFormation.

    Resolution order:
      1. JSON file at deploy/outputs/cognito.json (if exists)
      2. Environment variables (AGENTCORE_COGNITO_*)
      3. CloudFormation exports (fallback)

    Returns:
        Dict with keys: 'pool_id', 'pool_arn', 'client_id', 'issuer_url'.

    Raises:
        RuntimeError: If Cognito config cannot be resolved from any source.
    """
    # Source 1: JSON file
    if COGNITO_FILE.exists():
        logger.info(f"Loading Cognito config from {COGNITO_FILE}")
        data = json.loads(COGNITO_FILE.read_text())
        if all(k in data for k in ("pool_id", "pool_arn", "client_id", "issuer_url")):
            return data
        logger.warning(f"Cognito file exists but is incomplete, trying other sources...")

    # Source 2: Environment variables
    env_pool_id = os.environ.get("AGENTCORE_COGNITO_POOL_ID", "")
    env_pool_arn = os.environ.get("AGENTCORE_COGNITO_POOL_ARN", "")
    env_client_id = os.environ.get("AGENTCORE_COGNITO_CLIENT_ID", "")
    env_issuer_url = os.environ.get("AGENTCORE_COGNITO_ISSUER_URL", "")

    if all([env_pool_id, env_pool_arn, env_client_id, env_issuer_url]):
        logger.info("Loading Cognito config from environment variables")
        return {
            "pool_id": env_pool_id,
            "pool_arn": env_pool_arn,
            "client_id": env_client_id,
            "issuer_url": env_issuer_url,
        }

    # Source 3: CloudFormation exports
    logger.info("Loading Cognito config from CloudFormation exports...")
    try:
        cfn_client = boto3.client("cloudformation", region_name=config.region)
        exports = {}

        paginator = cfn_client.get_paginator("list_exports")
        for page in paginator.paginate():
            for export in page["Exports"]:
                exports[export["Name"]] = export["Value"]

        export_mapping = {
            "AgentCoreMCPDemo-UserPoolId": "pool_id",
            "AgentCoreMCPDemo-UserPoolArn": "pool_arn",
            "AgentCoreMCPDemo-UserPoolClientId": "client_id",
            "AgentCoreMCPDemo-IssuerUrl": "issuer_url",
        }

        cognito_config = {}
        for export_name, config_key in export_mapping.items():
            if export_name not in exports:
                raise RuntimeError(
                    f"CloudFormation export '{export_name}' not found. "
                    "Deploy the Cognito stack first: cdk deploy AgentCoreMCPDemo-Cognito"
                )
            cognito_config[config_key] = exports[export_name]

        return cognito_config

    except ClientError as e:
        raise RuntimeError(
            f"Failed to load Cognito config from CloudFormation: {e}. "
            "Provide config via deploy/outputs/cognito.json or AGENTCORE_COGNITO_* env vars."
        ) from e


def build_runtime_endpoint(region: str, runtime_arn: str) -> str:
    """Build the MCP server endpoint URL for a runtime.

    The endpoint URL format is:
        https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded-arn}/invocations?qualifier=DEFAULT

    The runtime ARN must be URL-encoded (colons and slashes escaped).

    Args:
        region: AWS region (e.g. 'eu-west-1').
        runtime_arn: The full runtime ARN.

    Returns:
        The fully-qualified HTTPS endpoint URL.
    """
    encoded_arn = urllib.parse.quote(runtime_arn, safe="")
    return (
        f"https://bedrock-agentcore.{region}.amazonaws.com"
        f"/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    )


def find_existing_gateway(client, gateway_name: str) -> dict | None:
    """Check if a gateway with the given name already exists using list_gateways.

    Since get_gateway requires an ID (not a name), we list all gateways
    and filter by name for idempotent deployments.

    Returns the gateway details dict if it exists, None otherwise.
    """
    try:
        paginator = client.get_paginator("list_gateways")
        for page in paginator.paginate():
            for gateway in page.get("items", []):
                if gateway.get("name") == gateway_name:
                    gateway_id = gateway.get("gatewayId")
                    logger.info(
                        f"Gateway '{gateway_name}' already exists (ID: {gateway_id})"
                    )
                    return gateway
        return None
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code in ("ResourceNotFoundException", "ValidationException"):
            return None
        raise
    except Exception as e:
        # If paginator fails, try without it
        logger.debug(f"Paginator failed, trying direct list: {e}")
        try:
            response = client.list_gateways()
            for gateway in response.get("items", []):
                if gateway.get("name") == gateway_name:
                    return gateway
            return None
        except Exception:
            return None


def find_existing_target(client, gateway_id: str, target_name: str) -> dict | None:
    """Check if a gateway target with the given name already exists.

    Lists targets on the gateway and checks by name since the target ID
    is auto-generated and we identify targets by their configured name.

    Returns the target details dict if it exists, None otherwise.
    """
    try:
        paginator = client.get_paginator("list_gateway_targets")
        for page in paginator.paginate(gatewayIdentifier=gateway_id):
            for target in page.get("items", []):
                if target.get("name") == target_name:
                    target_id = target.get("targetId")
                    logger.info(
                        f"Gateway target '{target_name}' already exists "
                        f"(ID: {target_id}) on gateway '{gateway_id}'"
                    )
                    return target
        return None
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code in ("ResourceNotFoundException", "ValidationException"):
            return None
        raise
    except Exception as e:
        logger.debug(f"Paginator failed, trying direct list: {e}")
        try:
            response = client.list_gateway_targets(gatewayIdentifier=gateway_id)
            for target in response.get("items", []):
                if target.get("name") == target_name:
                    return target
            return None
        except Exception:
            return None


def create_gateway(client, config: AgentCoreConfig, cognito_config: dict) -> tuple[str, str]:
    """Create the AgentCore Gateway with Custom JWT authentication.

    Creates a gateway with:
    - MCP protocol type
    - CUSTOM_JWT authorizer backed by Cognito
    - Discovery URL pointing to the OIDC well-known configuration
    - Gateway IAM role for invoking runtimes

    Args:
        client: The bedrock-agentcore-control boto3 client.
        config: The AgentCore configuration.
        cognito_config: Dict with 'client_id', 'issuer_url'.

    Returns:
        Tuple of (gateway_id, gateway_url).
    """
    name = config.gateway_name

    # Idempotent: check if gateway already exists
    existing = find_existing_gateway(client, name)
    if existing:
        gateway_id = existing.get("gatewayId", "")
        # Fetch full details to get the gateway URL
        try:
            details = client.get_gateway(gatewayIdentifier=gateway_id)
            gateway_url = details.get("gatewayUrl", "")
        except ClientError:
            gateway_url = ""
        return gateway_id, gateway_url

    logger.info(f"Creating gateway '{name}'...")

    role_arn = config.role_arn(config.gateway_role_name)
    issuer_url = cognito_config["issuer_url"]
    discovery_url = f"{issuer_url}/.well-known/openid-configuration"

    logger.info(f"  Role ARN:      {role_arn}")
    logger.info(f"  Discovery URL: {discovery_url}")
    logger.info(f"  Allowed client: {cognito_config['client_id']}")

    response = client.create_gateway(
        name=name,
        description="D&A Domain MCP Gateway for analytics tools",
        roleArn=role_arn,
        protocolType="MCP",
        authorizerType="CUSTOM_JWT",
        authorizerConfiguration={
            "customJWTAuthorizer": {
                "discoveryUrl": discovery_url,
                "allowedAudience": [cognito_config["client_id"]],
                "allowedClients": [cognito_config["client_id"]],
            }
        },
    )

    gateway_id = response["gatewayId"]
    gateway_url = response.get("gatewayUrl", "")
    logger.info(f"Gateway created: ID={gateway_id}, URL={gateway_url}")
    return gateway_id, gateway_url


def create_target(
    client,
    config: AgentCoreConfig,
    gateway_id: str,
    target_name: str,
    description: str,
    runtime_arn: str,
) -> str:
    """Register an MCP server runtime as a gateway target.

    Creates a target with:
    - DYNAMIC listing mode (tools discovered on-demand)
    - IAM credential provider for bedrock-agentcore service
    - Endpoint URL pointing to the runtime invocation API

    Args:
        client: The bedrock-agentcore-control boto3 client.
        config: The AgentCore configuration.
        gateway_id: The gateway ID to register the target on.
        target_name: Name for the target.
        description: Human-readable description.
        runtime_arn: The full runtime ARN.

    Returns:
        The target ID.
    """
    # Idempotent: check if target already exists
    existing = find_existing_target(client, gateway_id, target_name)
    if existing:
        return existing.get("targetId", "")

    logger.info(f"Creating target '{target_name}' on gateway '{gateway_id}'...")

    endpoint_url = build_runtime_endpoint(config.region, runtime_arn)
    logger.info(f"  Endpoint: {endpoint_url}")

    response = client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name=target_name,
        description=description,
        targetConfiguration={
            "mcp": {
                "mcpServer": {
                    "endpoint": endpoint_url,
                    "listingMode": "DYNAMIC",
                }
            }
        },
        credentialProviderConfigurations=[
            {
                "credentialProviderType": "GATEWAY_IAM_ROLE",
                "credentialProvider": {
                    "iamCredentialProvider": {
                        "service": "bedrock-agentcore",
                        "region": config.region,
                    }
                },
            }
        ],
    )

    target_id = response["targetId"]
    logger.info(f"Target '{target_name}' created: ID={target_id}")
    return target_id


def wait_for_gateway_ready(client, gateway_id: str) -> str:
    """Poll until the gateway reaches READY status.

    Args:
        client: The bedrock-agentcore-control boto3 client.
        gateway_id: The gateway ID to poll.

    Returns:
        The final status string.

    Raises:
        TimeoutError: If the gateway doesn't become READY within the max poll window.
        RuntimeError: If the gateway enters a FAILED state.
    """
    logger.info(f"Waiting for gateway '{gateway_id}' to become READY...")

    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        response = client.get_gateway(gatewayIdentifier=gateway_id)
        status = response.get("status", "UNKNOWN")
        logger.info(f"  [{attempt}/{MAX_POLL_ATTEMPTS}] Gateway status: {status}")

        if status == "READY":
            return status
        if status in ("FAILED", "CREATE_FAILED"):
            failure_reason = response.get("statusReason", "No reason provided")
            raise RuntimeError(
                f"Gateway '{gateway_id}' entered {status} state: {failure_reason}"
            )

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        f"Gateway '{gateway_id}' did not reach READY status within "
        f"{MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS} seconds."
    )


def wait_for_target_ready(client, gateway_id: str, target_id: str, target_name: str) -> str:
    """Poll until a gateway target reaches READY status.

    Args:
        client: The bedrock-agentcore-control boto3 client.
        gateway_id: The gateway ID that owns the target.
        target_id: The target ID to poll.
        target_name: Display name for logging.

    Returns:
        The final status string.

    Raises:
        TimeoutError: If the target doesn't become READY within the max poll window.
        RuntimeError: If the target enters a FAILED state.
    """
    logger.info(f"Waiting for target '{target_name}' (ID: {target_id}) to become READY...")

    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        response = client.get_gateway_target(
            gatewayIdentifier=gateway_id, targetId=target_id
        )
        status = response.get("status", "UNKNOWN")
        logger.info(f"  [{attempt}/{MAX_POLL_ATTEMPTS}] {target_name}: {status}")

        if status == "READY":
            return status
        if status in ("FAILED", "CREATE_FAILED"):
            failure_reason = response.get("statusReason", "No reason provided")
            raise RuntimeError(
                f"Target '{target_name}' entered {status} state: {failure_reason}"
            )

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        f"Target '{target_name}' did not reach READY status within "
        f"{MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS} seconds."
    )


def save_outputs(
    gateway_id: str,
    gateway_url: str,
    s3_tables_target_id: str,
    redshift_target_id: str,
) -> None:
    """Save gateway details to deploy/outputs/gateway.json for downstream scripts."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "gateway_id": gateway_id,
        "gateway_url": gateway_url,
        "s3_tables_target_id": s3_tables_target_id,
        "redshift_target_id": redshift_target_id,
    }

    GATEWAY_FILE.write_text(json.dumps(outputs, indent=2) + "\n")
    logger.info(f"Gateway outputs saved to {GATEWAY_FILE}")


def main() -> None:
    """Orchestrate deployment of the AgentCore Gateway and targets."""
    parser = argparse.ArgumentParser(
        description="Deploy AgentCore Gateway and register MCP server targets."
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Poll until gateway and targets reach READY status.",
    )
    args = parser.parse_args()

    config = AgentCoreConfig.from_env()

    if not config.account_id:
        logger.error(
            "AGENTCORE_ACCOUNT_ID environment variable is required. "
            "Set it to your AWS account ID (e.g. export AGENTCORE_ACCOUNT_ID=123456789012)."
        )
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("AgentCore Gateway Deployment")
    logger.info("=" * 60)
    logger.info(f"  Region:  {config.region}")
    logger.info(f"  Account: {config.account_id}")
    logger.info("")

    # Load prerequisites
    logger.info("Loading prerequisites...")
    runtime_arns = load_runtime_arns()
    cognito_config = load_cognito_config(config)
    logger.info(f"  S3 Tables runtime: {runtime_arns['s3_tables_runtime_arn']}")
    logger.info(f"  Redshift runtime:  {runtime_arns['redshift_runtime_arn']}")
    logger.info(f"  Cognito issuer:    {cognito_config['issuer_url']}")
    logger.info("")

    client = get_client(config)

    # Step 1: Create gateway
    gateway_id, gateway_url = create_gateway(client, config, cognito_config)

    # Step 2: Register S3 Tables target
    s3_tables_target_id = create_target(
        client,
        config,
        gateway_id,
        target_name=config.s3_tables_target_name,
        description="S3 Tables discovery and query tools",
        runtime_arn=runtime_arns["s3_tables_runtime_arn"],
    )

    # Step 3: Register Redshift target
    redshift_target_id = create_target(
        client,
        config,
        gateway_id,
        target_name=config.redshift_target_name,
        description="Redshift analytics discovery and query tools",
        runtime_arn=runtime_arns["redshift_runtime_arn"],
    )

    # Note: SynchronizeGatewayTargets is NOT supported for DYNAMIC listing mode.
    # Targets using DYNAMIC mode discover tools on-demand, no sync needed.

    # Save outputs for downstream scripts
    save_outputs(gateway_id, gateway_url, s3_tables_target_id, redshift_target_id)

    # Optionally wait for gateway and targets to become READY
    if args.wait:
        logger.info("")
        logger.info("Waiting for gateway and targets to become READY...")
        wait_for_gateway_ready(client, gateway_id)
        wait_for_target_ready(client, gateway_id, s3_tables_target_id, config.s3_tables_target_name)
        wait_for_target_ready(client, gateway_id, redshift_target_id, config.redshift_target_name)
        logger.info("Gateway and all targets are READY.")

    logger.info("")
    logger.info("Deployment complete.")
    logger.info(f"  Gateway ID:           {gateway_id}")
    logger.info(f"  Gateway URL:          {gateway_url}")
    logger.info(f"  S3 Tables target ID:  {s3_tables_target_id}")
    logger.info(f"  Redshift target ID:   {redshift_target_id}")


if __name__ == "__main__":
    main()
