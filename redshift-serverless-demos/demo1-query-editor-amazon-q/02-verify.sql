-- =============================================================================
-- Demo 1 verification: run AFTER 01-setup.sql
-- Every count should be non-zero and match the expected values below.
-- =============================================================================

-- Row counts (expected: members 500, merchants 12, offers 12,
--             transactions 5000, redemptions 800)
SELECT 'members'      AS table_name, COUNT(*) AS row_count FROM anycompany_demo.members
UNION ALL
SELECT 'merchants',    COUNT(*) FROM anycompany_demo.merchants
UNION ALL
SELECT 'offers',       COUNT(*) FROM anycompany_demo.offers
UNION ALL
SELECT 'transactions', COUNT(*) FROM anycompany_demo.transactions
UNION ALL
SELECT 'redemptions',  COUNT(*) FROM anycompany_demo.redemptions
ORDER BY table_name;

-- Peek at a few rows from each table
SELECT * FROM anycompany_demo.members    LIMIT 5;
SELECT * FROM anycompany_demo.merchants  LIMIT 5;
SELECT * FROM anycompany_demo.offers     LIMIT 5;
SELECT * FROM anycompany_demo.transactions ORDER BY txn_ts DESC LIMIT 5;
SELECT * FROM anycompany_demo.redemptions  ORDER BY redeemed_ts DESC LIMIT 5;

-- Sanity: a join that Amazon Q-style questions will rely on
-- (total spend and cashback by merchant category)
SELECT
    m.category,
    COUNT(*)                     AS txn_count,
    ROUND(SUM(t.amount), 2)      AS total_spend,
    ROUND(SUM(t.cashback_earned), 2) AS total_cashback
FROM anycompany_demo.transactions t
JOIN anycompany_demo.merchants m ON m.merchant_id = t.merchant_id
GROUP BY m.category
ORDER BY total_spend DESC;

-- Sanity: date range of transactions (should span roughly the last 365 days)
SELECT MIN(txn_ts) AS earliest_txn, MAX(txn_ts) AS latest_txn
FROM anycompany_demo.transactions;
