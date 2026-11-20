# Demo 2 — Auto-copy from S3 (COPY JOB)

**Audience:** AnyCompany (loyalty / card-linked offers)
**Platform:** Amazon Redshift Serverless + S3
**Duration:** ~5 minutes
**Goal:** Show that files landing in S3 get ingested automatically via a COPY JOB —
no external ETL pipeline, deduplicated and auditable. Reuses Demo 1's `anycompany_demo`
schema (database `dev`).

---

## Files in this folder

| File | Purpose | When |
|------|---------|------|
| `00-prereqs.md` | S3 bucket + IAM role setup; Path A vs Path B | Before the call |
| `01-setup.sql` | Creates the `transactions_incoming` landing table | Before the call |
| `02-create-copy-job.sql` | Creates the `anycompany_autocopy_txns` COPY JOB (`AUTO ON`) | Before the call (edit placeholders!) |
| `sample-data/*.csv` | Two batches of new transactions to "arrive" in S3 | During the call |
| `upload-files.sh` | Uploads a batch to the watched S3 prefix | During the call |
| `run-copy.sh` | CLI orchestrator: `setup\|load\|status\|whoami\|sql\|verify\|reset` | During the call |
| `03-run-and-verify.sql` | `COPY JOB RUN` + verification / system views | During the call |
| `04-runbook.md` | Minute-by-minute presenter script + recovery | During the call |
| `test-run-copy.sh` | Lightweight tests for `run-copy.sh` command dispatch | Development |
| `99-teardown.sql` | Drops the job + landing table | After the call |

---

## Order of operations (important)

A COPY JOB only ingests files created **after** it exists. So:

1. `01-setup.sql` — create landing table.
2. Edit `02-create-copy-job.sql` (`<BUCKET>`, `<ROLE_ARN>`) and run it — **create the job first**.
3. `./upload-files.sh 1` — file arrives in S3.
4. `03-run-and-verify.sql` — `COPY JOB RUN` loads it, verify rows.
5. `./upload-files.sh 2` + `COPY JOB RUN` again — shows automation + dedup.

**Quick status check:** `bash run-copy.sh status` — shows registered copy jobs and current row count without triggering any loads.

**Utility helpers:**
- `bash run-copy.sh whoami` — displays the current database user and database name (useful for verifying connection context).
- `bash run-copy.sh sql "SELECT ..."` — runs an arbitrary SQL statement and returns the result set. Defaults to `SELECT 1;` if no query is provided.

See `04-runbook.md` for the full script.

---

## Prereqs at a glance
- Bucket in the workgroup's region + a watched prefix (`00-prereqs.md`).
- IAM role with `s3:GetObject` + `s3:ListBucket`, trusted by `redshift.amazonaws.com`,
  attached to the namespace. Its ARN goes in the COPY JOB.
- `AWS_REGION`, `DEMO_BUCKET`, `DEMO_PREFIX` exported in your shell.

## Live demo vs production
- **Live:** `COPY JOB RUN` triggers the load immediately (deterministic on stage).
- **Production/real-time:** add an S3 event integration (Path B) so loads fire on file
  arrival with no manual run.
