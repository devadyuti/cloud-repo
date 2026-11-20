-- =============================================================================
-- Demo 3 setup: PRODUCER side (Serverless default-namespace, database `dev`)
-- Ensures anycompany_demo.transactions_incoming exists and has rows to share.
-- Re-runnable. If Demo 2 already populated the table, this just tops it up.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS anycompany_demo;

-- Same shape as Demo 2's landing table.
CREATE TABLE IF NOT EXISTS anycompany_demo.transactions_incoming (
    transaction_id   INTEGER        NOT NULL,
    member_id        INTEGER        NOT NULL,
    merchant_id      INTEGER        NOT NULL,
    txn_ts           TIMESTAMP,
    amount           DECIMAL(10,2),
    cashback_earned  DECIMAL(10,2),
    channel          VARCHAR(20)
);

-- Seed a few rows only if the table is empty, so Demo 3 stands alone even if
-- Demo 2 wasn't run. (No duplicates on re-run: guarded by the NOT EXISTS check.)
INSERT INTO anycompany_demo.transactions_incoming
    (transaction_id, member_id, merchant_id, txn_ts, amount, cashback_earned, channel)
SELECT * FROM (
    SELECT 100001, 42,  2,  '2026-07-09 08:14:03'::timestamp, 4.20,   0.21,  'card_present' UNION ALL
    SELECT 100002, 317, 6,  '2026-07-09 09:02:47'::timestamp, 289.99, 17.40, 'online'       UNION ALL
    SELECT 100003, 88,  1,  '2026-07-09 10:31:15'::timestamp, 63.75,  0.96,  'card_present' UNION ALL
    SELECT 100004, 205, 4,  '2026-07-09 12:45:52'::timestamp, 38.10,  1.52,  'card_present' UNION ALL
    SELECT 100005, 461, 9,  '2026-07-09 14:20:09'::timestamp, 749.00, 22.47, 'online'       UNION ALL
    SELECT 100006, 12,  10, '2026-07-09 16:05:33'::timestamp, 3.80,   0.19,  'card_present' UNION ALL
    SELECT 100007, 150, 3,  '2026-07-09 18:11:27'::timestamp, 55.40,  1.11,  'card_present'
) seed
WHERE NOT EXISTS (SELECT 1 FROM anycompany_demo.transactions_incoming);

-- Confirm there is data to share.
SELECT COUNT(*) AS producer_rows FROM anycompany_demo.transactions_incoming;
SELECT current_namespace AS producer_namespace;
