#!/usr/bin/env bash
set -euo pipefail

echo "run_model.sh: Preparing environment."

MODEL_DIR="/opt/ml/processing/input/model"

if [[ ! -d "${MODEL_DIR}/code" ]]; then
  echo "run_model.sh: ERROR: code directory not found in ${MODEL_DIR}" >&2
  exit 1
fi

if [[ ! -f "${MODEL_DIR}/requirements.txt" ]]; then
  echo "run_model.sh: ERROR: requirements.txt not found in ${MODEL_DIR}" >&2
  exit 1
fi

# Install pinned dependencies from the MLflow model artifact (already downloaded as a
# ProcessingInput) so the entry script has all required packages available.
# --timeout 5 --retries 0: fail fast if no internet access
pip install --quiet --timeout 5 --retries 0 -r "${MODEL_DIR}/requirements.txt" || {
  echo "run_model.sh: WARNING: pip install failed (no internet access?). Continuing with image packages." >&2
}

# MLflow stores code_paths under code/ within the artifact. Move them up to MODEL_DIR
# so MODEL_DIR can be used directly as a PYTHONPATH root (no /code/ prefix needed).
mv "${MODEL_DIR}/code/"* "${MODEL_DIR}/"

# Run from MODEL_DIR so that relative paths (e.g. config/config_base.yml) resolve
# correctly against the bundled code directories.
cd "$MODEL_DIR"

# MODEL_DIR now contains database/, models/, ifp_common/, config/ directly at its root.
export PYTHONPATH="$MODEL_DIR${PYTHONPATH:+:$PYTHONPATH}"

if [[ $# -lt 1 ]]; then
  echo "Usage: run_model.sh <python.module.name> [module args...]" >&2
  exit 2
fi

MODULE="$1"
shift

echo "[run_processing] python3 -m ${MODULE} $*"
exec python3 -m "${MODULE}" "$@"