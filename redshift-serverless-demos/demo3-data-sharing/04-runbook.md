# Demo 3 — Cross-cluster data sharing: presenter runbook (~5 minutes)

**Story:** "AnyCompany's ingest runs on Serverless. Your analysts want a dedicated cluster
for heavy queries — but they need *today's* data, not last night's extract. With Redshift
data sharing, the provisioned cluster reads the Serverless data **live**, no copy, no ETL.
Two workloads, one copy of the truth."

---

## Before the customer joins

- [ ] Prereqs done (`00-prereqs.md`): both namespace GUIDs noted.
- [ ] **Use an admin identity** for the producer steps — `PROFILE=demo-admin` for
      `run-share.sh`, or QEv2 connected as admin. `amplify-dev` cannot create datashares.
- [ ] Ran `01-setup.sql` on the producer — `transactions_incoming` has rows.
- [ ] Edited `02-create-share.sql` with the **consumer** GUID, ran it —
      `SHOW DATASHARES LIKE 'anycompany_share'` returns the share.
- [ ] `analytics-cluster` (`ra3.large`, 1 node) is **available**
      (`bash run-share.sh create-cluster` then wait).
- [ ] Edited `03-consume-and-verify.sql` with the **producer** GUID (already filled in).
- [ ] Two Query Editor v2 tabs open: one on **default-workgroup** (producer), one on
      **analytics-cluster** (consumer). Or a terminal for `run-share.sh`.
- [ ] Dry run once end-to-end, then reset (drop `anycompany_shared` on the consumer).

---

## Minute-by-minute

**0:00 — Frame the problem (45s)**
> "Ingest is on Serverless. Analysts want an isolated cluster so their big queries don't
> fight the pipeline. The usual answer is copying data over nightly — which means it's
> always stale. Watch us skip the copy entirely."

**0:45 — Show the share on the producer (45s)**
- Producer tab: `SHOW DATASHARES LIKE 'anycompany_share';` and the `svv_datashare_objects`
  query from `02-create-share.sql`.
- "One datashare, granted to the analytics cluster's namespace. That's the whole
  publish step."

**1:30 — Mount it on the consumer (1 min)**
- Consumer tab: run `03-consume-and-verify.sql` steps 1–2.
  - `SHOW DATASHARES;` → the inbound `anycompany_share` is visible.
  - `CREATE DATABASE anycompany_shared FROM DATASHARE anycompany_share OF NAMESPACE '0a84a6f2-...';`
- "This creates a database on the provisioned cluster that *points at* the Serverless
  data. Nothing was copied — that returned instantly."

**2:30 — Query Serverless data from the provisioned cluster (1 min)**
- Consumer tab: steps 3–4.
  - `SELECT COUNT(*) FROM anycompany_shared.anycompany_demo.transactions_incoming;` → 7 rows
  - The `GROUP BY channel` aggregation.
- "This query is running on the provisioned cluster's compute, reading the Serverless
  producer's data live."

**3:30 — Prove it's live, not a snapshot (1 min)**
- Producer tab: insert a row —
  ```sql
  INSERT INTO anycompany_demo.transactions_incoming VALUES
    (100999, 999, 5, GETDATE(), 12.34, 0.62, 'online');
  ```
- Consumer tab: re-run the `COUNT(*)` → **8 rows**, immediately.
  > "I inserted that on Serverless one second ago and the provisioned cluster already
  > sees it. No sync job. That's the difference between sharing and copying."
- (Or do all of this with `bash run-share.sh live`.)

**4:30 — Close (30s)**
- "Two independent compute worlds — Serverless for ingest, provisioned for analytics —
  reading one governed copy of the data, live. You pick which schemas and tables to
  share, and to which teams."

---

## Talking points

- **Live, zero-copy** — consumer reads the producer's blocks; no duplication, no drift.
- **Workload isolation** — ingest and analytics scale separately, no resource contention.
- **Serverless ↔ provisioned** — share works across both form factors (both RA3).
- **Governed** — grant specific schemas/tables to specific namespaces; revoke anytime.
- **Same-account is one grant** — no cross-account authorize/associate needed here.

---

## Why a provisioned consumer (not another Serverless workgroup)?
It shows the pairing customers actually ask about: keep the elastic ingest on Serverless,
give analysts a fixed-cost RA3 cluster they control — without splitting the data.

---

## If something breaks (recovery)

| Problem | Fix |
|--------|-----|
| Share not visible on consumer (`SHOW DATASHARES` empty) | Wrong consumer GUID in the `GRANT` on the producer. Re-check `run-share.sh consumer-ns` and re-run `02-create-share.sql`. |
| `CREATE DATABASE FROM DATASHARE` fails: namespace not found | Producer GUID in `03` is wrong. Use `0a84a6f2-df5c-42ff-a5c4-83c12b5b8f37`. |
| "datashare ... does not support this node type" | A side isn't RA3. The consumer must be `ra3.*`. |
| Consumer count doesn't change after producer insert | You queried the wrong tab, or the producer insert didn't commit. Re-run the insert, then the count. |
| Data API `AccessDenied` on consumer | Caller lacks `redshift:GetClusterCredentials`. Use QEv2 instead, or grant it. |
| Cluster still `creating` | Provisioning takes a few minutes — wait for `available`. |

---

## Reset (between rehearsals)
```sql
-- consumer (analytics-cluster) -- no IF EXISTS in Redshift; ignore "does not exist"
DROP DATABASE anycompany_shared;
-- producer (remove the demo insert if you added it)
DELETE FROM anycompany_demo.transactions_incoming WHERE transaction_id = 100999;
```
The datashare itself can stay; just re-mount on the consumer. Full teardown (including
deleting the cluster) is `bash run-share.sh teardown` / `99-teardown.sql`.

> **Remember the meter:** `analytics-cluster` bills ~$0.543/hr while it exists. If you're
> done for the day, run the teardown.
