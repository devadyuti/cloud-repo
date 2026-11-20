#!/usr/bin/env bash
# verify_images.sh — Verify that MCP server container images are present in ECR.
#
# Usage:
#   ./deploy/verify_images.sh [--region eu-west-1] [--account-id 123456789012]
#
# This script checks that both S3 Tables and Redshift MCP server images
# have been pushed to ECR with the 'latest' tag. Run this after
# build_and_push.sh to confirm the images are ready for AgentCore deployment.
#
# Exit codes:
#   0 — Both images verified successfully
#   1 — One or both images are missing or an error occurred

set -euo pipefail

# ─── Defaults ────────────────────────────────────────────────────────────────

REGION="${AGENTCORE_REGION:-eu-west-1}"
ACCOUNT_ID="${AGENTCORE_ACCOUNT_ID:-}"
S3_TABLES_REPO_NAME="${AGENTCORE_S3_TABLES_REPO_NAME:-s3-tables-mcp-server}"
REDSHIFT_REPO_NAME="${AGENTCORE_REDSHIFT_REPO_NAME:-redshift-mcp-server}"
IMAGE_TAG="latest"
VERBOSE=false

# ─── Usage ───────────────────────────────────────────────────────────────────

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Verify MCP server container images are present in ECR with the expected tag.

Options:
  --account-id ID       AWS account ID (default: from AGENTCORE_ACCOUNT_ID or STS)
  --region REGION       AWS region (default: eu-west-1, or AGENTCORE_REGION env var)
  --tag TAG             Image tag to verify (default: latest)
  --verbose             Show detailed image metadata
  -h, --help            Show this help message

Environment variables:
  AGENTCORE_REGION                Override default region
  AGENTCORE_ACCOUNT_ID            Override account ID
  AGENTCORE_S3_TABLES_REPO_NAME   ECR repo name for S3 Tables (default: s3-tables-mcp-server)
  AGENTCORE_REDSHIFT_REPO_NAME    ECR repo name for Redshift (default: redshift-mcp-server)
EOF
    exit "${1:-0}"
}

# ─── Parse Arguments ─────────────────────────────────────────────────────────

while [[ $# -gt 0 ]]; do
    case "$1" in
        --account-id)
            ACCOUNT_ID="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage 0
            ;;
        *)
            echo "Error: Unknown option '$1'" >&2
            usage 1
            ;;
    esac
done

# ─── Resolve Account ID ─────────────────────────────────────────────────────

if [[ -z "$ACCOUNT_ID" ]]; then
    echo "  Resolving account ID from STS..."
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || true)
    if [[ -z "$ACCOUNT_ID" ]]; then
        echo "Error: Could not determine account ID. Provide --account-id or set AGENTCORE_ACCOUNT_ID." >&2
        exit 1
    fi
fi

# ─── Derived Values ──────────────────────────────────────────────────────────

ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "============================================"
echo " AgentCore MCP Server — Image Verification"
echo "============================================"
echo ""
echo "  Account ID:    ${ACCOUNT_ID}"
echo "  Region:        ${REGION}"
echo "  ECR Registry:  ${ECR_REGISTRY}"
echo "  Image Tag:     ${IMAGE_TAG}"
echo ""

# ─── Helper Function ─────────────────────────────────────────────────────────

PASS_COUNT=0
FAIL_COUNT=0

verify_image() {
    local repo_name="$1"
    local display_name="$2"

    echo "── Checking ${display_name} ──"
    echo "  Repository: ${repo_name}"
    echo "  Tag:        ${IMAGE_TAG}"

    # Check if repository exists
    if ! aws ecr describe-repositories \
        --repository-names "$repo_name" \
        --region "$REGION" \
        --output text > /dev/null 2>&1; then
        echo "  Status:     MISSING (repository does not exist)"
        echo "  Action:     Deploy the ECR CDK stack first, then run build_and_push.sh"
        echo ""
        FAIL_COUNT=$((FAIL_COUNT + 1))
        return
    fi

    # Check if image with tag exists
    local result
    result=$(aws ecr describe-images \
        --repository-name "$repo_name" \
        --region "$REGION" \
        --image-ids imageTag="$IMAGE_TAG" \
        --output json 2>&1) || true

    if echo "$result" | grep -q "ImageNotFoundException"; then
        echo "  Status:     MISSING (repository exists but image tag '${IMAGE_TAG}' not found)"
        echo "  Action:     Run build_and_push.sh to build and push the image"
        echo ""
        FAIL_COUNT=$((FAIL_COUNT + 1))
        return
    fi

    if echo "$result" | grep -q "RepositoryNotFoundException"; then
        echo "  Status:     MISSING (repository does not exist)"
        echo "  Action:     Deploy the ECR CDK stack first, then run build_and_push.sh"
        echo ""
        FAIL_COUNT=$((FAIL_COUNT + 1))
        return
    fi

    # Image found — extract metadata
    local image_digest pushed_at image_size
    image_digest=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['imageDetails'][0].get('imageDigest','unknown'))" 2>/dev/null || echo "unknown")
    pushed_at=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['imageDetails'][0].get('imagePushedAt','unknown'))" 2>/dev/null || echo "unknown")
    image_size=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); size=d['imageDetails'][0].get('imageSizeInBytes',0); print(f'{size/1024/1024:.1f} MB')" 2>/dev/null || echo "unknown")

    echo "  Status:     PRESENT"
    echo "  Digest:     ${image_digest}"
    echo "  Pushed At:  ${pushed_at}"
    echo "  Size:       ${image_size}"

    if [[ "$VERBOSE" == "true" ]]; then
        local scan_status
        scan_status=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['imageDetails'][0].get('imageScanStatus',{}).get('status','not scanned'))" 2>/dev/null || echo "unknown")
        echo "  Scan:       ${scan_status}"
    fi

    echo "  Image URI:  ${ECR_REGISTRY}/${repo_name}:${IMAGE_TAG}"
    echo ""
    PASS_COUNT=$((PASS_COUNT + 1))
}

# ─── Verify Both Images ─────────────────────────────────────────────────────

verify_image "$S3_TABLES_REPO_NAME" "S3 Tables MCP Server"
verify_image "$REDSHIFT_REPO_NAME" "Redshift MCP Server"

# ─── Summary ─────────────────────────────────────────────────────────────────

echo "============================================"
echo " Verification Summary"
echo "============================================"
echo ""
echo "  Passed: ${PASS_COUNT}/2"
echo "  Failed: ${FAIL_COUNT}/2"
echo ""

if [[ $FAIL_COUNT -gt 0 ]]; then
    echo "  Some images are not yet available. To resolve:"
    echo ""
    echo "  1. Ensure the ECR CDK stack is deployed:"
    echo "       cd infra && cdk deploy AgentCoreMCPDemo-ECR"
    echo ""
    echo "  2. Build and push the images:"
    echo "       ./deploy/build_and_push.sh --account-id ${ACCOUNT_ID} --region ${REGION}"
    echo ""
    echo "  3. Re-run this verification:"
    echo "       ./deploy/verify_images.sh"
    echo ""
    exit 1
else
    echo "  All images verified. Ready to deploy AgentCore runtimes."
    echo ""
    echo "  Next step: python deploy/deploy_runtimes.py"
    echo ""
    exit 0
fi
