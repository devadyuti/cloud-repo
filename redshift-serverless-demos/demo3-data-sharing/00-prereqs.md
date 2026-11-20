# Demo 3 — Cross-cluster data sharing: prerequisites

**Goal of the demo:** a **provisioned** analytics cluster queries data that lives on the
**Serverless** producer — live, with **no copy**. The producer publishes a *datashare*;
the consumer mounts it as a local database. Same account, same region.

---

## Key behaviour to know (affects the script order)

- **RA3 on both sides.** Redshift data sharing works only on RA3 node types. Serverless
  is RA3-class already; the provisioned consumer must be `ra3.*` (we use `ra3.large`).
- **Same account = simple.** Because producer and consumer are in the **same AWS
  account**, you only need `GRANT USAGE ON DATASHARE ... TO NAMESPACE '<guid>'`. There is
  **no** authorize/associate step (that is only for *cross-account* shares).
- **Shares are live, not copies.** The consumer reads the producer's blocks directly.
  A row inserted on the producer is visible on the consumer immediately — no reload.
- **Objects must be in one database.** We share from database `dev`, schema
  `anycompany_demo` (the same schema Demo 1/2 use).
- Refs: [Datashares overview](https://docs.aws.amazon.com/redshift/latest/dg/datashare-overview.html),
  [Sharing across clusters/namespaces](https://docs.aws.amazon.com/redshift/latest/dg/across-account.html).

---

## Prereq 1 — Namespace GUIDs (you need both)

Data sharing is namespace-to-namespace. Grab both GUIDs before you start.

**Producer (Serverless `default-namespace`):**
```bash
aws redshift-serverless get-namespace \
  --namespace-name default-namespace \
  --profile amplify-dev --region eu-west-1 \
  --query 'namespace.namespaceId' --output text
# -> 0a84a6f2-df5c-42ff-a5c4-83c12b5b8f37
```
Or, connected to the producer: `SELECT current_namespace;`

**Consumer (provisioned `analytics-cluster`):** available once the cluster exists —
```bash
aws redshift describe-clusters --cluster-identifier analytics-cluster \
  --profile amplify-dev --region eu-west-1 \
  --query 'Clusters[0].ClusterNamespaceArn' --output text
# arn:aws:redshift:eu-west-1:123456789012:namespace:<CONSUMER_GUID>
```
The GUID is the part after `namespace:`. `run-share.sh producer-ns` / `consumer-ns`
print these for you.

---

## Prereq 2 — The provisioned consumer cluster

**Validated 2026-07-10:** `analytics-cluster` already exists — single-node **`ra3.large`**,
status `available`, consumer namespace `a2ba3a3f-bde1-4bda-ae84-70e95b20d0e8`,
endpoint `analytics-cluster.cjvfhennhbiy.eu-west-1.redshift.amazonaws.com`. The demo is
built for this cluster as-is. `bash run-share.sh create-cluster` detects it and skips
creation.

If you ever need to recreate it (single-node RA3, same region as the producer):

```bash
aws redshift create-cluster \
  --cluster-identifier analytics-cluster \
  --node-type ra3.large \
  --number-of-nodes 1 \
  --master-username awsuser \
  --master-user-password '<StrongTempPassw0rd!>' \
  --publicly-accessible \
  --profile demo-admin --region eu-west-1
```

Provisioning takes a few minutes; wait for `ClusterStatus = available`.

> **Cost:** `ra3.large` is ~**$0.543/hr** on-demand in `eu-west-1`. This cluster is the
> only thing in the demo that bills by the hour — the teardown deletes it.

---

## Prereq 3 — Profile / privileges (this is the important one)

**Validated 2026-07-10 — the `amplify-dev` profile is NOT sufficient.** Via the Data API
`amplify-dev` connects as db user `IAM:amplify-dev`, which is **not a superuser** and does
**not** own schema `anycompany_demo` (owner is `IAMR:admin`). Datashare creation fails for it:
`ERROR: cannot create datashare on dev. permission denied`.

Use an **admin** profile that assumes the account's `admin` role. In this workspace that
is **`demo-admin`** (assumes `arn:aws:...:role/admin` in account `123456789012`,
connects to Serverless as `IAMR:admin`). It can:
- create/alter the datashare on the producer (owns `anycompany_demo`), and
- call `GetClusterCredentials` for `analytics-cluster` as `awsuser` (superuser).

`run-share.sh` defaults to `PROFILE=demo-admin`; override with `PROFILE=<name>` if your
admin profile is named differently.

The Data API also needs `redshift-data:ExecuteStatement`, `DescribeStatement`,
`GetStatementResult` on both sides (the admin role has these).

> Query Editor v2 works too — connect to the Serverless workgroup **as an admin**
> (not `amplify-dev`) for the producer steps, and to `analytics-cluster` for the consumer.

---

## Prereq checklist (validated 2026-07-10)
- [x] `anycompany_demo.transactions_incoming` exists on the producer with **7 rows**
- [x] Producer namespace GUID: `0a84a6f2-df5c-42ff-a5c4-83c12b5b8f37`
- [x] Provisioned `analytics-cluster` (`ra3.large`, 1 node) `available`
- [x] Consumer namespace GUID: `a2ba3a3f-bde1-4bda-ae84-70e95b20d0e8`
- [x] Admin profile (`demo-admin`) can drive both sides via Data API — **full
      producer→consumer share + live-insert flow tested end-to-end and then reset**
- [x] `region eu-west-1`
- [ ] Use `PROFILE=demo-admin` (or your admin profile) — **not** `amplify-dev`

Next: run `01-setup.sql` (producer), then `02-create-share.sql`, then follow `04-runbook.md`.

IAM/CLI snippets above follow AWS documentation; surrounding guidance was rephrased for licensing compliance.
