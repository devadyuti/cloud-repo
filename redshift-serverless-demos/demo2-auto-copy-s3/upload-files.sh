#!/usr/bin/env bash
# Upload a demo batch file to the S3 prefix the COPY JOB watches.
# Run this AFTER the COPY JOB has been created (files must be newer than the job).
#
# Usage:
#   export DEMO_BUCKET=any-company-demo-autocopy-<suffix>
#   export AWS_REGION=eu-west-1
#   ./upload-files.sh 1     # uploads transactions_batch_01.csv
#   ./upload-files.sh 2     # uploads transactions_batch_02.csv
#
# Then run 03-run-and-verify.sql in Query Editor v2.

set -euo pipefail

BATCH="${1:-1}"
PREFIX="${DEMO_PREFIX:-any-company-demo/auto-copy/incoming}"
REGION="${AWS_REGION:-eu-west-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${DEMO_BUCKET:-}" ]]; then
  echo "ERROR: set DEMO_BUCKET first (export DEMO_BUCKET=your-bucket-name)" >&2
  exit 1
fi

case "$BATCH" in
  1) FILE="transactions_batch_01.csv" ;;
  2) FILE="transactions_batch_02.csv" ;;
  *) echo "ERROR: batch must be 1 or 2" >&2; exit 1 ;;
esac

SRC="$SCRIPT_DIR/sample-data/$FILE"
DEST="s3://$DEMO_BUCKET/$PREFIX/$FILE"

echo "Uploading $FILE -> $DEST (region $REGION)"
aws s3 cp "$SRC" "$DEST" --region "$REGION"
echo "Done. Now run 03-run-and-verify.sql (COPY JOB RUN) in Query Editor v2."
