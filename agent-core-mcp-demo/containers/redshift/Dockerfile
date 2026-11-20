# AgentCore Runtime wrapper for Redshift MCP Server
# Extends the base image with streamable HTTP transport + disabled DNS rebinding protection
FROM redshift-mcp-server:latest

USER root
COPY entrypoint.py /app/entrypoint.py
RUN chown app:app /app/entrypoint.py
USER app

ENTRYPOINT ["/app/.venv/bin/python", "/app/entrypoint.py"]
