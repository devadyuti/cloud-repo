#!/usr/bin/env bats
#
# Tests for recreate_raw_tables.sh, focused on the --prefix / --set-prefix
# behavior and the live-crawler TablePrefix check.
#
# The script only touches AWS through `aws glue ...` and parses JSON with `jq`.
# We put a fake `aws` on PATH so the script runs fully offline and deterministic;
# the real `jq` is used. Each test can shape the fake crawler's reported
# TablePrefix via the AWS_FAKE_PREFIX env var, and the fake records every
# `aws glue` subcommand it sees to $AWS_CALL_LOG so we can assert on side
# effects (e.g. that update-crawler was or was not called).
#
# Run with: bats scripts/test_recreate_raw_tables.bats

setup() {
  SCRIPT="${BATS_TEST_DIRNAME}/recreate_raw_tables.sh"
  FAKE_BIN="$(mktemp -d)"
  AWS_CALL_LOG="$(mktemp)"
  export AWS_CALL_LOG

  # Fake `aws`. Only the `glue` subcommands the script uses are handled; every
  # invocation is appended to AWS_CALL_LOG. AWS_FAKE_PREFIX controls what
  # get-crawler reports as the live TablePrefix (default: raw_).
  cat > "${FAKE_BIN}/aws" <<'EOF'
#!/usr/bin/env bash
# Drop any leading "glue" and "--region <r>" tokens, then dispatch on subcommand.
args=("$@")
# Log the full glue subcommand (skip the literal "glue" and region flag).
printf '%s\n' "$*" >> "$AWS_CALL_LOG"

svc="$1"; shift || true       # "glue"
# strip an optional --region <value>
if [[ "${1:-}" == "--region" ]]; then shift 2; fi
sub="${1:-}"; shift || true

case "$sub" in
  get-database) exit 0 ;;
  get-crawler)
    # Answer based on --query.
    if printf '%s ' "$@" | grep -q 'Crawler.TablePrefix'; then
      echo "${AWS_FAKE_PREFIX:-raw_}"
    elif printf '%s ' "$@" | grep -q 'Crawler.State'; then
      echo "READY"
    else
      exit 0
    fi
    ;;
  get-tables)      echo '[]' ;;   # no stale tables to delete
  update-crawler)  exit 0 ;;
  batch-delete-table) exit 0 ;;
  start-crawler)   exit 0 ;;
  *) exit 0 ;;
esac
EOF
  chmod +x "${FAKE_BIN}/aws"

  # Ensure real jq is still reachable via the fake bin dir.
  ln -s "$(command -v jq)" "${FAKE_BIN}/jq"

  PATH="${FAKE_BIN}:${PATH}"
  export PATH
}

teardown() {
  rm -rf "${FAKE_BIN}" "${AWS_CALL_LOG}"
}

# --- Argument parsing --------------------------------------------------------

@test "help output documents --prefix and --set-prefix" {
  run bash "$SCRIPT" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--prefix"* ]]
  [[ "$output" == *"--set-prefix"* ]]
}

@test "unknown argument is still rejected" {
  run bash "$SCRIPT" --bogus
  [ "$status" -eq 2 ]
  [[ "$output" == *"Unknown argument: --bogus"* ]]
}

@test "--prefix and --set-prefix are accepted (no 'Unknown argument')" {
  AWS_FAKE_PREFIX="raw_" run bash "$SCRIPT" --prefix raw_ --set-prefix --dry-run --yes
  [ "$status" -eq 0 ]
  [[ "$output" != *"Unknown argument"* ]]
}

# --- Live prefix check -------------------------------------------------------

@test "matching live prefix proceeds without update-crawler" {
  AWS_FAKE_PREFIX="raw_" run bash "$SCRIPT" --dry-run --yes
  [ "$status" -eq 0 ]
  [[ "$output" == *"Live crawler TablePrefix: raw_"* ]]
  run grep -c 'update-crawler' "$AWS_CALL_LOG"
  [ "$output" -eq 0 ]
}

@test "prefix mismatch without --set-prefix aborts and does not update" {
  AWS_FAKE_PREFIX="None" run bash "$SCRIPT" --dry-run --yes
  [ "$status" -eq 1 ]
  [[ "$output" == *"WARNING"* ]]
  [[ "$output" == *"--set-prefix"* ]]
  run grep -c 'update-crawler' "$AWS_CALL_LOG"
  [ "$output" -eq 0 ]
}

@test "prefix mismatch with --set-prefix --dry-run reports the intended update but makes no change" {
  AWS_FAKE_PREFIX="None" run bash "$SCRIPT" --set-prefix --dry-run --yes
  [ "$status" -eq 0 ]
  [[ "$output" == *"[dry-run] Would update crawler"* ]]
  run grep -c 'update-crawler' "$AWS_CALL_LOG"
  [ "$output" -eq 0 ]
}

@test "prefix mismatch with --set-prefix (live) calls update-crawler with the prefix" {
  AWS_FAKE_PREFIX="None" run bash "$SCRIPT" --set-prefix --yes
  [ "$status" -eq 0 ]
  run grep 'update-crawler' "$AWS_CALL_LOG"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--table-prefix raw_"* ]]
}

@test "custom --prefix is used when updating the live crawler" {
  AWS_FAKE_PREFIX="None" run bash "$SCRIPT" --prefix stg_ --set-prefix --yes
  [ "$status" -eq 0 ]
  run grep 'update-crawler' "$AWS_CALL_LOG"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--table-prefix stg_"* ]]
}

@test "--project changes the crawler name that is queried" {
  AWS_FAKE_PREFIX="raw_" run bash "$SCRIPT" --project acme --dry-run --yes
  [ "$status" -eq 0 ]
  [[ "$output" == *"Crawler:  acme-raw-crawler"* ]]
}
