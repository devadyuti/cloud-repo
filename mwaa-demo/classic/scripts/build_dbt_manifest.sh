#!/usr/bin/env bash
# Pre-compile the dbt manifest that Cosmos uses to render the dbt_anycompany_analytics DAG.
#
# Why: with LoadMode.DBT_MANIFEST the MWAA DAG processor builds the Airflow task graph
# from target/manifest.json — no dbt subprocess and no Redshift connection at parse time.
# Re-run this whenever models, tests, or seeds change (deploy_dags.sh calls it for you).
#
# Usage: ./scripts/build_dbt_manifest.sh
#   DBT_BIN=/path/to/dbt ./scripts/build_dbt_manifest.sh   # use a specific dbt executable
#
# `dbt parse` never connects to the warehouse, so a placeholder profile is enough.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")/dags/dbt/anycompany_analytics"
DBT_BIN="${DBT_BIN:-dbt}"

if ! command -v "$DBT_BIN" > /dev/null 2>&1; then
    echo "ERROR: dbt not found. Install it in a separate venv, e.g.:"
    echo "  python3.12 -m venv ~/.dbt-venv && ~/.dbt-venv/bin/pip install dbt-core==1.12.6 dbt-redshift==1.11.1"
    echo "  DBT_BIN=~/.dbt-venv/bin/dbt $0"
    exit 1
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

cat > "$WORK_DIR/profiles.yml" <<'EOF'
anycompany_analytics:
  target: dev
  outputs:
    dev:
      type: redshift
      host: placeholder.invalid
      user: placeholder
      password: placeholder
      port: 5439
      dbname: dev
      schema: dbt_anycompany
      threads: 4
EOF

echo "=== Parsing dbt project: $PROJECT_DIR ==="
"$DBT_BIN" parse \
    --project-dir "$PROJECT_DIR" \
    --profiles-dir "$WORK_DIR" \
    --target-path "$WORK_DIR/target" \
    --no-partial-parse \
    --quiet

mkdir -p "$PROJECT_DIR/target"
cp "$WORK_DIR/target/manifest.json" "$PROJECT_DIR/target/manifest.json"
echo "Manifest written to $PROJECT_DIR/target/manifest.json"
