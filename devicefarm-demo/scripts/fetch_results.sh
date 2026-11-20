#!/usr/bin/env bash
# Download all artifacts (video, logs, screenshots) for a Device Farm run.
# Usage: fetch_results.sh [RUN_ARN]   (defaults to last run in .demo_state.json)
set -euo pipefail

export AWS_REGION=us-west-2 AWS_DEFAULT_REGION=us-west-2
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN_ARN="${1:-$(jq -r '.last_run_arn // empty' "$ROOT/.demo_state.json" 2>/dev/null || true)}"
[[ -n "$RUN_ARN" ]] || { echo "Usage: $0 <run-arn>" >&2; exit 1; }

OUT="$ROOT/results/${RUN_ARN##*/}"
mkdir -p "$OUT"
echo "Downloading artifacts for $RUN_ARN -> $OUT"

for type in FILE SCREENSHOT LOG; do
  aws devicefarm list-artifacts --arn "$RUN_ARN" --type "$type" \
    --query 'artifacts[].[arn, name, extension, url]' --output text |
  while IFS=$'\t' read -r arn name ext url; do
    [[ -z "$url" || "$url" == "None" ]] && continue
    # Artifact ARN encodes project/run/job/suite/test; use the job id to group by device.
    job=$(echo "$arn" | cut -d/ -f3)
    dir="$OUT/$job/$(echo "$type" | tr '[:upper:]' '[:lower:]')"
    mkdir -p "$dir"
    file="$dir/$(echo "$name" | tr ' /' '__')-${arn##*/}.$ext"
    curl -sfL -o "$file" "$url" && echo "  $file"
  done
done

# Map job ids to device names for readability.
aws devicefarm list-jobs --arn "$RUN_ARN" \
  --query 'jobs[].[arn, device.name, result]' --output text |
  awk -F'\t' '{split($1,a,"/"); print a[3]"\t"$2"\t"$3}' > "$OUT/devices.tsv"
echo "Device map: $OUT/devices.tsv"
