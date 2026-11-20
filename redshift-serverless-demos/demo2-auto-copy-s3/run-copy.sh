#!/usr/bin/env bash
# Orchestrates Demo 2 via the Redshift Data API (no Query Editor needed).
# Steps: create landing table -> create COPY JOB -> upload a batch -> COPY JOB RUN -> verify.
#
# Usage:
#   bash run-copy.sh setup      # create table + copy job
#   bash run-copy.sh load 1     # upload batch 1, run job, show count
#   bash run-copy.sh load 2     # upload batch 2, run job, show count
#   bash run-copy.sh status     # show registered copy jobs + row count
#   bash run-copy.sh verify     # show count + system views
#   bash run-copy.sh reset      # drop job + truncate table + clear S3 files

set -uo pipefail

PROFILE="amplify-dev"
REGION="eu-west-1"
WORKGROUP="default-workgroup"
DATABASE="dev"
BUCKET="any-company-demo-autocopy-123456789012"
PREFIX="any-company-demo/auto-copy/incoming"
ROLE_ARN="arn:aws:iam::123456789012:role/any-company-demo-autocopy-role"
JOB="anycompany_autocopy_txns"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_sql() {
  local label="$1"; local sql="$2"
  local id
  id=$(aws redshift-data execute-statement --workgroup-name "$WORKGROUP" --database "$DATABASE" \
        --sql "$sql" --profile "$PROFILE" --region "$REGION" --query 'Id' --output text)
  local st
  while true; do
    st=$(aws redshift-data describe-statement --id "$id" --profile "$PROFILE" --region "$REGION" --query 'Status' --output text)
    case "$st" in FINISHED|FAILED|ABORTED) break;; esac
    sleep 2
  done
  echo "[$label] STATUS=$st (id=$id)"
  if [ "$st" = "FAILED" ]; then
    aws redshift-data describe-statement --id "$id" --profile "$PROFILE" --region "$REGION" --query 'Error' --output text
    return 1
  fi
  echo "$id"
}

show_result() {
  local label="$1"; local sql="$2"
  local id
  id=$(run_sql "$label" "$sql" | tail -n1)
  aws redshift-data get-statement-result --id "$id" --profile "$PROFILE" --region "$REGION" \
    --query 'Records' --output json
}

cmd="${1:-setup}"

case "$cmd" in
  setup)
    run_sql "create-table" "CREATE TABLE IF NOT EXISTS anycompany_demo.transactions_incoming (transaction_id INTEGER NOT NULL, member_id INTEGER NOT NULL, merchant_id INTEGER NOT NULL, txn_ts TIMESTAMP, amount DECIMAL(10,2), cashback_earned DECIMAL(10,2), channel VARCHAR(20));" >/dev/null && echo "table ready"
    run_sql "create-copy-job" "COPY anycompany_demo.transactions_incoming FROM 's3://$BUCKET/$PREFIX/' IAM_ROLE '$ROLE_ARN' FORMAT AS CSV IGNOREHEADER 1 TIMEFORMAT 'auto' JOB CREATE $JOB AUTO ON;" >/dev/null && echo "copy job created: $JOB"
    ;;
  load)
    batch="${2:-1}"
    file="transactions_batch_0${batch}.csv"
    echo "Uploading $file -> s3://$BUCKET/$PREFIX/$file"
    aws s3 cp "$SCRIPT_DIR/sample-data/$file" "s3://$BUCKET/$PREFIX/$file" --profile "$PROFILE" --region "$REGION"
    run_sql "copy-job-run" "COPY JOB RUN $JOB;" >/dev/null && echo "job run submitted"
    sleep 3
    echo "--- row count ---"
    show_result "count" "SELECT COUNT(*) AS rows_loaded FROM anycompany_demo.transactions_incoming;"
    ;;
  status)
    echo "--- copy jobs registered (sys_copy_job) ---"
    show_result "jobs" "SELECT * FROM sys_copy_job;"
    ;;
  whoami)
    show_result "whoami" "SELECT current_user AS db_user, current_database() AS db;"
    ;;
  sql)
    show_result "sql" "${2:-SELECT 1;}"
    ;;
  verify)
    echo "--- row count ---"
    show_result "count" "SELECT COUNT(*) AS rows_loaded FROM anycompany_demo.transactions_incoming;"
    echo "--- load history ---"
    show_result "load-history" "SELECT table_name, data_source, loaded_rows, status FROM sys_load_history ORDER BY start_time DESC LIMIT 10;"
    ;;
  reset)
    run_sql "drop-job" "COPY JOB DROP $JOB;" >/dev/null && echo "job dropped" || echo "job may not exist"
    run_sql "truncate" "TRUNCATE anycompany_demo.transactions_incoming;" >/dev/null && echo "table truncated"
    aws s3 rm "s3://$BUCKET/$PREFIX/" --recursive --profile "$PROFILE" --region "$REGION"
    echo "reset complete"
    ;;
  *)
    echo "Unknown command: $cmd (use setup|load|status|whoami|sql|verify|reset)"; exit 1 ;;
esac
