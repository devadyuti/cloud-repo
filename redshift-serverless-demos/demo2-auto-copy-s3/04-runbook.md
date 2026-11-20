# Demo 2 — Auto-copy from S3: presenter runbook (~5 minutes)

**Story:** "AnyCompany's pipelines drop transaction files into S3. Instead of building and
babysitting an ingestion pipeline, you define a COPY JOB once and Redshift loads every
new file automatically — deduplicated, tracked, no glue code."

---

## Before the customer joins

- [ ] Prereqs done (`00-prereqs.md`): bucket created, IAM role with S3 read attached to
      the namespace, ARN noted.
- [ ] `AWS_REGION`, `DEMO_BUCKET`, `DEMO_PREFIX` exported in your terminal.
- [ ] Ran `01-setup.sql` — `transactions_incoming` exists and is empty.
- [ ] Edited `02-create-copy-job.sql` with your `<BUCKET>` and `<ROLE_ARN>`, ran it —
      `COPY JOB SHOW anycompany_autocopy_txns` returns the job.
- [ ] **Did NOT upload any files yet** (job must exist before files land).
- [ ] Terminal open in this folder, `upload-files.sh` is executable
      (`chmod +x upload-files.sh`).
- [ ] Dry run once end-to-end so you know timing, then reset (see "Reset" below).

---

## Minute-by-minute

**0:00 — Frame the problem (45s)**
> "Normally, loading files as they arrive means Lambda, a scheduler, error handling...
> an ETL pipeline to maintain. Watch how little we do here."

**0:45 — Show the job definition (45s)**
- In QEv2 run: `COPY JOB SHOW anycompany_autocopy_txns;`
- Point out: the COPY definition (bucket path, format, IAM role) is stored once, with
  `AUTO ON`. "This is the entire pipeline."

**1:30 — A file lands (45s)**
- In the terminal: `./upload-files.sh 1`
- "That's a batch of new transactions arriving from the pipeline into S3."

**2:15 — Redshift ingests it (1 min)**
- In QEv2 run `03-run-and-verify.sql` top section:
  - `COPY JOB RUN anycompany_autocopy_txns;`
  - `SELECT COUNT(*) FROM anycompany_demo.transactions_incoming;` → 7 rows
  - `SELECT * ...` show the loaded rows
- "No pipeline code. The job loaded the file."

**3:15 — Prove the automation + dedup (1 min)**
- Terminal: `./upload-files.sh 2` (second batch arrives)
- QEv2: `COPY JOB RUN anycompany_autocopy_txns;` then re-run the COUNT → now 14 rows
- Re-run `COPY JOB RUN` once more → count **stays 14**.
  > "It tracks loaded files by name — the first file is never re-loaded. Idempotent."

**4:15 — System views + close (45s)**
- Run the `sys_copy_job` and `sys_load_history` queries → show the audit trail of which
  files were loaded, when, and row counts.
- Close: "Define once, and every file that lands is ingested, tracked, and de-duplicated.
  For true real-time you add an S3 event integration and drop the manual run entirely."

---

## Talking points

- **No pipeline to build/maintain** — the COPY JOB *is* the pipeline.
- **Exactly-once by filename** — no duplicate loads, safe to retry.
- **Auditable** — `sys_copy_job` / `sys_load_history` / `stl_load_errors` show every load.
- **Serverless** — compute spins up for the load and pauses when idle.
- **Real-time option** — S3 event integration makes it event-driven (Path B in prereqs),
  no `COPY JOB RUN` needed.

---

## Why we use `COPY JOB RUN` live
Auto-detection (AUTO ON polling) isn't instant, and standing on stage waiting is awkward.
`COPY JOB RUN` loads the newly arrived files immediately and deterministically, while the
job's `AUTO ON` setting tells the true story: in production this happens on its own
(instantly, with an S3 event integration).

---

## If something breaks (recovery)

| Problem | Fix |
|--------|-----|
| `COPY JOB RUN` loads 0 rows | File was uploaded *before* the job was created, or wrong prefix. Re-upload (new filename) and re-run. |
| Access denied on S3 | IAM role missing `s3:GetObject`/`s3:ListBucket`, not attached to namespace, or trust policy missing `redshift.amazonaws.com`. |
| Load error / bad rows | Check `stl_load_errors` (query in `03-run-and-verify.sql`). Usually a header/format mismatch. |
| Count doesn't increase | You re-uploaded the same filename — dedup skips it. Use the other batch file. |
| Region mismatch | Bucket must be in the same region as the workgroup. |

---

## Reset (between rehearsals)
```sql
-- in QEv2
COPY JOB DROP anycompany_autocopy_txns;
TRUNCATE anycompany_demo.transactions_incoming;
```
```bash
# remove uploaded files so filenames are fresh
aws s3 rm "s3://$DEMO_BUCKET/$DEMO_PREFIX/" --recursive --region "$AWS_REGION"
```
Then re-run `02-create-copy-job.sql` before uploading again.
