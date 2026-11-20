# Demo 1 — Amazon Q generative SQL prompt cheat sheet

Type these **in plain English** into the Amazon Q chat panel in Query Editor v2.
Q reads the `anycompany_demo` schema and generates SQL. Click **Add to query → Run**.

> Before you start: in the Q panel, make sure the selected database/schema context
> points at the database containing `anycompany_demo` (database `dev`). Q grounds its
> SQL on the schema it can see. If answers look wrong, re-select the schema.

The "SQL you should expect" is a reference so you can sanity-check what Q produces.
Q may phrase things differently — that's fine as long as results are sensible.

---

## Warm-up (build confidence)

**Prompt:** `How many members do we have, and how many are in each tier?`

Expect something like:
```sql
SELECT tier, COUNT(*) AS member_count
FROM anycompany_demo.members
GROUP BY tier
ORDER BY member_count DESC;
```

---

## 1. Simple aggregation

**Prompt:** `What is the total transaction amount per merchant category?`

Expect:
```sql
SELECT m.category, SUM(t.amount) AS total_amount
FROM anycompany_demo.transactions t
JOIN anycompany_demo.merchants m ON m.merchant_id = t.merchant_id
GROUP BY m.category
ORDER BY total_amount DESC;
```
*Talking point:* Q inferred the join between transactions and merchants on its own.

---

## 2. Top-N with a join

**Prompt:** `Show me the top 5 merchants by total cashback earned by members.`

Expect:
```sql
SELECT m.merchant_name, SUM(t.cashback_earned) AS total_cashback
FROM anycompany_demo.transactions t
JOIN anycompany_demo.merchants m ON m.merchant_id = t.merchant_id
GROUP BY m.merchant_name
ORDER BY total_cashback DESC
LIMIT 5;
```

---

## 3. Time filtering (great for a chart)

**Prompt:** `Show total spend by month for the last 12 months.`

Expect:
```sql
SELECT DATE_TRUNC('month', txn_ts) AS month, SUM(amount) AS total_spend
FROM anycompany_demo.transactions
WHERE txn_ts >= DATEADD(month, -12, GETDATE())
GROUP BY 1
ORDER BY 1;
```
*Action:* After running, switch the result panel to **Chart** to show the trend.

---

## 4. Conversational follow-up (the "wow")

Right after prompt 3, ask:

**Prompt:** `Now break that down by sales channel.`

Expect Q to keep context and add `channel` to the grouping:
```sql
SELECT DATE_TRUNC('month', txn_ts) AS month, channel, SUM(amount) AS total_spend
FROM anycompany_demo.transactions
WHERE txn_ts >= DATEADD(month, -12, GETDATE())
GROUP BY 1, 2
ORDER BY 1, 2;
```
*Talking point:* It remembered the previous question — this is conversational, not one-shot.

---

## 5. Multi-table / business question

**Prompt:** `Which membership tier redeems the most points on average per redemption?`

Expect:
```sql
SELECT mem.tier, AVG(r.points_redeemed) AS avg_points
FROM anycompany_demo.redemptions r
JOIN anycompany_demo.members mem ON mem.member_id = r.member_id
GROUP BY mem.tier
ORDER BY avg_points DESC;
```

---

## 6. "Explain this" / self-serve angle

**Prompt:** `List the most valuable members by total spend, with their city and tier, top 10.`

Expect:
```sql
SELECT mem.member_id, mem.first_name, mem.last_name, mem.city, mem.tier,
       SUM(t.amount) AS total_spend
FROM anycompany_demo.transactions t
JOIN anycompany_demo.members mem ON mem.member_id = t.member_id
GROUP BY 1,2,3,4,5
ORDER BY total_spend DESC
LIMIT 10;
```

---

## Backup prompts (if one misfires)

- `How many transactions happened online versus card present?`
- `What percentage of members are Gold or Platinum tier?`
- `Which city has the highest average transaction amount?`
- `Show the number of new members who joined each month.`

## If Q generates wrong or empty results
- Re-check the schema context selector in the Q panel.
- Rephrase using exact terms: "transactions", "members", "cashback_earned", "merchant category".
- Fall back to running the reference SQL above directly — the story still lands.
