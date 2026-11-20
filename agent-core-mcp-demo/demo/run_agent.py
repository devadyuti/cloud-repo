#!/usr/bin/env python3
"""Interactive D&A analytics agent connected to AgentCore Gateway.

Uses Strands Agents with BedrockModel and MCPClient to connect to the
AgentCore Gateway for tool discovery and invocation. Authenticates to
the gateway using AWS SigV4 (service: bedrock-agentcore).

Usage:
    python -m demo.run_agent
    python -m demo.run_agent --query "What tables are available?"
    AGENTCORE_GATEWAY_URL=https://... python -m demo.run_agent
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# Dependency check — provide clear install instructions if missing
try:
    from strands import Agent
    from strands.models.bedrock import BedrockModel
    from strands.tools.mcp import MCPClient
except ImportError as e:
    print(
        "\nError: Required packages are not installed.\n"
        "Install them with:\n\n"
        "    pip install strands-agents mcp\n\n"
        f"Missing: {e.name if hasattr(e, 'name') else e}\n",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    from mcp.client.streamable_http import streamablehttp_client
except ImportError as e:
    print(
        "\nError: MCP client package is not installed or outdated.\n"
        "Install/upgrade with:\n\n"
        "    pip install mcp>=1.0.0\n\n"
        f"Missing: {e.name if hasattr(e, 'name') else e}\n",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    import httpx
    from botocore.session import Session as BotocoreSession
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
except ImportError as e:
    print(
        "\nError: Required packages for SigV4 auth are not installed.\n"
        "Install them with:\n\n"
        "    pip install httpx botocore\n\n"
        f"Missing: {e.name if hasattr(e, 'name') else e}\n",
        file=sys.stderr,
    )
    sys.exit(1)

logger = logging.getLogger(__name__)

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "deploy" / "outputs"
AGENT_FILE = OUTPUTS_DIR / "agent.json"

# Default service name and region for AgentCore Gateway SigV4 signing
AGENTCORE_SERVICE = "bedrock-agentcore"
AGENTCORE_DEFAULT_REGION = "eu-west-1"


class SigV4AuthFlow(httpx.Auth):
    """httpx Auth handler that signs every request with AWS SigV4.

    This is required for AgentCore Gateway endpoints that use the AWS_IAM
    authorizer type. Each outgoing HTTP request is signed using the caller's
    AWS credentials (resolved via the standard botocore credential chain:
    env vars, ~/.aws/credentials, IAM role, etc.).

    The signature covers the request method, URL, headers, and body — so
    ``requires_request_body`` is set to True to ensure the body is available
    at signing time.
    """

    requires_request_body = True

    def __init__(self, service: str = AGENTCORE_SERVICE, region: str = AGENTCORE_DEFAULT_REGION):
        """Initialise the SigV4 auth handler.

        Args:
            service: The AWS service name for signing (default: 'bedrock-agentcore').
            region: The AWS region for signing (default: 'eu-west-1').
        """
        self.service = service
        self.region = region
        self._session = BotocoreSession()

    def auth_flow(self, request: httpx.Request):
        """Sign the request with SigV4 and yield it.

        Resolves credentials fresh on each call so that temporary credentials
        (e.g. from IAM roles or SSO) are automatically refreshed.
        """
        # Resolve credentials (supports env vars, profiles, IAM roles, SSO)
        credentials = self._session.get_credentials()
        if credentials is None:
            raise RuntimeError(
                "No AWS credentials found. Configure credentials via environment "
                "variables (AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY), AWS CLI profiles, "
                "or IAM role."
            )
        frozen_credentials = credentials.get_frozen_credentials()

        # Build an AWSRequest for the signer
        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            headers={k: v for k, v in request.headers.items()},
            data=request.content or b"",
        )

        # Sign the request
        signer = SigV4Auth(frozen_credentials, self.service, self.region)
        signer.add_auth(aws_request)

        # Apply the signed headers back to the httpx request
        for header_name, header_value in aws_request.headers.items():
            request.headers[header_name] = header_value

        yield request


def extract_region_from_url(gateway_url: str) -> str:
    """Extract the AWS region from an AgentCore Gateway URL.

    Expected URL format:
        https://<name>.gateway.bedrock-agentcore.<region>.amazonaws.com/mcp

    Falls back to AGENTCORE_DEFAULT_REGION if the region cannot be parsed.

    Args:
        gateway_url: The full gateway URL.

    Returns:
        The extracted region string (e.g. 'eu-west-1').
    """
    try:
        hostname = urlparse(gateway_url).hostname or ""
        # Pattern: *.gateway.bedrock-agentcore.<region>.amazonaws.com
        parts = hostname.split(".")
        # Find 'bedrock-agentcore' and take the next part as region
        for i, part in enumerate(parts):
            if part == "bedrock-agentcore" and i + 1 < len(parts):
                return parts[i + 1]
    except Exception:
        pass

    return AGENTCORE_DEFAULT_REGION

SYSTEM_PROMPT = """You are a data analytics assistant for the D&A team.
Use the available tools to discover and query S3 Tables and Redshift data sources.
The Redshift database is analytics_db with tables in the public schema.
Always explain what data you found and present results clearly.
When asked to compare data across sources, query both and synthesise results."""


def load_agent_config() -> dict:
    """Load agent configuration from deploy/outputs/agent.json or environment.

    Resolution order:
      1. AGENTCORE_GATEWAY_URL environment variable (overrides file)
      2. deploy/outputs/agent.json file

    Returns:
        Dict with keys: 'gateway_url', 'model_id', 'agent_name'.
    """
    gateway_url = os.environ.get("AGENTCORE_GATEWAY_URL", "")
    model_id = os.environ.get("AGENTCORE_AGENT_MODEL", "")
    agent_name = os.environ.get("AGENTCORE_AGENT_NAME", "")

    # Try loading from file for any missing values
    if AGENT_FILE.exists():
        file_config = json.loads(AGENT_FILE.read_text())
        if not gateway_url:
            gateway_url = file_config.get("gateway_url", "")
        if not model_id:
            model_id = file_config.get("model_id", "")
        if not agent_name:
            agent_name = file_config.get("agent_name", "")

    # Defaults
    if not model_id:
        model_id = "anthropic.claude-sonnet-4-20250514"
    if not agent_name:
        agent_name = "da-analytics-agent"

    if not gateway_url:
        print(
            "\nError: Gateway URL not found.\n"
            "Either:\n"
            "  1. Run 'python -m deploy.deploy_agent' to generate deploy/outputs/agent.json\n"
            "  2. Set AGENTCORE_GATEWAY_URL environment variable\n",
            file=sys.stderr,
        )
        sys.exit(1)

    return {
        "gateway_url": gateway_url,
        "model_id": model_id,
        "agent_name": agent_name,
    }


def create_agent(config: dict) -> tuple:
    """Create a Strands Agent connected to the AgentCore Gateway via MCP.

    Configures the MCP client with SigV4 authentication so that all HTTP
    requests to the gateway are signed with AWS credentials (service:
    bedrock-agentcore).

    Args:
        config: Dict with 'gateway_url', 'model_id', 'agent_name'.

    Returns:
        Tuple of (agent, mcp_client) for lifecycle management.
    """
    gateway_url = config["gateway_url"]
    model_id = config["model_id"]

    logger.info(f"Connecting to gateway: {gateway_url}")
    logger.info(f"Using model: {model_id}")

    # Determine the region from the gateway URL for SigV4 signing
    region = extract_region_from_url(gateway_url)
    logger.info(f"SigV4 signing: service={AGENTCORE_SERVICE}, region={region}")

    # Create SigV4 auth handler for the AgentCore Gateway
    sigv4_auth = SigV4AuthFlow(service=AGENTCORE_SERVICE, region=region)

    # Create MCP client connected to the AgentCore Gateway with SigV4 auth
    mcp_client = MCPClient(
        lambda: streamablehttp_client(gateway_url, auth=sigv4_auth)
    )

    # Create Bedrock model
    model = BedrockModel(
        model_id=model_id,
        region_name=region,
    )

    # Create the Strands Agent
    agent = Agent(
        model=model,
        tools=[mcp_client],
        system_prompt=SYSTEM_PROMPT,
    )

    return agent, mcp_client


def list_available_tools(mcp_client: MCPClient) -> list[str]:
    """List tools available from the gateway and print them.

    Args:
        mcp_client: The connected MCP client.

    Returns:
        List of tool names.
    """
    try:
        tools = mcp_client.list_tools_sync()
        tool_names = [t.name for t in tools]

        if tool_names:
            print(f"\nDiscovered {len(tool_names)} tools from gateway:")
            for name in sorted(tool_names):
                print(f"  • {name}")
            print()
        else:
            print("\nNo tools discovered from gateway (targets may still be initialising).\n")

        return tool_names
    except Exception as e:
        logger.warning(f"Could not list tools: {e}")
        print(f"\nNote: Could not list tools at startup ({e}). Tools may still be available during queries.\n")
        return []


def run_single_query(agent: Agent, query: str) -> None:
    """Run a single query and print the response.

    Args:
        agent: The Strands Agent.
        query: The natural language query.
    """
    print(f"\nQuery: {query}\n")
    print("-" * 60)

    response = agent(query)
    print(f"\n{response}\n")


def run_interactive(agent: Agent) -> None:
    """Run the agent in interactive mode with an input loop.

    Supports:
      - 'exit' or 'quit' to leave
      - 'tools' to list available tools
      - Any other input is sent as a query
    """
    print("=" * 60)
    print("D&A Analytics Agent — Interactive Mode")
    print("=" * 60)
    print()
    print("Type your questions about S3 Tables or Redshift data.")
    print("Commands: 'exit' to quit, 'tools' to list available tools.")
    print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            print("\nGoodbye!")
            break

        if user_input.lower() == "tools":
            # Re-list tools (they may have changed)
            try:
                tools = agent.tool_registry.get_all_tools_config()
                print(f"\nAvailable tools ({len(tools)}):")
                for tool in tools:
                    name = tool.get("name", "unknown")
                    desc = tool.get("description", "")[:80]
                    print(f"  • {name}: {desc}")
                print()
            except Exception as e:
                print(f"\nCould not list tools: {e}\n")
            continue

        # Send query to agent
        print()
        try:
            response = agent(user_input)
            print(f"\nAgent: {response}\n")
        except KeyboardInterrupt:
            print("\n\n(Query interrupted)")
        except Exception as e:
            print(f"\nError: {e}\n")


def main() -> None:
    """Entry point for the D&A analytics demo agent."""
    parser = argparse.ArgumentParser(
        description="Interactive D&A analytics agent connected to AgentCore Gateway."
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Run a single query and exit (non-interactive mode).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load configuration
    config = load_agent_config()

    print(f"\nAgent: {config['agent_name']}")
    print(f"Model: {config['model_id']}")
    print(f"Gateway: {config['gateway_url']}")

    # Create agent and MCP client
    agent, mcp_client = create_agent(config)

    # Agent already initializes the MCP client during creation
    if args.query:
        # Single-shot mode
        run_single_query(agent, args.query)
    else:
        # Interactive mode
        run_interactive(agent)


if __name__ == "__main__":
    main()
