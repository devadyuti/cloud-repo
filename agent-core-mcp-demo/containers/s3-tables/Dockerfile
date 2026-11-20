# AgentCore Runtime wrapper for S3 Tables MCP Server
# Extends the base image with streamable HTTP transport + disabled DNS rebinding protection
FROM s3-tables-mcp-server:latest

USER root
COPY entrypoint.py /app/entrypoint.py
RUN chown app:app /app/entrypoint.py
USER app

ENTRYPOINT ["/app/.venv/bin/python", "/app/entrypoint.py"]
