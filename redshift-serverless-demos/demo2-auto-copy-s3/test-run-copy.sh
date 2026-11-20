#!/usr/bin/env bash
# Lightweight tests for run-copy.sh command parsing.
# Validates that each subcommand is recognised without making real AWS calls.
# We prepend a fake `aws` script to PATH so all aws CLI invocations are stubbed.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PASS=0; FAIL=0

# Create a temporary stub for the aws CLI
STUB_DIR=$(mktemp -d)
cat > "$STUB_DIR/aws" <<'EOF'
#!/usr/bin/env bash
# Minimal stub: subcommands that run-copy.sh uses
case "${1:-}" in
  redshift-data)
    # execute-statement needs to return an ID
    if [[ "${2:-}" == "execute-statement" ]]; then
      echo "STUB_ID_123"
    elif [[ "${2:-}" == "describe-statement" ]]; then
      echo "FINISHED"
    elif [[ "${2:-}" == "get-statement-result" ]]; then
      echo '[[{"longValue": 42}]]'
    fi
    ;;
  s3)
    echo "upload: stub"
    ;;
  *)
    echo "stub-noop"
    ;;
esac
exit 0
EOF
chmod +x "$STUB_DIR/aws"
export PATH="$STUB_DIR:$PATH"

cleanup() { rm -rf "$STUB_DIR"; }
trap cleanup EXIT

# --- helpers ---

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

echo "=== run-copy.sh command dispatch tests ==="

# Test: unknown command exits non-zero
assert_exits_nonzero "unknown command rejected" bash "$SCRIPT_DIR/run-copy.sh" "bogus"

# Test: unknown command prints usage hint including 'status'
assert_output_contains "unknown command shows valid options" "status" bash "$SCRIPT_DIR/run-copy.sh" "bogus"

# Test: setup is accepted
assert_output_contains "setup command accepted" "table ready" bash "$SCRIPT_DIR/run-copy.sh" "setup"

# Test: status is accepted (new command)
assert_output_contains "status command accepted" "copy jobs registered" bash "$SCRIPT_DIR/run-copy.sh" "status"

# Test: verify is accepted
assert_output_contains "verify command accepted" "row count" bash "$SCRIPT_DIR/run-copy.sh" "verify"

# Test: load is accepted
assert_output_contains "load command accepted" "Uploading" bash "$SCRIPT_DIR/run-copy.sh" "load" "1"

# Test: whoami is accepted
assert_output_contains "whoami command accepted" "whoami" bash "$SCRIPT_DIR/run-copy.sh" "whoami"

# Test: sql is accepted (default query)
assert_output_contains "sql command accepted (default)" "sql" bash "$SCRIPT_DIR/run-copy.sh" "sql"

# Test: sql with custom query is accepted
assert_output_contains "sql command accepted (custom)" "sql" bash "$SCRIPT_DIR/run-copy.sh" "sql" "SELECT 42;"

# Test: reset is accepted
assert_output_contains "reset command accepted" "reset complete" bash "$SCRIPT_DIR/run-copy.sh" "reset"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
