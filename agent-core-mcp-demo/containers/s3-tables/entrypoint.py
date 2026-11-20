#!/usr/bin/env python3
"""AgentCore Runtime wrapper for S3 Tables MCP Server.

Runs the S3 Tables MCP server with streamable HTTP transport on 0.0.0.0:8000.
Disables DNS rebinding protection for AgentCore Runtime compatibility
(AgentCore routes requests via internal hostnames).
"""
import os
from mcp.server.transport_security import TransportSecuritySettings
from awslabs.s3_tables_mcp_server.server import app

# Enable write mode if requested via env var
if os.environ.get("ALLOW_WRITE", "").lower() in ("true", "1", "yes"):
    app.allow_write = True

# Configure for AgentCore Runtime
app.settings.host = "0.0.0.0"
app.settings.port = 8000
app.settings.stateless_http = True
app.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False
)

# Run with streamable HTTP transport
app.run(transport="streamable-http")
