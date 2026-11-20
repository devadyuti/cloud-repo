#!/usr/bin/env bash
# End-to-end Device Farm run: project -> device pool -> uploads -> run -> poll.
# Idempotent: project and pool are reused (by name, cached in .demo_state.json).
#
# Env overrides:
#   PROJECT_NAME  (default: example-bank-devicefarm-demo)
#   POOL_NAME     (default: android-top3)
#   APP_PATH      (default: build/app-debug.apk, downloaded if missing)
#   BUNDLE_PATH   (default: build/test_bundle.zip, built if missing)
#   NO_WAIT=1     schedule the run and exit without polling
set -euo pipefail

export AWS_REGION=us-west-2 AWS_DEFAULT_REGION=us-west-2   # Device Farm only lives here
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$ROOT/.demo_state.json"
PROJECT_NAME="${PROJECT_NAME:-example-bank-devicefarm-demo}"
POOL_NAME="${POOL_NAME:-android-top3}"
APP_PATH="${APP_PATH:-$ROOT/build/app-debug.apk}"
BUNDLE_PATH="${BUNDLE_PATH:-$ROOT/build/test_bundle.zip}"
SPEC_PATH="$ROOT/testspec.yml"
SAMPLE_APK_URL="https://github.com/aws-samples/aws-device-farm-sample-app-for-android/raw/master/prebuilt/app-debug.apk"

df() { aws devicefarm "$@"; }
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

[[ -f "$STATE" ]] || echo '{}' > "$STATE"
state_get() { jq -r --arg k "$1" '.[$k] // empty' "$STATE"; }
state_set() { tmp=$(mktemp); jq --arg k "$1" --arg v "$2" '.[$k]=$v' "$STATE" > "$tmp" && mv "$tmp" "$STATE"; }

# ---- inputs -----------------------------------------------------------------
mkdir -p "$ROOT/build"
if [[ ! -f "$APP_PATH" ]]; then
  log "Building sample Android app (targetSdk 24) from $SAMPLE_APK_URL"
  "$ROOT/scripts/patch_apk.sh"
fi
[[ -f "$BUNDLE_PATH" ]] || "$ROOT/scripts/package.sh"

# ---- project ----------------------------------------------------------------
PROJECT_ARN="$(state_get project_arn)"
if [[ -z "$PROJECT_ARN" ]] || ! df get-project --arn "$PROJECT_ARN" >/dev/null 2>&1; then
  PROJECT_ARN=$(df list-projects --query "projects[?name=='$PROJECT_NAME'].arn | [0]" --output text)
  if [[ -z "$PROJECT_ARN" || "$PROJECT_ARN" == "None" ]]; then
    log "Creating project $PROJECT_NAME"
    PROJECT_ARN=$(df create-project --name "$PROJECT_NAME" \
      --default-job-timeout-minutes 10 --query project.arn --output text)
  fi
  state_set project_arn "$PROJECT_ARN"
fi
log "Project: $PROJECT_ARN"

# ---- device pool (max 3 highly available Android devices) -------------------
POOL_ARN="$(state_get pool_arn)"
if [[ -z "$POOL_ARN" ]] || ! df get-device-pool --arn "$POOL_ARN" >/dev/null 2>&1; then
  POOL_ARN=$(df list-device-pools --arn "$PROJECT_ARN" --type PRIVATE \
    --query "devicePools[?name=='$POOL_NAME'].arn | [0]" --output text)
  if [[ -z "$POOL_ARN" || "$POOL_ARN" == "None" ]]; then
    log "Creating device pool $POOL_NAME"
    POOL_ARN=$(df create-device-pool --project-arn "$PROJECT_ARN" --name "$POOL_NAME" \
      --max-devices 3 \
      --rules '[{"attribute":"PLATFORM","operator":"EQUALS","value":"\"ANDROID\""},
                {"attribute":"AVAILABILITY","operator":"EQUALS","value":"\"HIGHLY_AVAILABLE\""}]' \
      --query devicePool.arn --output text)
  fi
  state_set pool_arn "$POOL_ARN"
fi
log "Device pool: $POOL_ARN"

# ---- uploads ----------------------------------------------------------------
upload() {  # upload <file> <type> -> prints ARN once SUCCEEDED
  local file="$1" type="$2" arn url status
  read -r arn url < <(df create-upload --project-arn "$PROJECT_ARN" \
    --name "$(basename "$file")" --type "$type" \
    --query '[upload.arn, upload.url]' --output text)
  curl -sf -T "$file" "$url" >/dev/null
  for _ in $(seq 1 60); do
    status=$(df get-upload --arn "$arn" --query upload.status --output text)
    case "$status" in
      SUCCEEDED) echo "$arn"; return 0 ;;
      FAILED) log "Upload $type FAILED:" >&2
              df get-upload --arn "$arn" --query upload.metadata --output text >&2
              return 1 ;;
    esac
    sleep 5
  done
  log "Upload $type timed out" >&2; return 1
}

log "Uploading app, test bundle, testspec"
APP_ARN=$(upload "$APP_PATH" ANDROID_APP)
PKG_ARN=$(upload "$BUNDLE_PATH" APPIUM_PYTHON_TEST_PACKAGE)
SPEC_ARN=$(upload "$SPEC_PATH" APPIUM_PYTHON_TEST_SPEC)
log "Uploads SUCCEEDED"

# ---- schedule run -----------------------------------------------------------
RUN_NAME="demo-$(date +%Y%m%d-%H%M%S)"
RUN_ARN=$(df schedule-run --project-arn "$PROJECT_ARN" --app-arn "$APP_ARN" \
  --device-pool-arn "$POOL_ARN" --name "$RUN_NAME" \
  --test "type=APPIUM_PYTHON,testPackageArn=$PKG_ARN,testSpecArn=$SPEC_ARN" \
  --execution-configuration "jobTimeoutMinutes=10,videoCapture=true" \
  --query run.arn --output text)
state_set last_run_arn "$RUN_ARN"

PROJECT_ID="${PROJECT_ARN##*:project:}"
RUN_ID="${RUN_ARN##*/}"
CONSOLE_URL="https://us-west-2.console.aws.amazon.com/devicefarm/home?region=us-west-2#/mobile/projects/$PROJECT_ID/runs/$RUN_ID"
log "Run scheduled: $RUN_ARN"
log "Console: $CONSOLE_URL"

[[ "${NO_WAIT:-0}" == "1" ]] && exit 0

# ---- poll -------------------------------------------------------------------
while true; do
  read -r status result < <(df get-run --arn "$RUN_ARN" --query '[run.status, run.result]' --output text)
  log "Run status: $status ($result)"
  [[ "$status" == "COMPLETED" ]] && break
  sleep 20
done

echo
echo "=== Result: $result ==="
df get-run --arn "$RUN_ARN" --query 'run.counters' --output table
df list-jobs --arn "$RUN_ARN" \
  --query 'jobs[].{Device:device.name,OS:device.os,Result:result,Minutes:deviceMinutes.total}' \
  --output table
echo "Console: $CONSOLE_URL"
echo "Artifacts: scripts/fetch_results.sh $RUN_ARN"

[[ "$result" == "PASSED" ]]
