# Demo 1 — Presenter runbook (~5 minutes)

**Story:** "You already write SQL. Amazon Q lets your analysts ask questions in plain
English and get correct, runnable SQL against your own schema — faster onboarding,
faster answers, no data leaves your control."

---

## Before the customer joins (5 min)

- [ ] Workgroup `default` shows **Available**.
- [ ] Ran `01-setup.sql` (data loaded) and `02-verify.sql` (counts look right).
- [ ] Amazon Q generative SQL enabled (Settings → Generative SQL settings → on).
- [ ] Q panel open, schema context = database with `anycompany_demo`.
- [ ] Ran one warm-up question so the first-query cold start is already paid.
- [ ] `03-amazon-q-prompts.md` open on a second screen / printed.

---

## Minute-by-minute

**0:00 — Frame it (30s)**
> "This is Redshift Serverless — no clusters to manage. I've loaded a small loyalty
> dataset: members, merchants, transactions, redemptions. Watch me ask questions in
> English instead of writing SQL."

**0:30 — Warm-up (30s)**
- Prompt: *How many members do we have, and how many are in each tier?*
- Run it. Point out Q wrote the GROUP BY for you.

**1:00 — Join without thinking about joins (1 min)**
- Prompt: *What is the total transaction amount per merchant category?*
- Highlight: Q figured out the transactions↔merchants join by itself.

**2:00 — Trend + chart (1 min)**
- Prompt: *Show total spend by month for the last 12 months.*
- Run, then switch result panel to **Chart**. Visual payoff.

**3:00 — The conversational moment (1 min)**
- Prompt: *Now break that down by sales channel.*
- Call it out: "It remembered the last question — this is a conversation."

**4:00 — Business value + trust (1 min)**
- Prompt: *Which membership tier redeems the most points on average per redemption?*
- Close with the trust points below.

---

## Closing talking points

- **Grounded on your schema:** Q uses your table/column metadata to generate SQL —
  answers reference real columns, not guesses.
- **Faster onboarding:** new analysts productive without learning every table first.
- **Stays in your control:** it generates SQL you review and run; you're not shipping
  raw data out to get an answer.
- **Serverless:** no cluster to size or babysit; it scales with the query and pauses
  when idle so you pay for what you use.

---

## If something breaks (recovery)

| Problem | Fix |
|--------|-----|
| Q panel missing | Settings → Generative SQL settings → enable; refresh QEv2. |
| Q returns wrong table | Re-select schema context in the Q panel; rephrase with exact table names. |
| Query slow first time | That's cold start — you warmed it up in pre-flight, so re-run. |
| Q unavailable entirely | Fall back to the reference SQL in `03-amazon-q-prompts.md`; story still lands. |
| Data looks empty | Re-run `02-verify.sql`; if empty, re-run `01-setup.sql`. |

---

## After the demo
- Optional: keep the workgroup for follow-up demos (2 and 3), or tear down.
- Teardown steps: see `00-provision-serverless.md` and `99-teardown.sql`.
