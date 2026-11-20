#!/usr/bin/env bash
# ============================================================
# Claude Code + Amazon Bedrock — Team Setup (macOS)
# ============================================================
# This script:
#   1. Creates an AWS profile via ada (or isengardcli as fallback)
#   2. Adds Bedrock environment variables to ~/.bashrc & ~/.zshrc
#   3. Installs Claude Code if not already installed
#   4. Launches Claude Code
#
# Usage:
#   chmod +x setup-macos.sh
#   ./setup-macos.sh
#
# You will be prompted for your AWS account ID.
# ============================================================
set -euo pipefail

# ── Configuration ───────────────────────────────────────────
PROFILE_NAME="claude-bedrock"
AWS_REGION_VALUE="us-east-1"
SONNET_MODEL="us.anthropic.claude-sonnet-4-6"
HAIKU_MODEL="us.anthropic.claude-haiku-4-5-20251001-v1:0"
OPUS_MODEL="us.anthropic.claude-opus-4-7"
# ─────────────────────────────────────────────────────────────

echo "============================================"
echo "  Claude Code + Bedrock — macOS Setup"
echo "============================================"
echo ""

# ── Step 1: Check prerequisites ─────────────────────────────
echo "🔍 Checking prerequisites..."

# Node.js
if ! command -v node &>/dev/null; then
  echo "❌ Node.js is not installed. Please install Node.js 18+ first."
  echo "   brew install node"
  exit 1
fi
NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
  echo "❌ Node.js 18+ required. Found: $(node -v)"
  exit 1
fi
echo "  ✅ Node.js $(node -v)"

# Detect credential tool: prefer ada, fall back to isengardcli
CRED_TOOL=""
if command -v ada &>/dev/null; then
  CRED_TOOL="ada"
  echo "  ✅ ada found"
elif command -v isengardcli &>/dev/null; then
  CRED_TOOL="isengardcli"
  echo "  ✅ isengardcli found (legacy)"
else
  echo "❌ Neither ada nor isengardcli found. Install one first:"
  echo "   ada:          toolbox install ada"
  echo "   isengardcli:  toolbox install isengardcli  (legacy, may not be available)"
  exit 1
fi

# AWS CLI
if ! command -v aws &>/dev/null; then
  echo "❌ AWS CLI not found. Install it first:"
  echo "   brew install awscli"
  exit 1
fi
echo "  ✅ AWS CLI found"

# ── Step 2: Create AWS profile ───────────────────────────────
echo ""
echo "🔐 Setting up AWS profile '$PROFILE_NAME' via $CRED_TOOL..."
echo ""

create_profile() {
  local ACCOUNT_ID="$1"
  if [ "$CRED_TOOL" = "ada" ]; then
    ada profile add --account "$ACCOUNT_ID" --profile "$PROFILE_NAME" --provider isengard --region "$AWS_REGION_VALUE"
  else
    isengardcli add-profile "$ACCOUNT_ID" --profile "$PROFILE_NAME" --region "$AWS_REGION_VALUE"
  fi
}

# Check if profile already exists
if aws configure list --profile "$PROFILE_NAME" &>/dev/null 2>&1; then
  echo "  ⚠️  Profile '$PROFILE_NAME' already exists."
  read -rp "  Overwrite it? (y/N): " OVERWRITE
  if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
    echo "  Keeping existing profile."
  else
    read -rp "  Enter your AWS account ID: " ACCOUNT_ID
    create_profile "$ACCOUNT_ID"
    echo "  ✅ Profile '$PROFILE_NAME' created via $CRED_TOOL"
  fi
else
  read -rp "  Enter your AWS account ID: " ACCOUNT_ID
  create_profile "$ACCOUNT_ID"
  echo "  ✅ Profile '$PROFILE_NAME' created via $CRED_TOOL"
fi

# Verify credentials
echo ""
echo "  Verifying credentials..."
if aws sts get-caller-identity --profile "$PROFILE_NAME" &>/dev/null; then
  IDENTITY=$(aws sts get-caller-identity --profile "$PROFILE_NAME" --output text --query 'Arn')
  echo "  ✅ Authenticated as: $IDENTITY"
else
  echo "  ⚠️  Could not verify credentials right now. You may need to run:"
  if [ "$CRED_TOOL" = "ada" ]; then
    echo "     ada credentials update --account <account-id> --profile $PROFILE_NAME --role <your-role> --once"
    echo "     (Common roles: Admin, ReadOnly, or a custom role from your team)"
  else
    echo "     isengardcli credentials <account-id>"
  fi
  echo "  Continuing with setup..."
fi

# ── Step 3: Add environment variables to shell profiles ──────
echo ""
echo "📝 Adding environment variables to shell profiles..."

ENV_BLOCK="
# Claude Code + Amazon Bedrock (added by setup script)
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_PROFILE=$PROFILE_NAME
export AWS_REGION=$AWS_REGION_VALUE
export ANTHROPIC_DEFAULT_SONNET_MODEL='$SONNET_MODEL'
export ANTHROPIC_DEFAULT_HAIKU_MODEL='$HAIKU_MODEL'
export ANTHROPIC_DEFAULT_OPUS_MODEL='$OPUS_MODEL'"

for RC in "$HOME/.bashrc" "$HOME/.zshrc"; do
  if [ -f "$RC" ]; then
    if grep -q "CLAUDE_CODE_USE_BEDROCK" "$RC"; then
      echo "  ⏭️  Already present in $RC — skipping"
    else
      echo "$ENV_BLOCK" >> "$RC"
      echo "  ✅ Added to $RC"
    fi
  else
    echo "$ENV_BLOCK" > "$RC"
    echo "  ✅ Created $RC with variables"
  fi
done

# Source into current session
export CLAUDE_CODE_USE_BEDROCK=1
export AWS_PROFILE="$PROFILE_NAME"
export AWS_REGION="$AWS_REGION_VALUE"
export ANTHROPIC_DEFAULT_SONNET_MODEL="$SONNET_MODEL"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="$HAIKU_MODEL"
export ANTHROPIC_DEFAULT_OPUS_MODEL="$OPUS_MODEL"

# ── Step 4: Install Claude Code ──────────────────────────────
echo ""
echo "📦 Checking Claude Code installation..."

if command -v claude &>/dev/null; then
  echo "  ✅ Claude Code already installed"
else
  echo "  Installing Claude Code (requires sudo)..."
  sudo npm install -g @anthropic-ai/claude-code
  echo "  ✅ Claude Code installed"
fi

# ── Step 5: Launch ───────────────────────────────────────────
echo ""
echo "============================================"
echo "  ✅ Setup complete!"
echo "============================================"
echo ""
echo "  Profile:  $PROFILE_NAME (via $CRED_TOOL)"
echo "  Region:   $AWS_REGION_VALUE"
echo "  Models:   Sonnet 4.6, Haiku 4.5, Opus 4.7"
echo ""
echo "  Launching Claude Code..."
echo ""

claude
