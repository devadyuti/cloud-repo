#!/usr/bin/env bash
# Lightweight tests for run-share.sh command parsing.
# Validates each subcommand is recognised without making real AWS calls.
# We prepend a fake `aws` script to PATH so all aws CLI invocations are stubbed.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASS=0; FAIL=0

# Create a temporary stub for the aws CLI
STUB_DIR=$(mktemp -d)
cat > "$STUB_DIR/aws" <<'EOF'
#!/usr/bin/env bash
# Minimal stub for the aws CLI subcommands run-share.sh uses.
svc="${1:-}"; sub="${2:-}"
# If any arg asks for the namespace ARN, return a well-formed one.
for a in "$@"; do
  if [[ "$a" == *ClusterNamespaceArn* ]]; then
    echo "arn:aws:redshift:eu-west-1:123456789012:namespace:a2ba3a3f-bde1-4bda-ae84-70e95b20d0e8"
    exit 0
  fi
done
case "$svc" in
  redshift-data)
    case "$sub" in
      execute-statement)   echo "STUB_ID_123" ;;
      describe-statement)  echo "FINISHED" ;;
      get-statement-result) echo '[[{"longValue": 7}]]' ;;
    esac
    ;;
  redshift)
    case "$sub" in
      describe-clusters) echo '{"status":"available","type":"ra3.large","nodes":1}' ;;
      delete-cluster)    echo '{"id":"analytics-cluster","status":"deleting"}' ;;
      wait)              : ;;
      create-cluster)    echo '{"id":"analytics-cluster","status":"creating"}' ;;
    esac
    ;;
  *) echo "stub-noop" ;;
esac
exit 0
EOF
chmod +x "$STUB_DIR/aws"
export PATH="$STUB_DIR:$PATH"

cleanup() { rm -rf "$STUB_DIR"; }
trap cleanup EXIT

assert_exits_nonzero() {
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    ((FAIL++)); echo "  FAIL: $label (expected failure, got 0)"
  else
    ((PASS++)); echo "  PASS: $label"
  fi
}

assert_output_contains() {
  local label="$1"; local expected="$2"; shift 2
  local output
  output=$("$@" 2>&1) || true
  if echo "$output" | grep -qF "$expected"; then
    ((PASS++)); echo "  PASS: $label"
  else
    ((FAIL++)); echo "  FAIL: $label (expected '$expected' in output)"
  fi
}

echo "=== run-share.sh command dispatch tests ==="

assert_exits_nonzero   "unknown command rejected"                bash "$SCRIPT_DIR/run-share.sh" "bogus"
assert_output_contains "unknown command shows valid options"     "create-cluster" bash "$SCRIPT_DIR/run-share.sh" "bogus"
assert_output_contains "create-cluster accepted (exists branch)" "already exists" bash "$SCRIPT_DIR/run-share.sh" "create-cluster"
assert_output_contains "producer-ns prints producer GUID"        "0a84a6f2-df5c-42ff-a5c4-83c12b5b8f37" bash "$SCRIPT_DIR/run-share.sh" "producer-ns"
assert_output_contains "consumer-ns resolves consumer GUID"      "a2ba3a3f-bde1-4bda-ae84-70e95b20d0e8" bash "$SCRIPT_DIR/run-share.sh" "consumer-ns"
assert_output_contains "share command accepted"                  "datashare created" bash "$SCRIPT_DIR/run-share.sh" "share"
assert_output_contains "consume command accepted"                "mounted" bash "$SCRIPT_DIR/run-share.sh" "consume"
assert_output_contains "verify command accepted"                 "rows visible over the share" bash "$SCRIPT_DIR/run-share.sh" "verify"
assert_output_contains "live command accepted"                   "BEFORE producer insert" bash "$SCRIPT_DIR/run-share.sh" "live"
assert_output_contains "status command accepted"                 "outbound datashares" bash "$SCRIPT_DIR/run-share.sh" "status"
assert_output_contains "teardown command accepted"               "teardown complete" bash "$SCRIPT_DIR/run-share.sh" "teardown"

echo ""
echo "=== PROFILE env-var override tests ==="

# Test: default profile is demo-admin (verify the script's default value)
default_profile=$(bash -c 'unset PROFILE; eval "$(grep "^PROFILE=" "'"$SCRIPT_DIR"'/run-share.sh")"; echo "$PROFILE"')
if [ "$default_profile" = "demo-admin" ]; then
  ((PASS++)); echo "  PASS: PROFILE defaults to demo-admin"
else
  ((FAIL++)); echo "  FAIL: PROFILE defaults to demo-admin (got '$default_profile')"
fi

# Test: PROFILE env-var override works
override_profile=$(PROFILE=my-custom-profile bash -c 'eval "$(grep "^PROFILE=" "'"$SCRIPT_DIR"'/run-share.sh")"; echo "$PROFILE"')
if [ "$override_profile" = "my-custom-profile" ]; then
  ((PASS++)); echo "  PASS: PROFILE override accepted"
else
  ((FAIL++)); echo "  FAIL: PROFILE override accepted (got '$override_profile')"
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
