#!/usr/bin/env bash
# build_and_push.sh — Build and push S3 Tables and Redshift MCP server images to ECR.
#
# Usage:
#   ./deploy/build_and_push.sh --account-id 123456789012 [--region eu-west-1] [--mcp-repo-dir ./mcp]
#
# This script:
#   1. Clones the awslabs/mcp repo (or reuses an existing clone)
#   2. Builds Docker images for S3 Tables and Redshift MCP servers
#   3. Authenticates with ECR
#   4. Tags and pushes both images to their respective ECR repositories

set -euo pipefail

# ─── Defaults ────────────────────────────────────────────────────────────────

REGION="${AGENTCORE_REGION:-eu-west-1}"
ACCOUNT_ID="${AGENTCORE_ACCOUNT_ID:-}"
MCP_REPO_DIR=""
MCP_REPO_URL="https://github.com/awslabs/mcp.git"
S3_TABLES_REPO_NAME="${AGENTCORE_S3_TABLES_REPO_NAME:-s3-tables-mcp-server}"
REDSHIFT_REPO_NAME="${AGENTCORE_REDSHIFT_REPO_NAME:-redshift-mcp-server}"
IMAGE_TAG="latest"

# ─── Usage ───────────────────────────────────────────────────────────────────

usage() {
    cat <<EOF
Usage: $(basename "$0") --account-id ACCOUNT_ID [OPTIONS]

Build and push MCP server Docker images to ECR.

Required:
  --account-id ID       AWS account ID for ECR

Options:
  --region REGION       AWS region (default: eu-west-1, or AGENTCORE_REGION env var)
  --mcp-repo-dir DIR    Path to existing awslabs/mcp clone (default: ./mcp in script dir)
  --tag TAG             Image tag (default: latest)
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
        --mcp-repo-dir)
            MCP_REPO_DIR="$2"
            shift 2
            ;;
        --tag)
            IMAGE_TAG="$2"
            shift 2
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

# ─── Validate Parameters ────────────────────────────────────────────────────

if [[ -z "$ACCOUNT_ID" ]]; then
    echo "Error: --account-id is required (or set AGENTCORE_ACCOUNT_ID env var)" >&2
    usage 1
fi

if [[ -z "$REGION" ]]; then
    echo "Error: --region is required (or set AGENTCORE_REGION env var)" >&2
    usage 1
fi

# Verify Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH" >&2
    exit 1
fi

# Verify AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed or not in PATH" >&2
    exit 1
fi

# ─── Derived Values ──────────────────────────────────────────────────────────

ECR_REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
S3_TABLES_IMAGE_URI="${ECR_REGISTRY}/${S3_TABLES_REPO_NAME}:${IMAGE_TAG}"
REDSHIFT_IMAGE_URI="${ECR_REGISTRY}/${REDSHIFT_REPO_NAME}:${IMAGE_TAG}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default MCP repo location: alongside the project root
if [[ -z "$MCP_REPO_DIR" ]]; then
    MCP_REPO_DIR="${PROJECT_ROOT}/mcp"
fi

echo "============================================"
echo " AgentCore MCP Server — Build & Push"
echo "============================================"
echo ""
echo "  Account ID:    ${ACCOUNT_ID}"
echo "  Region:        ${REGION}"
echo "  ECR Registry:  ${ECR_REGISTRY}"
echo "  S3 Tables:     ${S3_TABLES_IMAGE_URI}"
echo "  Redshift:      ${REDSHIFT_IMAGE_URI}"
echo "  MCP Repo Dir:  ${MCP_REPO_DIR}"
echo ""

# ─── Step 1: Clone or reuse MCP repository ──────────────────────────────────

echo "── Step 1: Preparing awslabs/mcp repository ──"

if [[ -d "${MCP_REPO_DIR}/.git" ]]; then
    echo "  Found existing clone at ${MCP_REPO_DIR}"
    echo "  Pulling latest changes..."
    git -C "$MCP_REPO_DIR" pull --ff-only || echo "  Warning: pull failed, using existing state"
else
    echo "  Cloning ${MCP_REPO_URL} to ${MCP_REPO_DIR}..."
    git clone --depth 1 "$MCP_REPO_URL" "$MCP_REPO_DIR"
fi

# Verify expected source directories exist
if [[ ! -d "${MCP_REPO_DIR}/src/s3-tables-mcp-server" ]]; then
    echo "Error: src/s3-tables-mcp-server not found in ${MCP_REPO_DIR}" >&2
    exit 1
fi

if [[ ! -d "${MCP_REPO_DIR}/src/redshift-mcp-server" ]]; then
    echo "Error: src/redshift-mcp-server not found in ${MCP_REPO_DIR}" >&2
    exit 1
fi

echo "  MCP repository ready."
echo ""

# ─── Step 2: Build Docker images ────────────────────────────────────────────

echo "── Step 2: Building Docker images ──"

echo "  Building S3 Tables MCP server image..."
docker build \
    -t "${S3_TABLES_REPO_NAME}:${IMAGE_TAG}" \
    -f "${MCP_REPO_DIR}/src/s3-tables-mcp-server/Dockerfile" \
    "${MCP_REPO_DIR}/src/s3-tables-mcp-server"

echo "  Building Redshift MCP server image..."
docker build \
    -t "${REDSHIFT_REPO_NAME}:${IMAGE_TAG}" \
    -f "${MCP_REPO_DIR}/src/redshift-mcp-server/Dockerfile" \
    "${MCP_REPO_DIR}/src/redshift-mcp-server"

echo "  Both images built successfully."
echo ""

# ─── Step 2b: Build AgentCore wrapper images ─────────────────────────────────

echo "── Step 2b: Building AgentCore Runtime wrapper images ──"

# The wrapper builds override the base image tags, adding streamable HTTP transport
# and disabling DNS rebinding protection for AgentCore Runtime compatibility.

CONTAINERS_DIR="${PROJECT_ROOT}/containers"

echo "  Building S3 Tables AgentCore wrapper..."
docker build \
    -t "${S3_TABLES_REPO_NAME}:${IMAGE_TAG}" \
    -f "${CONTAINERS_DIR}/s3-tables/Dockerfile" \
    "${CONTAINERS_DIR}/s3-tables"

echo "  Building Redshift AgentCore wrapper..."
docker build \
    -t "${REDSHIFT_REPO_NAME}:${IMAGE_TAG}" \
    -f "${CONTAINERS_DIR}/redshift/Dockerfile" \
    "${CONTAINERS_DIR}/redshift"

echo "  Wrapper images built (overriding base tags)."
echo ""

# ─── Step 3: Authenticate with ECR ──────────────────────────────────────────

echo "── Step 3: Authenticating with ECR ──"

aws ecr get-login-password --region "$REGION" \
    | docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo "  ECR authentication successful."
echo ""

# ─── Step 4: Tag and push images ────────────────────────────────────────────

echo "── Step 4: Tagging and pushing images ──"

echo "  Tagging S3 Tables image..."
docker tag "${S3_TABLES_REPO_NAME}:${IMAGE_TAG}" "$S3_TABLES_IMAGE_URI"

echo "  Pushing S3 Tables image to ECR..."
docker push "$S3_TABLES_IMAGE_URI"

echo "  Tagging Redshift image..."
docker tag "${REDSHIFT_REPO_NAME}:${IMAGE_TAG}" "$REDSHIFT_IMAGE_URI"

echo "  Pushing Redshift image to ECR..."
docker push "$REDSHIFT_IMAGE_URI"

echo ""
echo "============================================"
echo " Build & Push Complete"
echo "============================================"
echo ""
echo "  S3 Tables image: ${S3_TABLES_IMAGE_URI}"
echo "  Redshift image:  ${REDSHIFT_IMAGE_URI}"
echo ""
echo "  Next step: Run deploy/deploy_runtimes.py to create AgentCore runtimes."
echo ""
