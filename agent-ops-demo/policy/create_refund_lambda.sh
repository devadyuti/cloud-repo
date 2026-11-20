#!/usr/bin/env bash
# R3 setup: create the synthetic process_refund Lambda that backs the gateway
# target. Idempotent-ish: re-running updates the function code.
#
# Usage (with materialized creds or a working profile):
#   AWS_REGION=eu-west-1 ./create_refund_lambda.sh
#
# Prints the Lambda ARN on success — feed it to `agentcore add gateway-target`.
set -euo pipefail

: "${AWS_REGION:=eu-west-1}"
export AWS_REGION AWS_PAGER=""

FN_NAME="agentops-process-refund"
ROLE_NAME="agentops-refund-lambda-role"
HERE="$(cd "$(dirname "$0")" && pwd)"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

echo "Account: $ACCOUNT  Region: $AWS_REGION"

# 1) Execution role (basic Lambda logging only — synthetic, no other perms)
TRUST='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
if ! aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE_NAME" \
    --assume-role-policy-document "$TRUST" \
    --description "AgentOps demo synthetic refund Lambda" >/dev/null
  aws iam attach-role-policy --role-name "$ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
  echo "Created role $ROLE_NAME; waiting 10s for propagation..."
  sleep 10
else
  echo "Role $ROLE_NAME exists."
fi
ROLE_ARN="arn:aws:iam::${ACCOUNT}:role/${ROLE_NAME}"

# 2) Package the handler
TMP=$(mktemp -d)
cp "$HERE/refund_lambda.py" "$TMP/refund_lambda.py"
( cd "$TMP" && zip -q refund_lambda.zip refund_lambda.py )

# 3) Create or update the function
if aws lambda get-function --function-name "$FN_NAME" >/dev/null 2>&1; then
  echo "Updating existing function $FN_NAME..."
  aws lambda update-function-code --function-name "$FN_NAME" \
    --zip-file "fileb://$TMP/refund_lambda.zip" >/dev/null
else
  echo "Creating function $FN_NAME..."
  aws lambda create-function --function-name "$FN_NAME" \
    --runtime python3.12 --handler refund_lambda.handler \
    --role "$ROLE_ARN" \
    --zip-file "fileb://$TMP/refund_lambda.zip" \
    --timeout 10 --memory-size 128 \
    --description "AgentOps demo — synthetic process_refund tool (no money moved)" >/dev/null
fi

rm -rf "$TMP"
FN_ARN=$(aws lambda get-function --function-name "$FN_NAME" --query 'Configuration.FunctionArn' --output text)
echo
echo "Lambda ARN: $FN_ARN"
echo "Next: agentcore add gateway-target --type lambda-function-arn --lambda-arn $FN_ARN ..."
