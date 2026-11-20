#!/usr/bin/env bash
# R2 verification: invoke the deployed runtime, then confirm OpenTelemetry spans
# actually reached CloudWatch (per-agent 'spans' stream) and X-Ray Transaction Search.
#
# Usage:
#   AWS_PROFILE=default AWS_REGION=eu-west-1 ./verify_traces.sh
#
# Reads the runtime ARN from ../agent/runtime_config.json (written by deploy.py).
set -euo pipefail

: "${AWS_PROFILE:=default}"
: "${AWS_REGION:=eu-west-1}"
export AWS_PROFILE AWS_REGION AWS_PAGER=""

CFG="$(dirname "$0")/../agent/runtime_config.json"
[ -f "$CFG" ] || { echo "runtime_config.json not found — run deploy.py first"; exit 1; }

ARN=$(python3 -c "import json,sys;print(json.load(open('$CFG'))['runtime_arn'])")
RID=$(python3 -c "import json,sys;print(json.load(open('$CFG'))['runtime_id'])")
echo "Runtime: $RID"

echo "== invoking =="
for q in "What is the weather in Athens?" "What is 12 * 34?"; do
  B64=$(printf '{"prompt":"%s"}' "$q" | base64)
  OUT=$(mktemp)
  SC=$(aws bedrock-agentcore invoke-agent-runtime \
        --agent-runtime-arn "$ARN" --payload "$B64" \
        --content-type application/json --region "$AWS_REGION" "$OUT" \
        --query statusCode --output text)
  echo "  [$SC] $q -> $(cat "$OUT")"; rm -f "$OUT"
done

echo "== waiting 90s for span export =="
sleep 90

LG="/aws/bedrock-agentcore/runtimes/${RID}-DEFAULT"
echo "== spans stream ($LG) =="
aws logs describe-log-streams --log-group-name "$LG" \
  --log-stream-name-prefix spans --region "$AWS_REGION" \
  --query 'logStreams[].{name:logStreamName,lastEvent:lastEventTimestamp}' --output json || true

echo "== X-Ray trace summaries (last 10m) =="
START=$(python3 -c "import time;print(int(time.time()-600))")
END=$(python3 -c "import time;print(int(time.time()))")
aws xray get-trace-summaries --start-time "$START" --end-time "$END" \
  --region "$AWS_REGION" --query 'TraceSummaries[].[Id,Duration]' --output text || true

echo
echo "If the spans stream shows a non-null lastEvent and X-Ray lists trace IDs,"
echo "R2 is satisfied. View them in CloudWatch > GenAI Observability."
