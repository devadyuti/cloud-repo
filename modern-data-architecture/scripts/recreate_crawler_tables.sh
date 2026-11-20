#!/usr/bin/env bash
#
# recreate_crawler_tables.sh
#
# Purpose:
#   A Glue crawler only applies its TablePrefix when it CREATES a table -- it
#   never renames tables that already exist. So if a crawler first ran without a
#   prefix and later had TablePrefix added (e.g. raw_ or stage_), its database
#   still holds the old unprefixed tables and the crawler keeps updating those
#   instead of creating prefixed ones.
#
#   This script (1) optionally sets the live crawler's TablePrefix, (2) deletes
#   the stale unprefixed table definitions the crawler produced, and (3) re-runs
#   the crawler so it recreates them WITH the prefix. It deletes ONLY catalog
#   metadata (the table definitions) -- the underlying S3 data is never touched.
#
#   The set of "stale" table names is derived automatically from the crawler's
#   own S3 targets: each target folder maps to one table named after that
#   folder. This makes the script correct for any crawler/database.
#
# Usage:
#   scripts/recreate_crawler_tables.sh --database <db> [--crawler <name>]
#       [--project mda] [--region <r>] [--prefix <p>] [--set-prefix]
#       [--yes] [--dry-run]
#
#   --database   Glue database holding the tables (required, e.g. raw or stage).
#   --crawler    Crawler name. Default: "<project>-<database>-crawler"
#                (so --project mda --database stage -> mda-stage-crawler).
#   --project    ProjectName used at deploy time (default: mda). Only used to
#                derive the default crawler name.
#   --region     AWS region. Defaults to AWS_REGION / AWS_DEFAULT_REGION / the
#                configured CLI region.
#   --prefix     The TablePrefix the crawler should use. Default: "<database>_"
#                (raw -> raw_, stage -> stage_).
#   --set-prefix Update the LIVE crawler's TablePrefix to --prefix before
#                crawling. Use this if the crawler was deployed without the
#                prefix and you are not redeploying the CloudFormation stack.
#   --yes        Skip the interactive confirmation before deleting tables.
#   --dry-run    Print what would happen without deleting or starting anything.
#
# NOTE: Correct sequence is (1) ensure the live crawler has the prefix -- via
#   --set-prefix or a CloudFormation redeploy of the updated template -- then
#   (2) delete the stale unprefixed tables and re-run the crawler. Running this
#   WITHOUT the prefix in place just recreates the unprefixed names.
#
# Requires: awscli v2, jq. Uses whatever AWS credentials are already configured.

set -euo pipefail

PROJECT="mda"
DATABASE=""
CRAWLER=""
REGION=""
PREFIX=""
SET_PREFIX=0
ASSUME_YES=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)    PROJECT="$2"; shift 2 ;;
    --database)   DATABASE="$2"; shift 2 ;;
    --crawler)    CRAWLER="$2"; shift 2 ;;
    --region)     REGION="$2"; shift 2 ;;
    --prefix)     PREFIX="$2"; shift 2 ;;
    --set-prefix) SET_PREFIX=1; shift ;;
    --yes)        ASSUME_YES=1; shift ;;
    --dry-run)    DRY_RUN=1; shift ;;
    -h|--help)  grep '^#' "$0" | sed 's/^#\{1,2\} \{0,1\}//'; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$DATABASE" ]]; then
  echo "ERROR: --database is required (e.g. --database raw or --database stage)." >&2
  exit 2
fi

# Defaults derived from database/project.
[[ -z "$CRAWLER" ]] && CRAWLER="${PROJECT}-${DATABASE}-crawler"
[[ -z "$PREFIX"  ]] && PREFIX="${DATABASE}_"

# Region flag applied to every aws call (empty = let the CLI resolve it).
AWS_REGION_ARGS=()
if [[ -n "$REGION" ]]; then
  AWS_REGION_ARGS=(--region "$REGION")
fi

for bin in aws jq; do
  command -v "$bin" >/dev/null 2>&1 || { echo "ERROR: '$bin' is required but not on PATH." >&2; exit 1; }
done

aws_glue() { aws glue "${AWS_REGION_ARGS[@]}" "$@"; }

echo "Project:  $PROJECT"
echo "Database: $DATABASE"
echo "Crawler:  $CRAWLER"
echo "Prefix:   $PREFIX"
echo "Region:   ${REGION:-<CLI default>}"
echo

# --- Sanity check: the database and crawler must exist -----------------------
if ! aws_glue get-database --name "$DATABASE" >/dev/null 2>&1; then
  echo "ERROR: Glue database '$DATABASE' not found. Is the stack deployed and are" >&2
  echo "       your credentials/region pointing at the right account?" >&2
  exit 1
fi
if ! aws_glue get-crawler --name "$CRAWLER" >/dev/null 2>&1; then
  echo "ERROR: Glue crawler '$CRAWLER' not found. Check --crawler/--project and --region." >&2
  exit 1
fi

# --- Derive the stale (unprefixed) table names from the crawler's S3 targets -
# Each S3 target folder maps to a table named after that folder. E.g.
# s3://bucket/sales/ -> table "sales".
STALE_TABLES=()
while IFS= read -r _t; do
  [[ -n "$_t" ]] && STALE_TABLES+=("$_t")
done < <(
  aws_glue get-crawler --name "$CRAWLER" \
    --query 'Crawler.Targets.S3Targets[].Path' --output text \
  | tr '\t' '\n' \
  | sed -E 's#/+$##; s#.*/##' \
  | grep -v '^$' \
  | sort -u
)

if [[ ${#STALE_TABLES[@]} -eq 0 ]]; then
  echo "ERROR: could not derive any table names from crawler S3 targets." >&2
  exit 1
fi
echo "Unprefixed table names implied by crawler S3 targets: ${STALE_TABLES[*]}"

# --- Check the LIVE crawler's TablePrefix ------------------------------------
# 'None' is what the CLI prints for a null TablePrefix.
LIVE_PREFIX="$(aws_glue get-crawler --name "$CRAWLER" --query 'Crawler.TablePrefix' --output text)"
echo "Live crawler TablePrefix: ${LIVE_PREFIX}"

if [[ "$LIVE_PREFIX" != "$PREFIX" ]]; then
  echo "WARNING: the deployed crawler's TablePrefix ('${LIVE_PREFIX}') does not match"
  echo "         the desired prefix ('${PREFIX}'). Recreating tables now would just"
  echo "         produce unprefixed names again."
  if [[ $SET_PREFIX -eq 1 ]]; then
    if [[ $DRY_RUN -eq 1 ]]; then
      echo "[dry-run] Would update crawler '$CRAWLER' TablePrefix -> '${PREFIX}'"
    else
      echo "Updating crawler '$CRAWLER' TablePrefix -> '${PREFIX}'..."
      aws_glue update-crawler --name "$CRAWLER" --table-prefix "$PREFIX"
      LIVE_PREFIX="$PREFIX"
    fi
  else
    echo "         Re-run with --set-prefix to update the live crawler in place, or"
    echo "         redeploy the CloudFormation stack (which now sets TablePrefix)."
    exit 1
  fi
fi

# --- Wait for any in-progress crawl to finish --------------------------------
wait_for_crawler_ready() {
  local state
  while true; do
    state="$(aws_glue get-crawler --name "$CRAWLER" --query 'Crawler.State' --output text)"
    if [[ "$state" == "READY" ]]; then
      break
    fi
    echo "  crawler state=$state; waiting..."
    sleep 15
  done
}

echo "Checking crawler is idle before making changes..."
wait_for_crawler_ready

# --- Figure out which stale tables actually exist ----------------------------
EXISTING_TABLES="$(aws_glue get-tables --database-name "$DATABASE" \
  --query 'TableList[].Name' --output json)"

to_delete=()
for t in "${STALE_TABLES[@]}"; do
  if echo "$EXISTING_TABLES" | jq -e --arg t "$t" 'index($t) != null' >/dev/null; then
    to_delete+=("$t")
  fi
done

if [[ ${#to_delete[@]} -eq 0 ]]; then
  echo "No stale unprefixed tables (${STALE_TABLES[*]}) found in '$DATABASE'."
  echo "Nothing to delete; will just (re)run the crawler."
else
  echo "Stale unprefixed tables to delete from '$DATABASE': ${to_delete[*]}"
fi

if [[ $DRY_RUN -eq 1 ]]; then
  echo
  echo "[dry-run] Would delete: ${to_delete[*]:-<none>}"
  echo "[dry-run] Would start crawler: $CRAWLER"
  exit 0
fi

# --- Confirm before deleting catalog metadata --------------------------------
if [[ ${#to_delete[@]} -gt 0 && $ASSUME_YES -ne 1 ]]; then
  echo
  echo "This deletes the above TABLE DEFINITIONS from the Glue Data Catalog."
  echo "Underlying S3 data is NOT affected. The crawler will recreate them as ${PREFIX}*."
  read -r -p "Proceed? [y/N] " reply
  case "$reply" in
    [yY]|[yY][eE][sS]) ;;
    *) echo "Aborted."; exit 1 ;;
  esac
fi

# --- Delete stale tables (batch, metadata only) ------------------------------
if [[ ${#to_delete[@]} -gt 0 ]]; then
  echo "Deleting stale tables..."
  aws_glue batch-delete-table --database-name "$DATABASE" \
    --tables-to-delete "${to_delete[@]}"
  echo "Deleted: ${to_delete[*]}"
fi

# --- Run the crawler and wait ------------------------------------------------
echo "Starting crawler '$CRAWLER'..."
aws_glue start-crawler --name "$CRAWLER"

# start-crawler returns immediately; give it a moment to leave READY, then wait.
sleep 5
wait_for_crawler_ready

# --- Report the resulting tables ---------------------------------------------
echo
echo "Crawl complete. Tables now in '$DATABASE':"
aws_glue get-tables --database-name "$DATABASE" \
  --query 'sort_by(TableList, &Name)[].Name' --output table

echo
echo "Expected ${PREFIX}-prefixed tables (one per crawler S3 target folder)."
