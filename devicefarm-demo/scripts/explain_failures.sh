#!/usr/bin/env bash
# Explain why a run failed, per device: Device Farm's suite message, each failed
# pytest test with its error (from junit.xml), plus the screenshot/video to show.
# Usage: explain_failures.sh [RUN_ARN]   (defaults to last run in .demo_state.json)
set -euo pipefail

export AWS_REGION=us-west-2 AWS_DEFAULT_REGION=us-west-2 AWS_PAGER=""
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN_ARN="${1:-$(jq -r '.last_run_arn // empty' "$ROOT/.demo_state.json" 2>/dev/null || true)}"
[[ -n "$RUN_ARN" ]] || { echo "Usage: $0 <run-arn>" >&2; exit 1; }
OUT="$ROOT/results/${RUN_ARN##*/}"
df() { aws devicefarm "$@" </dev/null; }

# Artifacts are needed for junit.xml; download once.
[[ -f "$OUT/devices.tsv" ]] || "$ROOT/scripts/fetch_results.sh" "$RUN_ARN" >/dev/null

df list-jobs --arn "$RUN_ARN" --query 'jobs[].[arn, device.name, device.os, result]' --output text |
while IFS=$'\t' read -r job device os result; do
  id=$(echo "$job" | cut -d/ -f3)
  echo "=== $device (Android $os): $result"
  [[ "$result" == "PASSED" ]] && { echo; continue; }

  # Device Farm's own view: which lifecycle suite failed and why.
  df list-suites --arn "$job" --query "suites[?result!='PASSED'].[name, message]" --output text |
    sed 's/^/  Device Farm: /'

  # pytest's view: failed tests and the first error line, from junit.xml.
  zip=$(ls "$OUT/$id"/file/Customer_Artifacts-*.zip 2>/dev/null | head -1 || true)
  if [[ -n "$zip" ]]; then
    unzip -p "$zip" '*junit.xml' 2>/dev/null | python3 -c '
import sys, xml.etree.ElementTree as ET
try:
    root = ET.fromstring(sys.stdin.read())
except ET.ParseError:
    sys.exit()
for tc in root.iter("testcase"):
    for bad in list(tc.findall("failure")) + list(tc.findall("error")):
        msg = (bad.get("message") or "").splitlines()[0][:110]
        print("  FAILED " + tc.get("name", "?") + ": " + msg)
'
  else
    echo "  (no junit.xml: tests did not start; see Test_spec_output below)"
  fi

  echo "  Show:"
  ls "$OUT/$id"/screenshot/*.png 2>/dev/null | sed 's/^/    screenshot /' || true
  ls "$OUT/$id"/file/Video-*.mp4 2>/dev/null | sed 's/^/    video      /' || true
  ls "$OUT/$id"/file/Test_spec_output-*.txt 2>/dev/null | sed 's/^/    log        /' || true
  echo
done
