#!/usr/bin/env python3
"""Deploy AgentCore Runtimes for S3 Tables and Redshift MCP servers.

Creates two AgentCore Runtimes via the bedrock-agentcore-control API:
  1. S3 Tables MCP Server — stateless HTTP, public network mode
  2. Redshift MCP Server — stateless HTTP, VPC connectivity (or PUBLIC fallback)

Outputs runtime ARNs and IDs to deploy/outputs/runtimes.json for downstream scripts.

Usage:
    python -m deploy.deploy_runtimes          # Deploy both runtimes
    python -m deploy.deploy_runtimes --wait   # Deploy and poll until ACTIVE
"""

import argparse
import json
import logging
import sys
import time
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
OUTPUTS_FILE = OUTPUTS_DIR / "runtimes.json"

# Polling config for --wait flag
POLL_INTERVAL_SECONDS = 10
MAX_POLL_ATTEMPTS = 60  # 10 minutes max


def get_client(config: AgentCoreConfig):
    """Create a bedrock-agentcore-control boto3 client."""
    return boto3.client("bedrock-agentcore-control", region_name=config.region)


def find_existing_runtime(client, runtime_name: str) -> dict | None:
    """Check if a runtime with the given name already exists using list_agent_runtimes.

    Since get_agent_runtime requires an ID (not a name), we list all runtimes
    and filter by name for idempotent deployments.

    Returns the runtime details dict if it exists, None otherwise.
    """
    try:
        paginator = client.get_paginator("list_agent_runtimes")
        for page in paginator.paginate():
            for runtime in page.get("runtimeSummaries", []):
                if runtime.get("name") == runtime_name or runtime.get("agentRuntimeName") == runtime_name:
                    runtime_id = runtime.get("agentRuntimeId", runtime.get("id"))
                    runtime_arn = runtime.get("agentRuntimeArn", runtime.get("arn"))
                    logger.info(
                        f"Runtime '{runtime_name}' already exists "
                        f"(ARN: {runtime_arn}, ID: {runtime_id})"
                    )
                    return runtime
        return None
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code in ("ResourceNotFoundException", "ValidationException"):
            return None
        raise
    except Exception as e:
        # If list_agent_runtimes pagination fails, try without paginator
        logger.debug(f"Paginator failed, trying direct list: {e}")
        try:
            response = client.list_agent_runtimes()
            for runtime in response.get("runtimeSummaries", []):
                if runtime.get("name") == runtime_name or runtime.get("agentRuntimeName") == runtime_name:
                    return runtime
            return None
        except Exception:
            return None


def deploy_s3_tables_runtime(client, config: AgentCoreConfig) -> tuple[str, str]:
    """Deploy the S3 Tables MCP Server runtime.

    Creates an AgentCore Runtime with:
    - ECR image from the s3-tables-mcp-server repository
    - AWS_REGION and FASTMCP_LOG_LEVEL environment variables (top-level)
    - MCP server protocol configuration
    - PUBLIC network mode (no VPC needed for S3 Tables)
    - S3 Tables IAM role for data access

    Returns:
        Tuple of (runtime_arn, runtime_id).
    """
    name = config.s3_tables_runtime_name

    # Idempotent: check if runtime already exists
    existing = find_existing_runtime(client, name)
    if existing:
        arn = existing.get("agentRuntimeArn", existing.get("arn", ""))
        rid = existing.get("agentRuntimeId", existing.get("id", ""))
        return arn, rid

    logger.info(f"Creating S3 Tables runtime '{name}'...")

    image_uri = config.ecr_image_uri(config.s3_tables_repo_name)
    role_arn = config.role_arn(config.s3_tables_role_name)

    logger.info(f"  Image URI: {image_uri}")
    logger.info(f"  Role ARN:  {role_arn}")

    response = client.create_agent_runtime(
        agentRuntimeName=name,
        description="S3 Tables MCP Server for D&A domain",
        agentRuntimeArtifact={
            "containerConfiguration": {
                "containerUri": image_uri,
            }
        },
        roleArn=role_arn,
        environmentVariables={
            "AWS_REGION": config.region,
            "FASTMCP_LOG_LEVEL": "INFO",
        },
        protocolConfiguration={
            "serverProtocol": "MCP",
        },
        networkConfiguration={
            "networkMode": "PUBLIC",
        },
    )

    runtime_arn = response["agentRuntimeArn"]
    runtime_id = response["agentRuntimeId"]
    logger.info(f"S3 Tables runtime created: ARN={runtime_arn}, ID={runtime_id}")
    return runtime_arn, runtime_id


def deploy_redshift_runtime(client, config: AgentCoreConfig) -> tuple[str, str]:
    """Deploy the Redshift MCP Server runtime.

    Creates an AgentCore Runtime with:
    - ECR image from the redshift-mcp-server repository
    - AWS_REGION and FASTMCP_LOG_LEVEL environment variables (top-level)
    - MCP server protocol configuration
    - VPC network config (subnets + security groups) for Redshift connectivity,
      or PUBLIC mode if VPC IDs are not configured
    - Redshift IAM role for Data API access

    Returns:
        Tuple of (runtime_arn, runtime_id).
    """
    name = config.redshift_runtime_name

    # Idempotent: check if runtime already exists
    existing = find_existing_runtime(client, name)
    if existing:
        arn = existing.get("agentRuntimeArn", existing.get("arn", ""))
        rid = existing.get("agentRuntimeId", existing.get("id", ""))
        return arn, rid

    logger.info(f"Creating Redshift runtime '{name}'...")

    image_uri = config.ecr_image_uri(config.redshift_repo_name)
    role_arn = config.role_arn(config.redshift_role_name)

    logger.info(f"  Image URI: {image_uri}")
    logger.info(f"  Role ARN:  {role_arn}")

    create_params = {
        "agentRuntimeName": name,
        "description": "Redshift MCP Server for D&A analytics queries",
        "agentRuntimeArtifact": {
            "containerConfiguration": {
                "containerUri": image_uri,
            }
        },
        "roleArn": role_arn,
        "environmentVariables": {
            "AWS_REGION": config.region,
            "FASTMCP_LOG_LEVEL": "INFO",
        },
        "protocolConfiguration": {
            "serverProtocol": "MCP",
        },
    }

    # Add VPC network config if subnet/SG IDs are provided
    if config.vpc_subnet_ids and config.vpc_security_group_ids:
        create_params["networkConfiguration"] = {
            "networkMode": "VPC",
            "networkModeConfig": {
                "subnets": config.vpc_subnet_ids,
                "securityGroups": config.vpc_security_group_ids,
            },
        }
        logger.info(
            f"  VPC config: subnets={config.vpc_subnet_ids}, "
            f"security_groups={config.vpc_security_group_ids}"
        )
    else:
        create_params["networkConfiguration"] = {
            "networkMode": "PUBLIC",
        }
        logger.warning(
            "No VPC subnet/security group IDs configured. "
            "Redshift runtime will deploy in PUBLIC mode — "
            "set AGENTCORE_VPC_SUBNET_IDS and AGENTCORE_VPC_SECURITY_GROUP_IDS for VPC connectivity."
        )

    response = client.create_agent_runtime(**create_params)

    runtime_arn = response["agentRuntimeArn"]
    runtime_id = response["agentRuntimeId"]
    logger.info(f"Redshift runtime created: ARN={runtime_arn}, ID={runtime_id}")
    return runtime_arn, runtime_id


def wait_for_runtime_active(client, runtime_id: str, runtime_name: str) -> str:
    """Poll until a runtime reaches ACTIVE status.

    Args:
        client: The bedrock-agentcore-control boto3 client.
        runtime_id: The agentRuntimeId to poll (get_agent_runtime uses ID).
        runtime_name: Display name for logging.

    Returns:
        The final status string.

    Raises:
        TimeoutError: If the runtime doesn't become ACTIVE within the max poll window.
        RuntimeError: If the runtime enters a FAILED state.
    """
    logger.info(f"Waiting for runtime '{runtime_name}' (ID: {runtime_id}) to become ACTIVE/READY or READY...")

    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        response = client.get_agent_runtime(agentRuntimeId=runtime_id)
        status = response.get("status", "UNKNOWN")
        logger.info(f"  [{attempt}/{MAX_POLL_ATTEMPTS}] {runtime_name}: {status}")

        if status in ("ACTIVE", "READY"):
            return status
        if status in ("FAILED", "DELETE_FAILED"):
            failure_reason = response.get("statusReason", "No reason provided")
            raise RuntimeError(
                f"Runtime '{runtime_name}' entered {status} state: {failure_reason}"
            )

        time.sleep(POLL_INTERVAL_SECONDS)

    raise TimeoutError(
        f"Runtime '{runtime_name}' did not reach ACTIVE/READY status within "
        f"{MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS} seconds."
    )


def save_outputs(
    s3_tables_arn: str,
    s3_tables_id: str,
    redshift_arn: str,
    redshift_id: str,
) -> None:
    """Save runtime ARNs and IDs to deploy/outputs/runtimes.json for downstream scripts."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "s3_tables_runtime_arn": s3_tables_arn,
        "s3_tables_runtime_id": s3_tables_id,
        "redshift_runtime_arn": redshift_arn,
        "redshift_runtime_id": redshift_id,
    }

    OUTPUTS_FILE.write_text(json.dumps(outputs, indent=2) + "\n")
    logger.info(f"Runtime ARNs and IDs saved to {OUTPUTS_FILE}")


def main() -> None:
    """Orchestrate deployment of both AgentCore runtimes."""
    parser = argparse.ArgumentParser(
        description="Deploy AgentCore Runtimes for S3 Tables and Redshift MCP servers."
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Poll until both runtimes reach ACTIVE status.",
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
    logger.info("AgentCore Runtime Deployment")
    logger.info("=" * 60)
    logger.info(f"  Region:  {config.region}")
    logger.info(f"  Account: {config.account_id}")
    logger.info("")

    client = get_client(config)

    # Deploy S3 Tables runtime
    s3_tables_arn, s3_tables_id = deploy_s3_tables_runtime(client, config)

    # Deploy Redshift runtime
    redshift_arn, redshift_id = deploy_redshift_runtime(client, config)

    # Save outputs for downstream scripts
    save_outputs(s3_tables_arn, s3_tables_id, redshift_arn, redshift_id)

    # Optionally wait for runtimes to become ACTIVE/READY or READY
    if args.wait:
        logger.info("")
        logger.info("Waiting for runtimes to become ACTIVE/READY or READY...")
        wait_for_runtime_active(client, s3_tables_id, config.s3_tables_runtime_name)
        wait_for_runtime_active(client, redshift_id, config.redshift_runtime_name)
        logger.info("Both runtimes are ACTIVE.")

    logger.info("")
    logger.info("Deployment complete.")
    logger.info(f"  S3 Tables runtime ARN: {s3_tables_arn}")
    logger.info(f"  S3 Tables runtime ID:  {s3_tables_id}")
    logger.info(f"  Redshift runtime ARN:  {redshift_arn}")
    logger.info(f"  Redshift runtime ID:   {redshift_id}")


if __name__ == "__main__":
    main()
