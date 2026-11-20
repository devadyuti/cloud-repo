#!/usr/bin/env bash
# Build the OpenAI SDK Lambda layer as a standalone zip.
# Use this only if you are NOT relying on `sam build` (which builds the
# layer automatically via the template's BuildMethod).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LAYER_DIR="$PROJECT_DIR/layer"

rm -rf "$LAYER_DIR/python"
mkdir -p "$LAYER_DIR/python"

pip install -r "$LAYER_DIR/requirements.txt" -t "$LAYER_DIR/python"

cd "$LAYER_DIR"
rm -f openai-layer.zip
zip -r openai-layer.zip python/ >/dev/null

echo "Built $LAYER_DIR/openai-layer.zip"
