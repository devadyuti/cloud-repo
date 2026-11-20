-- =============================================================================
-- Demo 3: consume the datashare on the CONSUMER (provisioned analytics-cluster)
-- Run on analytics-cluster (database `dev`, user awsuser) AFTER 02-create-share.sql.
--
-- Producer namespace (source of the share): 0a84a6f2-df5c-42ff-a5c4-83c12b5b8f37
-- Consumer namespace (this side): <CONSUMER_NAMESPACE_GUID>
-- =============================================================================

-- 1) See the datashares available to this namespace (the producer's share appears here).
SHOW DATASHARES;
SELECT share_name, producer_namespace, producer_account
FROM svv_datashares
WHERE share_type = 'INBOUND';

-- 2) Mount the share as a local database. Nothing is copied — this is a pointer to
--    the producer's live data.
--    Redshift DROP DATABASE has NO "IF EXISTS". Re-running? Uncomment the next line
--    first (errors harmlessly the first time, when the database doesn't exist yet):
-- DROP DATABASE anycompany_shared;

CREATE DATABASE anycompany_shared
    FROM DATASHARE anycompany_share
    OF NAMESPACE '0a84a6f2-df5c-42ff-a5c4-83c12b5b8f37';

-- 3) Query the producer's data live via three-part names: db.schema.table
SELECT COUNT(*) AS rows_visible_over_share
FROM anycompany_shared.anycompany_demo.transactions_incoming;

SELECT *
FROM anycompany_shared.anycompany_demo.transactions_incoming
ORDER BY transaction_id;

-- 4) A real analytics query, running on the PROVISIONED cluster against SERVERLESS data.
SELECT channel,
       COUNT(*)              AS txns,
       ROUND(SUM(amount), 2) AS total_amount,
       ROUND(SUM(cashback_earned), 2) AS total_cashback
FROM anycompany_shared.anycompany_demo.transactions_incoming
GROUP BY channel
ORDER BY total_amount DESC;

-- 5) LIVE PROOF (optional, the "wow"):
--    On the PRODUCER, insert one row:
--        INSERT INTO anycompany_demo.transactions_incoming VALUES
--          (100999, 999, 5, GETDATE(), 12.34, 0.62, 'online');
--    Then re-run the COUNT here on the CONSUMER — it goes up immediately, no reload.
