# Demo 1 — Query Editor v2 + Amazon Q generative SQL

**Audience:** AnyCompany (loyalty / card-linked offers)
**Platform:** Amazon Redshift Serverless + Query Editor v2 (QEv2)
**Duration:** ~5 minutes
**Goal:** Show natural-language → SQL in the editor, grounded on *their* kind of data (members, merchants, transactions, redemptions), so the productivity win is obvious.

---

## Files in this folder

| File | Purpose | When to run |
|------|---------|-------------|
| `01-setup.sql` | Creates `anycompany_demo` schema + sample data | Before the call (once) |
| `02-verify.sql` | Sanity-check row counts and sample rows | Before the call |
| `03-amazon-q-prompts.md` | The natural-language prompts to type live, with the SQL you should expect | During the call |
| `04-runbook.md` | Minute-by-minute presenter script + talking points | During the call |
| `99-teardown.sql` | Removes everything the demo created | After the call (optional) |

---

## Pre-flight checklist (do this before the customer joins)

1. **Warm the workgroup.** Run any quick query in QEv2 so the first-query cold start doesn't happen live.
   ```sql
   SELECT 1;
   ```
2. **Enable Amazon Q generative SQL (admin, one-time per account).**
   - In QEv2, choose the **Settings** (gear) icon → **Generative SQL settings**.
   - Toggle **Q generative SQL** on for the account.
   - The admin doing this needs `sqlworkbench:UpdateAccountQSqlSettings` in their IAM policy, on top of the standard QEv2 managed policy.
   - Ref: [Updating generative SQL settings as an administrator](https://docs.aws.amazon.com/redshift/latest/mgmt/query-editor-v2-generative-ai-settings.html)
3. **Load the demo data.** Open `01-setup.sql` in QEv2, connect to your Serverless workgroup (database `dev` is fine), and run the whole script.
4. **Verify.** Run `02-verify.sql` — you should see non-zero counts for all four tables.
5. **Confirm the Q panel is visible.** Look for the Amazon Q / generative SQL chat panel in the editor. Ask it one warm-up question privately (e.g. "how many members do we have?") so you know it's connected to the right database/schema.

> Tip: In the Q chat panel, make sure the selected **database/schema context** points at the database where you created `anycompany_demo`. Q grounds its SQL on the schema it can see.

---

## What "good" looks like on the call

- You type plain English, Q returns runnable SQL referencing `anycompany_demo` tables and columns.
- You click **Add to query** → **Run**, and a result/chart appears.
- A follow-up prompt ("now only for the last 90 days") refines the previous answer — showing it's conversational and context-aware.

Content in `03-amazon-q-prompts.md` was written for compliance with source licensing; enablement steps were rephrased from AWS documentation.
