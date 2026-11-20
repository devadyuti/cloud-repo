# Starter agent (extracted)

This is the **workshop starter agent** we observe in the AgentOps demo — reused
as-is, not rebuilt. `agent.py` here is byte-for-byte the code extracted from the
deployed runtime's `code.zip`.

## What it is
- Framework: **Strands Agents** (`BedrockAgentCoreApp` entrypoint).
- Model: `global.anthropic.claude-haiku-4-5-20251001-v1:0` (EU/global inference profile).
- Tools: `weather` (custom) and `calculator` (from `strands_tools`).
- Input contract: `{"prompt": "<text>"}`.

## Source of truth
Extracted from the already-deployed runtime:
- Runtime ARN: `arn:aws:bedrock-agentcore:eu-west-1:123456789012:runtime/strands_bedrock_2847-rc30j0EnVr`
- Code artifact: `s3://agentcore-code-123456789012-eu-west-1/strands_bedrock_2847/code.zip`
- Type: **CodeConfiguration** (S3 code.zip, `entryPoint: agent.py`, PYTHON_3_13)

## Why requirements.txt adds ADOT
The deployed package was built **without** an active OpenTelemetry exporter, so the
runtime's `spans` / `otel-rt-logs` CloudWatch streams stay empty and no traces reach
X-Ray — even with `AGENT_OBSERVABILITY_ENABLED=true` set on the runtime.

`aws-opentelemetry-distro>=0.18.0` in `requirements.txt` lets AgentCore
auto-instrument the runtime and export Strands' spans to CloudWatch Transaction
Search. **The agent logic is unchanged** — only the observability dependency is added.

## Redeploy (observability-enabled)
From this folder, with the AgentCore starter toolkit:

```bash
export AWS_PROFILE=default AWS_REGION=eu-west-1
agentcore configure --entrypoint agent.py    # Strands / HTTP runtime
agentcore launch                             # builds with requirements.txt, sets OTEL
```

The toolkit launches the container under `opentelemetry-instrument` and sets
`AGENT_OBSERVABILITY_ENABLED=true` automatically when the ADOT distro is present.

## Account-level prerequisite (already done)
CloudWatch Transaction Search is enabled in this account/region:
- `logs put-resource-policy` granting `xray.amazonaws.com` → `logs:PutLogEvents` on `aws/spans`
- `xray update-trace-segment-destination --destination CloudWatchLogs`
- `xray update-indexing-rule --name Default --rule '{"Probabilistic":{"DesiredSamplingPercentage":100}}'`
