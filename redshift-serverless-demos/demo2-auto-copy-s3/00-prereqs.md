# Demo 2 — Auto-copy from S3 (COPY JOB): prerequisites

**Goal of the demo:** files land in an S3 prefix (as they would from AnyCompany's data
pipeline) and Redshift ingests them into a table with **no external ETL** — you just
define a COPY JOB once.

**Two paths (pick based on time/appetite):**

| Path | What it shows | Setup | Detection |
|------|---------------|-------|-----------|
| **A — COPY JOB + `COPY JOB RUN`** *(recommended for live demo)* | Job stores the COPY definition; new files load automatically. You trigger a run on stage so there's no waiting. | IAM role with S3 read only | On demand / polling |
| **B — S3 event integration** *(optional "production" path)* | Truly hands-off, near real-time load when a file lands | IAM role **+** S3 bucket policy **+** an S3 event integration resource | Event-driven |

> Do Path A live (deterministic). Mention/show Path B as the production-grade,
> real-time option if the customer asks "does someone have to trigger it?"

---

## Key behaviour to know (affects the script order)

- A COPY JOB **does not load pre-existing files** — only files created **after** the
  job is created. So the order is always: **create the job first, then upload files.**
- Redshift tracks loaded files **by filename**, so a file is never loaded twice.
- COPY JOB **cannot** use `MAXERROR`, `IGNOREALLERRORS`, a manifest, or key-based auth.
  You **must** pass `IAM_ROLE 'arn:...'` (the namespace default role is not used).
- Ref: [COPY JOB](https://docs.aws.amazon.com/redshift/latest/dg/r_COPY-JOB.html),
  [Auto-copy / S3 event integration](https://docs.aws.amazon.com/redshift/latest/dg/loading-data-copy-job.html)

---

## Prereq 1 — S3 bucket + prefix

Create (or reuse) a bucket in the **same region as your workgroup** (e.g. `eu-west-1`)
and a prefix the job will watch:

```bash
# set these once for the whole demo
export AWS_REGION=eu-west-1
export DEMO_BUCKET=any-company-demo-autocopy-<your-unique-suffix>
export DEMO_PREFIX=any-company-demo/auto-copy/incoming

aws s3 mb "s3://$DEMO_BUCKET" --region "$AWS_REGION"
```

Do **not** pre-upload the sample files — they go up *after* the job is created
(see the runbook). The `upload-files.sh` helper handles that.

---

## Prereq 2 — IAM role with S3 read, attached to the namespace

The role your Serverless namespace uses must be able to read the bucket.

**Permissions policy** (scope to the demo bucket):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AutoCopyRead",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::any-company-demo-autocopy-<your-unique-suffix>",
        "arn:aws:s3:::any-company-demo-autocopy-<your-unique-suffix>/*"
      ]
    }
  ]
}
```

**Trust policy** (lets Redshift assume the role):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": ["redshift.amazonaws.com"] },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Attach the role to the namespace:**
- Console: Redshift Serverless → your namespace → **Security and encryption** →
  **Manage IAM roles** → add the role → save. (Takes ~1 min to apply.)
- Note the role ARN — you'll paste it into the COPY JOB command as `IAM_ROLE`.

---

## Prereq 3 (Path B only) — S3 event integration for hands-off auto-copy

Skip for the live run; use if you want to show true event-driven ingestion.

1. Add a **bucket policy** allowing Redshift to manage notifications:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AutoCopyPolicy01",
      "Effect": "Allow",
      "Principal": { "Service": "redshift.amazonaws.com" },
      "Action": ["s3:GetBucketNotification", "s3:PutBucketNotification", "s3:GetBucketLocation"],
      "Resource": "arn:aws:s3:::any-company-demo-autocopy-<your-unique-suffix>",
      "Condition": {
        "StringEquals": { "aws:SourceAccount": "<your-account-id>" },
        "ArnLike": { "aws:SourceArn": "arn:aws:redshift:eu-west-1:<your-account-id>:integration:*" }
      }
    }
  ]
}
```
2. Redshift console → **Zero-ETL / Integrations → Create S3 event integration**, pick
   the bucket as source and your namespace as target.
3. When creating the COPY JOB, the AUTO ON job binds to the integration and loads
   files as they arrive — no `COPY JOB RUN` needed.

---

## Prereq checklist
- [ ] Bucket created in the workgroup's region
- [ ] IAM role with S3 read (policy + trust) created
- [ ] Role attached to the Serverless namespace (note the ARN)
- [ ] Demo 1's `anycompany_demo` schema already exists (we reuse it)
- [ ] `AWS_REGION`, `DEMO_BUCKET`, `DEMO_PREFIX` exported in your shell

Next: run `01-setup.sql`, then follow `04-runbook.md`.

IAM policies above were reproduced from AWS documentation for accuracy; surrounding guidance was rephrased for licensing compliance.
