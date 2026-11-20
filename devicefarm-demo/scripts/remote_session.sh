#!/usr/bin/env bash
# Remote access session helper (us-west-2).
#   remote_session.sh start   pick a device, install the app, open a session
#   remote_session.sh test    run the local pytest suite against the session's Appium endpoint
#   remote_session.sh stop    stop the session (billing stops)
# Env: DEVICE_NAME (substring match, e.g. "Pixel 9", default: first available Android)
#      APP_PATH (default build/app-debug.apk)
set -euo pipefail

export AWS_REGION=us-west-2 AWS_DEFAULT_REGION=us-west-2 AWS_PAGER=""
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="$ROOT/.demo_state.json"
APP_PATH="${APP_PATH:-$ROOT/build/app-debug.apk}"
df() { aws devicefarm --cli-read-timeout 30 "$@" </dev/null; }
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
[[ -f "$STATE" ]] || echo '{}' > "$STATE"
state_get() { jq -r --arg k "$1" '.[$k] // empty' "$STATE"; }
state_set() { tmp=$(mktemp); jq --arg k "$1" --arg v "$2" '.[$k]=$v' "$STATE" > "$tmp" && mv "$tmp" "$STATE"; }

start() {
  local project_arn device_arn device app_arn url status session_arn
  project_arn="$(state_get project_arn)"
  [[ -n "$project_arn" ]] || { echo "No project yet; run scripts/run_demo.sh first" >&2; exit 1; }
  [[ -f "$APP_PATH" ]] || "$ROOT/scripts/patch_apk.sh"

  read -r device_arn device < <(df list-devices \
    --filters 'attribute=PLATFORM,operator=EQUALS,values=ANDROID' \
              'attribute=REMOTE_ACCESS_ENABLED,operator=EQUALS,values=TRUE' \
              'attribute=AVAILABILITY,operator=EQUALS,values=HIGHLY_AVAILABLE' \
    --query "devices[?contains(name, '${DEVICE_NAME:-}')] | [0].[arn, join(' ', [name, 'Android', os])]" \
    --output text)
  [[ -n "$device_arn" && "$device_arn" != "None" ]] || { echo "No matching device" >&2; exit 1; }
  log "Device: $device"

  log "Uploading app"
  read -r app_arn url < <(df create-upload --project-arn "$project_arn" \
    --name "$(basename "$APP_PATH")" --type ANDROID_APP \
    --query '[upload.arn, upload.url]' --output text)
  curl -sf -T "$APP_PATH" "$url" >/dev/null
  until [[ "$(df get-upload --arn "$app_arn" --query upload.status --output text)" == SUCCEEDED ]]; do
    sleep 5
  done

  session_arn=$(df create-remote-access-session --project-arn "$project_arn" \
    --device-arn "$device_arn" --app-arn "$app_arn" --name "demo-remote-$(date +%H%M)" \
    --query remoteAccessSession.arn --output text)
  state_set remote_session_arn "$session_arn"
  log "Session: $session_arn"

  while true; do
    status=$(df get-remote-access-session --arn "$session_arn" \
      --query remoteAccessSession.status --output text)
    log "Status: $status"
    [[ "$status" == RUNNING ]] && break
    [[ "$status" == COMPLETED ]] && { echo "Session ended early" >&2; exit 1; }
    sleep 10
  done

  # --app-arn on create isn't always enough to have the app on the device; install explicitly.
  log "Installing app into session"
  df install-to-remote-access-session --remote-access-session-arn "$session_arn" \
    --app-arn "$app_arn" --query appUpload.status --output text >/dev/null

  state_set remote_driver_endpoint "$(df get-remote-access-session --arn "$session_arn" \
    --query remoteAccessSession.endpoints.remoteDriverEndpoint --output text)"
  echo
  echo "Session RUNNING on $device (billed per minute until stopped)."
  echo "Interact: console > Device Farm > Mobile device testing > ${project_arn##*:project:} > Remote access"
  echo "Automate: scripts/remote_session.sh test"
  echo "Stop:     scripts/remote_session.sh stop"
}

run_tests() {
  local endpoint venv="$ROOT/.venv"
  endpoint="$(state_get remote_driver_endpoint)"
  [[ -n "$endpoint" && "$endpoint" != "None" ]] || { echo "No session endpoint; run start" >&2; exit 1; }
  if [[ ! -x "$venv/bin/pytest" ]]; then
    python3.11 -m venv "$venv"
    "$venv/bin/pip" install -q -r "$ROOT/requirements.txt"
  fi
  # conftest.py uses its local path here: no udid/platformVersion (rejected by the endpoint),
  # app is already installed by the session.
  cd "$ROOT" && APPIUM_URL="$endpoint" "$venv/bin/pytest" tests -v
}

stop() {
  local arn
  arn="$(state_get remote_session_arn)"
  [[ -n "$arn" ]] || { echo "No session recorded" >&2; exit 1; }
  df stop-remote-access-session --arn "$arn" --query remoteAccessSession.status --output text
  state_set remote_session_arn ""
  state_set remote_driver_endpoint ""
}

case "${1:-}" in
  start) start ;;
  test) run_tests ;;
  stop) stop ;;
  *) echo "Usage: $0 start|test|stop" >&2; exit 1 ;;
esac
