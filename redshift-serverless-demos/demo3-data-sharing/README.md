# Demo 3 — Cross-cluster data sharing (Serverless → Provisioned)

**Audience:** AnyCompany (loyalty / card-linked offers)
**Platform:** Amazon Redshift Serverless (producer) + Redshift provisioned RA3 (consumer)
**Duration:** ~5 minutes
**Goal:** Show that a provisioned analytics cluster can query Serverless any-company data
**live, with no copying**. The producer publishes a datashare; the consumer mounts it
as a local database and queries it directly. Reuses Demo 2's
`anycompany_demo.transactions_incoming` table (database `dev`).

---

## The two sides

| Role | Where | Namespace GUID | Notes |
|------|-------|----------------|-------|
| **Producer** | Serverless `default-namespace` / `default-workgroup` | `0a84a6f2-df5c-42ff-a5c4-83c12b5b8f37` | Holds `anycompany_demo.transactions_incoming` |
| **Consumer** | Provisioned `analytics-cluster` (single-node `ra3.large`) | `a2ba3a3f-bde1-4bda-ae84-70e95b20d0e8` | Mounts the share read-only |

Same account (`123456789012`), same region (`eu-west-1`), profile `demo-admin`
(override with `PROFILE=<name> bash run-share.sh …`).
Same-account sharing needs only `GRANT USAGE ON DATASHARE ... TO NAMESPACE '<guid>'` —
no cross-account authorization/association step.

---

## Files in this folder

| File | Purpose | When |
|------|---------|------|
| `00-prereqs.md` | Provisioned cluster + namespace GUIDs + RA3/IAM requirements | Before the call |
| `01-setup.sql` | (Producer) ensures `anycompany_demo.transactions_incoming` exists + has data | Before the call |
| `02-create-share.sql` | (Producer) creates `anycompany_share`, adds the table, grants to consumer namespace | Before the call (edit consumer GUID!) |
| `03-consume-and-verify.sql` | (Consumer) creates DB from the datashare, queries live | During the call |
| `04-runbook.md` | Minute-by-minute presenter script + recovery | During the call |
| `run-share.sh` | CLI orchestrator: `create-cluster\|producer-ns\|consumer-ns\|share\|consume\|verify\|live\|status\|teardown` | During the call |
| `test-run-share.sh` | Lightweight tests for `run-share.sh` command dispatch | Development |
| `99-teardown.sql` | (Both) drops the mounted DB + datashare | After the call |

> **Teardown deletes the provisioned cluster.** `ra3.large` costs ~**$0.543/hr** in
> `eu-west-1`, so `bash run-share.sh teardown` runs the SQL cleanup **and** deletes
> `analytics-cluster`. Do not skip it.

---

## Order of operations

1. **(Producer)** `01-setup.sql` — table exists and has rows to share.
2. **(Producer)** edit `02-create-share.sql` with the **consumer** namespace GUID, run it —
   datashare created and granted.
3. Create/confirm the consumer cluster (`bash run-share.sh create-cluster`).
4. **(Consumer)** edit `03-consume-and-verify.sql` with the **producer** namespace GUID,
   run it — mount the share and query live.
5. Prove it's live: insert a row on the producer, re-query on the consumer — it appears
   instantly with no reload.

**One-shot path (Data API, no Query Editor).** Runs as `PROFILE=demo-admin` by
default (an admin identity is required — `amplify-dev` cannot create datashares). This
full flow was validated end-to-end on `ra3.large` and then reset:
```bash
bash run-share.sh create-cluster   # single-node ra3.large (skips if it exists)
bash run-share.sh share            # producer: datashare + grant to consumer ns
bash run-share.sh consume          # consumer: CREATE DATABASE FROM DATASHARE
bash run-share.sh verify           # consumer: count + sample rows over the share
bash run-share.sh live             # insert on producer, re-count on consumer (live proof)
bash run-share.sh teardown         # drop db + datashare, DELETE the cluster
```

**Quick status check:** `bash run-share.sh status` — shows the datashares on both sides
without changing anything.

---

## Prereqs at a glance
- Provisioned `analytics-cluster` (single-node `ra3.large`) in `eu-west-1` — data
  sharing requires RA3 on both sides (Serverless is RA3-class already).
- Both namespace GUIDs (producer is known; consumer resolves once the cluster exists).
- Data API access: IAM `redshift:GetClusterCredentials` for the consumer, plus
  `redshift-data:*` on both.
- AWS CLI profile `demo-admin` (or override via `PROFILE` env var) with superuser /
  schema-owner privileges on the producer Serverless namespace.

## Why this matters for AnyCompany
- **No copies, no drift** — analysts on the provisioned cluster read the exact same rows
  the Serverless pipeline just wrote. No ETL, no nightly sync, no stale extract.
- **Isolated compute** — heavy analytics on the provisioned cluster don't compete with
  the ingest workload on Serverless. Each side scales independently.
- **Governed** — the producer grants specific schemas/tables to specific namespaces.
