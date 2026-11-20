#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────
# test-pipeline.sh — End-to-end test for S3→EventBridge→Glue
# Uploads sample CSV, waits for Glue job, verifies Parquet output.
# ─────────────────────────────────────────────────────────────

REGION="eu-west-1"
STACK_NAME="S3EventBridgeGluePipelineStack"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔍 Fetching stack outputs..."
SOURCE_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='SourceBucketName'].OutputValue" \
  --output text)

TARGET_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='TargetBucketName'].OutputValue" \
  --output text)

GLUE_JOB=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='GlueJobName'].OutputValue" \
  --output text)

echo "  Source bucket: $SOURCE_BUCKET"
echo "  Target bucket: $TARGET_BUCKET"
echo "  Glue job:      $GLUE_JOB"
echo ""

# ─────────────────────────────────────────────────────────────
# Step 1: Upload sample CSV
# ─────────────────────────────────────────────────────────────
CSV_FILE="$PROJECT_DIR/test-data/sample-orders.csv"
ROW_COUNT=$(wc -l < "$CSV_FILE" | tr -d ' ')
echo "📤 Uploading sample-orders.csv ($ROW_COUNT lines) to s3://$SOURCE_BUCKET/input/..."
aws s3 cp "$CSV_FILE" \
  "s3://$SOURCE_BUCKET/input/sample-orders.csv" \
  --region "$REGION"
echo "   Done."
echo ""

# ─────────────────────────────────────────────────────────────
# Step 2: Wait for Glue job to start and complete
# ─────────────────────────────────────────────────────────────
echo "⏳ Waiting for Glue job to start (EventBridge propagation ~10-30s)..."
sleep 30

echo "🔎 Checking latest Glue job run..."
MAX_ATTEMPTS=20
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  ATTEMPT=$((ATTEMPT + 1))

  RUN_STATUS=$(aws glue get-job-runs \
    --job-name "$GLUE_JOB" \
    --region "$REGION" \
    --max-items 1 \
    --query "JobRuns[0].JobRunState" \
    --output text 2>/dev/null || echo "NONE")

  echo "   Attempt $ATTEMPT/$MAX_ATTEMPTS — Status: $RUN_STATUS"

  if [ "$RUN_STATUS" = "SUCCEEDED" ]; then
    echo "✅ Glue job completed successfully!"
    break
  elif [ "$RUN_STATUS" = "FAILED" ] || [ "$RUN_STATUS" = "ERROR" ] || [ "$RUN_STATUS" = "TIMEOUT" ]; then
    echo "❌ Glue job failed with status: $RUN_STATUS"
    echo "   Check the Glue console for error details."
    exit 1
  elif [ "$RUN_STATUS" = "NONE" ]; then
    echo "   No job run found yet. Waiting..."
  fi

  sleep 15
done

if [ "$RUN_STATUS" != "SUCCEEDED" ]; then
  echo "❌ Timed out waiting for Glue job to complete."
  exit 1
fi

echo ""

# ─────────────────────────────────────────────────────────────
# Step 3: Verify Parquet output
# ─────────────────────────────────────────────────────────────
echo "📂 Checking for Parquet output in s3://$TARGET_BUCKET/output/sample-orders/..."
OUTPUT_FILES=$(aws s3 ls "s3://$TARGET_BUCKET/output/sample-orders/" --region "$REGION" 2>/dev/null || echo "")

if [ -n "$OUTPUT_FILES" ]; then
  echo "✅ Parquet files found:"
  echo "$OUTPUT_FILES" | sed 's/^/   /'
else
  echo "❌ No output files found. Check the Glue job logs."
  exit 1
fi

echo ""
echo "🎉 Pipeline test completed successfully!"
echo ""
echo "Next steps:"
echo "  • View Parquet: aws s3 ls s3://$TARGET_BUCKET/output/sample-orders/ --region $REGION"
echo "  • Query with Athena: Create a Glue Crawler on s3://$TARGET_BUCKET/output/"
echo "  • Check DLQ: aws sqs get-queue-attributes --queue-url <dlq-url> --attribute-names ApproximateNumberOfMessages"
