#!/usr/bin/env python3
"""Validate AgentCore Gateway readiness and save agent configuration.

Verifies that the AgentCore Gateway is READY, confirms both MCP server
targets (S3 Tables and Redshift) are registered, and saves the agent
configuration for the Strands-based demo agent.

Outputs agent config to deploy/outputs/agent.json for downstream scripts.

Usage:
    python -m deploy.deploy_agent           # Validate gateway and save config
    python -m deploy.deploy_agent --verify  # Also attempt to list tools from gateway
"""

import argparse
import json
import logging
import sys
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
GATEWAY_FILE = OUTPUTS_DIR / "gateway.json"
AGENT_FILE = OUTPUTS_DIR / "agent.json"


def get_client(config: AgentCoreConfig):
    """Create a bedrock-agentcore-control boto3 client."""
    return boto3.client("bedrock-agentcore-control", region_name=config.region)


def load_gateway_config() -> dict:
    """Load gateway configuration from the gateway deployment output file.

    Returns:
        Dict with keys: 'gateway_id', 'gateway_url', 's3_tables_target_id',
        'redshift_target_id'.

    Raises:
        FileNotFoundError: If gateway.json doesn't exist.
        KeyError: If expected keys are missing.
    """
    if not GATEWAY_FILE.exists():
        raise FileNotFoundError(
            f"Gateway outputs not found at {GATEWAY_FILE}. "
            "Run 'python -m deploy.deploy_gateway' first."
        )

    data = json.loads(GATEWAY_FILE.read_text())

    required_keys = ["gateway_id", "gateway_url", "s3_tables_target_id", "redshift_target_id"]
    for key in required_keys:
        if key not in data:
            raise KeyError(
                f"Missing key '{key}' in {GATEWAY_FILE}. "
                "Re-run 'python -m deploy.deploy_gateway' to regenerate."
            )

    return data


def verify_gateway_status(client, gateway_id: str) -> dict:
    """Verify the gateway exists and check its status.

    Args:
        client: The bedrock-agentcore-control boto3 client.
        gateway_id: The gateway ID to verify.

    Returns:
        The full gateway response dict.

    Raises:
        RuntimeError: If gateway is not found or not in READY/ACTIVE state.
    """
    logger.info(f"Verifying gateway '{gateway_id}' status...")

    try:
        response = client.get_gateway(gatewayIdentifier=gateway_id)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            raise RuntimeError(
                f"Gateway '{gateway_id}' not found. "
                "Run 'python -m deploy.deploy_gateway' to create it."
            ) from e
        raise

    status = response.get("status", "UNKNOWN")
    logger.info(f"  Gateway status: {status}")

    # Accept READY, ACTIVE, or UPDATING as valid states
    valid_states = {"READY", "ACTIVE", "UPDATING"}
    if status not in valid_states:
        raise RuntimeError(
            f"Gateway '{gateway_id}' is in '{status}' state (expected one of {valid_states}). "
            "Wait for it to become READY or re-deploy."
        )

    return response


def verify_gateway_targets(client, gateway_id: str, expected_target_ids: list[str]) -> list[dict]:
    """Verify that the expected targets are registered on the gateway.

    Args:
        client: The bedrock-agentcore-control boto3 client.
        gateway_id: The gateway ID to check targets on.
        expected_target_ids: List of target IDs that should exist.

    Returns:
        List of target detail dicts found on the gateway.

    Raises:
        RuntimeError: If any expected targets are missing.
    """
    logger.info(f"Verifying gateway targets on '{gateway_id}'...")

    found_targets = []
    try:
        paginator = client.get_paginator("list_gateway_targets")
        for page in paginator.paginate(gatewayIdentifier=gateway_id):
            for target in page.get("items", []):
                found_targets.append(target)
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            raise RuntimeError(
                f"Gateway '{gateway_id}' not found when listing targets."
            ) from e
        raise
    except Exception as e:
        # Fallback if paginator not available
        logger.debug(f"Paginator failed, trying direct list: {e}")
        try:
            response = client.list_gateway_targets(gatewayIdentifier=gateway_id)
            found_targets = response.get("items", [])
        except Exception as fallback_err:
            raise RuntimeError(
                f"Failed to list gateway targets: {fallback_err}"
            ) from fallback_err

    found_ids = {t.get("targetId") for t in found_targets}
    missing = [tid for tid in expected_target_ids if tid not in found_ids]

    if missing:
        raise RuntimeError(
            f"Missing gateway targets: {missing}. "
            "Re-run 'python -m deploy.deploy_gateway' to register them."
        )

    for target in found_targets:
        target_id = target.get("targetId", "unknown")
        target_name = target.get("name", "unnamed")
        target_status = target.get("status", "UNKNOWN")
        logger.info(f"  Target '{target_name}' (ID: {target_id}): {target_status}")

    return found_targets


def verify_tools_via_http(gateway_url: str) -> None:
    """Attempt to list tools from the gateway via HTTP POST (requires auth token).

    This is a best-effort verification. It will likely fail without a valid
    JWT token, but confirms the gateway URL is reachable.

    Args:
        gateway_url: The full gateway MCP endpoint URL.
    """
    logger.info(f"Attempting tool discovery at: {gateway_url}")

    try:
        import urllib.request
        import urllib.error

        # MCP protocol: send an initialize request to verify connectivity
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "deploy-verify", "version": "1.0.0"},
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            gateway_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            logger.info(f"  Gateway responded ({resp.status}): {body[:200]}")

    except urllib.error.HTTPError as e:
        # 401/403 is expected without a valid JWT — gateway is reachable
        if e.code in (401, 403):
            logger.info(
                f"  Gateway returned {e.code} (expected without JWT token) — "
                "endpoint is reachable and auth is enforced."
            )
        else:
            logger.warning(f"  Gateway returned HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        logger.warning(f"  Could not reach gateway URL: {e.reason}")
    except Exception as e:
        logger.warning(f"  Tool verification failed: {e}")


def save_outputs(config: AgentCoreConfig, gateway_config: dict) -> None:
    """Save agent configuration to deploy/outputs/agent.json.

    This file is consumed by the demo agent (demo/run_agent.py) to know
    which gateway to connect to and which model to use.
    """
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "agent_type": "strands-local",
        "gateway_id": gateway_config["gateway_id"],
        "gateway_url": gateway_config["gateway_url"],
        "model_id": config.agent_model,
        "agent_name": config.agent_name,
    }

    AGENT_FILE.write_text(json.dumps(outputs, indent=2) + "\n")
    logger.info(f"Agent config saved to {AGENT_FILE}")


def main() -> None:
    """Validate gateway readiness and save agent configuration."""
    parser = argparse.ArgumentParser(
        description="Validate AgentCore Gateway and save agent configuration for Strands demo agent."
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Also attempt to list tools from the gateway via HTTP POST.",
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
    logger.info("Agent Configuration — Gateway Validation")
    logger.info("=" * 60)
    logger.info(f"  Region:  {config.region}")
    logger.info(f"  Account: {config.account_id}")
    logger.info("")

    # Load gateway config from previous deployment step
    logger.info("Loading gateway configuration...")
    gateway_config = load_gateway_config()
    logger.info(f"  Gateway ID:  {gateway_config['gateway_id']}")
    logger.info(f"  Gateway URL: {gateway_config['gateway_url']}")
    logger.info("")

    client = get_client(config)

    # Step 1: Verify gateway is READY
    verify_gateway_status(client, gateway_config["gateway_id"])

    # Step 2: Verify both targets exist
    expected_targets = [
        gateway_config["s3_tables_target_id"],
        gateway_config["redshift_target_id"],
    ]
    verify_gateway_targets(client, gateway_config["gateway_id"], expected_targets)

    # Step 3: Save agent config for the Strands demo agent
    save_outputs(config, gateway_config)

    # Step 4 (optional): Verify gateway reachability via HTTP
    if args.verify:
        logger.info("")
        verify_tools_via_http(gateway_config["gateway_url"])

    logger.info("")
    logger.info("=" * 60)
    logger.info("Validation complete — gateway is ready for agent use.")
    logger.info("=" * 60)
    logger.info("")
    logger.info(f"  Agent type:  strands-local")
    logger.info(f"  Agent name:  {config.agent_name}")
    logger.info(f"  Model:       {config.agent_model}")
    logger.info(f"  Gateway:     {gateway_config['gateway_id']}")
    logger.info(f"  Gateway URL: {gateway_config['gateway_url']}")
    logger.info("")
    logger.info("Next step: Run the interactive demo agent:")
    logger.info("")
    logger.info("    python -m demo.run_agent")
    logger.info("")
    logger.info("Or run a single query:")
    logger.info("")
    logger.info('    python -m demo.run_agent --query "What tables are available?"')
    logger.info("")


if __name__ == "__main__":
    main()
