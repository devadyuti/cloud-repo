# Step 0 — Provision Redshift Serverless (do this first)

You need a **namespace** (storage + admin identity + IAM roles) and a **workgroup**
(compute — RPUs, networking) before running any demo SQL.

Two paths below: **Console** (easiest, ~5 min) or **CLI** (repeatable). Pick one.

> **Cost:** Serverless charges per RPU-hour *only while queries run* and auto-pauses
> when idle, plus a small storage charge. To stay safe we set **max RPU = 32** and a
> **daily usage limit**. Delete the workgroup after the engagement (see teardown at
> the bottom) if you don't need it.
>
> **Region:** examples use `eu-west-1`. Change to match the customer.

---

## Option A — Console (recommended for a one-off demo)

1. Go to **Amazon Redshift → Redshift Serverless → Get started / Create workgroup**.
2. **Workgroup**
   - Name: `any-company-demo-wg`
   - Base capacity: **8 RPU** (lowest; plenty for a demo)
   - Max capacity: set **32 RPU** (cost cap)
3. **Namespace**
   - Choose **Create a new namespace**: `any-company-demo-ns`
   - Admin credentials: set **Customize admin user credentials**
     - Admin user: `admin`
     - Set a password (save it) — or use **AWS Secrets Manager** managed credentials
4. **Networking**: accept the default VPC + subnets. Keep it **not publicly accessible**
   (Query Editor v2 connects over AWS's internal network, no public endpoint needed).
5. **IAM role**: under **Associated IAM roles**, choose **Create IAM role** and give it
   S3 access (default: "Any S3 bucket" is fine for a demo, or scope to one bucket).
   This role is used for auto-copy (Demo 2) and general S3 access — set it as **default**.
6. Create. Provisioning takes ~2–3 minutes.
7. **Usage limit (guardrail):** open the workgroup → **Limits** tab → add a
   **Daily** limit of e.g. `2` RPU-hours with action **Alert** (or **Deactivate**).

Then jump to **"After provisioning"** below.

---

## Option B — CLI (uses the helper script)

Run the bundled script. It discovers your default VPC subnets + security group,
creates the namespace and workgroup with cost guardrails, and prints the status.

```bash
# from this folder
chmod +x provision-serverless.sh
./provision-serverless.sh
```

Set overrides via env vars if you like:

```bash
AWS_REGION=eu-west-1 \
NAMESPACE=any-company-demo-ns \
WORKGROUP=any-company-demo-wg \
ADMIN_USER=admin \
MAX_RPU=32 \
./provision-serverless.sh
```

The script will prompt you to type `yes` before creating billable resources.

---

## After provisioning (both paths)

1. **Open Query Editor v2**: Redshift console → **Query editor v2** (left nav).
2. In the tree, expand your **`any-company-demo-wg`** workgroup → connect.
   - Auth: **Federated user** (uses your console IAM identity) or the admin
     user/password you set. Database: `dev`.
3. **Enable Amazon Q generative SQL** (one-time, account-level, admin):
   - Settings (gear icon) → **Generative SQL settings** → turn it **on**.
   - The admin needs `sqlworkbench:UpdateAccountQSqlSettings` in their IAM policy,
     plus the standard Query Editor v2 managed policy.
   - Ref: https://docs.aws.amazon.com/redshift/latest/mgmt/query-editor-v2-generative-ai-settings.html
4. Run **`01-setup.sql`** to load the loyalty demo data, then **`02-verify.sql`**.
5. Follow **`04-runbook.md`** on the call.

---

## Teardown (after the engagement)

Deleting the **workgroup** stops all compute charges. Deleting the **namespace**
removes the data (it will offer a final snapshot — you can skip it for a demo).

Console: Redshift Serverless → select workgroup → **Actions → Delete**, then the namespace.

CLI:
```bash
aws redshift-serverless delete-workgroup --workgroup-name any-company-demo-wg --region eu-west-1
aws redshift-serverless delete-namespace --namespace-name any-company-demo-ns --region eu-west-1
# (add --final-snapshot-name ... to delete-namespace if you want a backup)
```
