#!/usr/bin/env bash
# Deploy DAGs to the MWAA S3 bucket.
# Usage: ./scripts/deploy_dags.sh [--dry-run]
#
# Syncs local dags/ folder to s3://<bucket>/dags/
# Also syncs requirements.txt if it has changed.

set -euo pipefail

REGION="eu-west-1"
BUCKET="any-company-mwaa-demo-dags-123456789012"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DAGS_DIR="$PROJECT_DIR/dags"

DRY_RUN=""
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN="--dryrun"
    echo "[DRY RUN] No files will be uploaded."
fi

echo "=== MWAA Classic DAG Deployment ==="
echo "Region:  $REGION"
echo "Bucket:  s3://$BUCKET"
echo "Source:  $DAGS_DIR"
echo ""

# Verify bucket exists
if ! aws s3 ls "s3://$BUCKET" --region "$REGION" > /dev/null 2>&1; then
    echo "ERROR: Bucket s3://$BUCKET not found or not accessible."
    exit 1
fi

# Refresh the dbt manifest Cosmos renders the dbt_anycompany_analytics DAG from.
# Falls back to the committed manifest if dbt isn't installed locally.
echo "--- Building dbt manifest ---"
if command -v "${DBT_BIN:-dbt}" > /dev/null 2>&1; then
    "$SCRIPT_DIR/build_dbt_manifest.sh"
else
    echo "WARN: dbt not found (set DBT_BIN) — deploying the committed manifest.json as-is."
fi
echo ""
# Sync DAGs (exclude __pycache__, .pyc, and local dbt run artifacts except the manifest)
echo "--- Syncing DAGs ---"
aws s3 sync "$DAGS_DIR" "s3://$BUCKET/dags/" \
    --region "$REGION" \
    --exclude "*__pycache__/*" \
    --exclude "*.pyc" \
    --exclude "dbt/*/logs/*" \
    --exclude "dbt/*/dbt_packages/*" \
    --exclude "dbt/*/target/*" \
    --include "dbt/*/target/manifest.json" \
    --exclude "serverless-workflows/*" \
    --exclude ".gitkeep" \
    --delete \
    $DRY_RUN

# Sync requirements.txt if present
REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
if [[ -f "$REQUIREMENTS_FILE" ]]; then
    echo ""
    echo "--- Syncing requirements.txt ---"
    aws s3 cp "$REQUIREMENTS_FILE" "s3://$BUCKET/requirements.txt" \
        --region "$REGION" \
        $DRY_RUN
fi

# Sync plugins if any exist (beyond .gitkeep)
PLUGINS_DIR="$PROJECT_DIR/plugins"
PLUGIN_COUNT=$(find "$PLUGINS_DIR" -type f ! -name ".gitkeep" 2>/dev/null | wc -l | tr -d ' ')
if [[ "$PLUGIN_COUNT" -gt 0 ]]; then
    echo ""
    echo "--- Syncing plugins ---"
    aws s3 sync "$PLUGINS_DIR" "s3://$BUCKET/plugins/" \
        --region "$REGION" \
        --exclude ".gitkeep" \
        $DRY_RUN
fi

echo ""
echo "=== Deployment complete ==="
echo ""
echo "DAGs will be picked up by MWAA within ~30 seconds."
echo "Check Airflow UI: aws mwaa create-web-login-token --name any-company-mwaa-demo --region $REGION"
