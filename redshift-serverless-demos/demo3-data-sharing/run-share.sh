#!/usr/bin/env bash
# Orchestrates Demo 3 via the Redshift Data API (no Query Editor needed).
# Producer = Serverless default-workgroup; Consumer = provisioned analytics-cluster.
# Flow: create cluster -> producer publishes datashare -> consumer mounts it -> verify live.
#
# Usage:
#   bash run-share.sh create-cluster   # single-node ra3.large (skips if it exists)
#   bash run-share.sh producer-ns      # print producer namespace GUID
#   bash run-share.sh consumer-ns      # print consumer namespace GUID
#   bash run-share.sh share            # producer: create datashare + grant to consumer ns
#   bash run-share.sh consume          # consumer: CREATE DATABASE FROM DATASHARE
#   bash run-share.sh verify           # consumer: count + sample rows over the share
#   bash run-share.sh live             # insert on producer, re-count on consumer (live proof)
#   bash run-share.sh status           # show datashares on both sides
#   bash run-share.sh teardown         # drop db + datashare, DELETE the cluster (billable!)

set -uo pipefail

# NOTE ON PROFILE / PRIVILEGES (validated 2026-07-10):
#   The producer datashare commands (CREATE DATASHARE, ALTER DATASHARE ADD SCHEMA)
#   require a superuser or the owner of schema anycompany_demo. That schema is owned by
#   IAMR:admin, and IAM:amplify-dev is NOT a superuser ("cannot create datashare ...
#   permission denied"). So this script uses an ADMIN profile that assumes the
#   account's `admin` role (connects to Serverless as IAMR:admin) and can also call
#   GetClusterCredentials for the provisioned cluster. Override with PROFILE=... if
#   your admin profile has a different name.
PROFILE="${PROFILE:-demo-admin}"
REGION="eu-west-1"

# Producer (Serverless)
WORKGROUP="default-workgroup"
PRODUCER_DB="dev"
PRODUCER_NS="0a84a6f2-df5c-42ff-a5c4-83c12b5b8f37"

# Consumer (provisioned)
CLUSTER="analytics-cluster"
NODE_TYPE="ra3.large"           # existing cluster is single-node ra3.large (~$0.543/hr)
CONSUMER_DB="dev"
CONSUMER_USER="awsuser"

SHARE="anycompany_share"
SHARED_DB="anycompany_shared"
SCHEMA="anycompany_demo"
TABLE="transactions_incoming"

# ---- Data API helpers -------------------------------------------------------
# Poll a submitted statement to completion. Echoes the statement id on success.
_wait() {
  local label="$1"; local id="$2"
  local st
  while true; do
    st=$(aws redshift-data describe-statement --id "$id" --profile "$PROFILE" --region "$REGION" --query 'Status' --output text)
    case "$st" in FINISHED|FAILED|ABORTED) break;; esac
    sleep 2
  done
  echo "[$label] STATUS=$st (id=$id)" >&2
  if [ "$st" != "FINISHED" ]; then
    aws redshift-data describe-statement --id "$id" --profile "$PROFILE" --region "$REGION" --query 'Error' --output text >&2
    return 1
  fi
  echo "$id"
}

# Run SQL on the PRODUCER (Serverless workgroup).
prod_sql() {
  local label="$1"; local sql="$2"
  local id
  id=$(aws redshift-data execute-statement --workgroup-name "$WORKGROUP" --database "$PRODUCER_DB" \
        --sql "$sql" --profile "$PROFILE" --region "$REGION" --query 'Id' --output text) || return 1
  _wait "$label" "$id"
}

# Run SQL on the CONSUMER (provisioned cluster; uses temporary creds via db-user).
cons_sql() {
  local label="$1"; local sql="$2"
  local id
  id=$(aws redshift-data execute-statement --cluster-identifier "$CLUSTER" --database "$CONSUMER_DB" \
        --db-user "$CONSUMER_USER" --sql "$sql" --profile "$PROFILE" --region "$REGION" --query 'Id' --output text) || return 1
  _wait "$label" "$id"
}

# Run + print the result set (JSON records). $1 side: prod|cons, $2 label, $3 sql.
show_result() {
  local side="$1"; local label="$2"; local sql="$3"
  local id
  if [ "$side" = "cons" ]; then id=$(cons_sql "$label" "$sql" | tail -n1); else id=$(prod_sql "$label" "$sql" | tail -n1); fi
  [ -n "$id" ] || return 1
  aws redshift-data get-statement-result --id "$id" --profile "$PROFILE" --region "$REGION" \
    --query 'Records' --output json
}

# Resolve the consumer namespace GUID from the cluster's namespace ARN.
resolve_consumer_ns() {
  local arn
  arn=$(aws redshift describe-clusters --cluster-identifier "$CLUSTER" --profile "$PROFILE" --region "$REGION" \
        --query 'Clusters[0].ClusterNamespaceArn' --output text 2>/dev/null)
  echo "${arn##*:namespace:}"
}

cmd="${1:-status}"

case "$cmd" in
  create-cluster)
    if aws redshift describe-clusters --cluster-identifier "$CLUSTER" --profile "$PROFILE" --region "$REGION" >/dev/null 2>&1; then
      echo "cluster '$CLUSTER' already exists — skipping create"
      aws redshift describe-clusters --cluster-identifier "$CLUSTER" --profile "$PROFILE" --region "$REGION" \
        --query 'Clusters[0].{status:ClusterStatus,type:NodeType,nodes:NumberOfNodes}' --output json
    else
      echo "creating single-node $NODE_TYPE cluster '$CLUSTER' (~a few minutes)..."
      : "${MASTER_PASSWORD:?set MASTER_PASSWORD env var to a strong password before creating}"
      aws redshift create-cluster \
        --cluster-identifier "$CLUSTER" \
        --node-type "$NODE_TYPE" \
        --number-of-nodes 1 \
        --master-username "$CONSUMER_USER" \
        --master-user-password "$MASTER_PASSWORD" \
        --publicly-accessible \
        --profile "$PROFILE" --region "$REGION" \
        --query 'Cluster.{id:ClusterIdentifier,status:ClusterStatus}' --output json
      echo "waiting for 'available'..."
      aws redshift wait cluster-available --cluster-identifier "$CLUSTER" --profile "$PROFILE" --region "$REGION"
      echo "cluster available"
    fi
    ;;

  producer-ns)
    echo "$PRODUCER_NS"
    ;;

  consumer-ns)
    ns=$(resolve_consumer_ns)
    if [ -n "$ns" ] && [ "$ns" != "None" ]; then echo "$ns"; else echo "ERROR: cluster '$CLUSTER' not found — run create-cluster first" >&2; exit 1; fi
    ;;

  share)
    cns=$(resolve_consumer_ns)
    if [ -z "$cns" ] || [ "$cns" = "None" ]; then echo "ERROR: could not resolve consumer namespace — is '$CLUSTER' created?" >&2; exit 1; fi
    echo "granting datashare '$SHARE' to consumer namespace $cns"
    prod_sql "drop-share" "DROP DATASHARE $SHARE;" >/dev/null 2>&1 || true   # no IF EXISTS in Redshift
    prod_sql "create-share" "CREATE DATASHARE $SHARE;" >/dev/null && echo "datashare created"
    prod_sql "add-schema" "ALTER DATASHARE $SHARE ADD SCHEMA $SCHEMA;" >/dev/null && echo "schema added"
    prod_sql "add-table" "ALTER DATASHARE $SHARE ADD TABLE $SCHEMA.$TABLE;" >/dev/null && echo "table added"
    prod_sql "grant" "GRANT USAGE ON DATASHARE $SHARE TO NAMESPACE '$cns';" >/dev/null && echo "granted to $cns"
    ;;

  consume)
    echo "mounting datashare '$SHARE' from producer namespace $PRODUCER_NS on '$CLUSTER'"
    cons_sql "drop-db" "DROP DATABASE $SHARED_DB;" >/dev/null 2>&1 || true   # no IF EXISTS in Redshift
    cons_sql "create-db" "CREATE DATABASE $SHARED_DB FROM DATASHARE $SHARE OF NAMESPACE '$PRODUCER_NS';" >/dev/null && echo "database '$SHARED_DB' mounted"
    ;;

  verify)
    echo "--- rows visible over the share (running on provisioned cluster) ---"
    show_result cons "count" "SELECT COUNT(*) AS rows_visible FROM $SHARED_DB.$SCHEMA.$TABLE;"
    echo "--- by channel ---"
    show_result cons "agg" "SELECT channel, COUNT(*) AS txns, ROUND(SUM(amount),2) AS total_amount FROM $SHARED_DB.$SCHEMA.$TABLE GROUP BY channel ORDER BY total_amount DESC;"
    ;;

  live)
    echo "--- consumer count BEFORE producer insert ---"
    show_result cons "count-before" "SELECT COUNT(*) AS rows_visible FROM $SHARED_DB.$SCHEMA.$TABLE;"
    echo "--- inserting one row on the PRODUCER ---"
    prod_sql "insert" "INSERT INTO $SCHEMA.$TABLE VALUES (100999, 999, 5, GETDATE(), 12.34, 0.62, 'online');" >/dev/null && echo "row inserted on producer"
    sleep 2
    echo "--- consumer count AFTER producer insert (should be +1, no reload) ---"
    show_result cons "count-after" "SELECT COUNT(*) AS rows_visible FROM $SHARED_DB.$SCHEMA.$TABLE;"
    ;;

  status)
    echo "--- producer: outbound datashares ---"
    show_result prod "prod-shares" "SELECT share_name, share_type FROM svv_datashares;"
    echo "--- consumer: inbound datashares ---"
    show_result cons "cons-shares" "SELECT share_name, share_type FROM svv_datashares;" || echo "(consumer not reachable — cluster may not exist yet)"
    ;;

  teardown)
    echo "dropping mounted database on consumer..."
    cons_sql "drop-db" "DROP DATABASE $SHARED_DB;" >/dev/null 2>&1 && echo "database dropped" || echo "(consumer db not present / cluster gone)"
    echo "dropping datashare + demo row on producer..."
    prod_sql "drop-share" "DROP DATASHARE $SHARE;" >/dev/null 2>&1 && echo "datashare dropped" || echo "(datashare not present)"
    prod_sql "del-row" "DELETE FROM $SCHEMA.$TABLE WHERE transaction_id = 100999;" >/dev/null 2>&1 || true
    echo "deleting provisioned cluster '$CLUSTER' (stops the ~\$0.543/hr charge)..."
    aws redshift delete-cluster --cluster-identifier "$CLUSTER" --skip-final-cluster-snapshot \
      --profile "$PROFILE" --region "$REGION" \
      --query 'Cluster.{id:ClusterIdentifier,status:ClusterStatus}' --output json \
      && echo "cluster deletion requested" || echo "(cluster not found / already deleting)"
    echo "teardown complete"
    ;;

  *)
    echo "Unknown command: $cmd (use create-cluster|producer-ns|consumer-ns|share|consume|verify|live|status|teardown)"; exit 1 ;;
esac
