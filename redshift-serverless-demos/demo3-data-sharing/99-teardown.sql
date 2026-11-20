-- =============================================================================
-- Demo 3 teardown (SQL side)
-- Removes the mounted database on the consumer and the datashare on the producer.
-- Does NOT touch anycompany_demo itself or the Serverless workgroup.
--
-- NOTE: deleting the provisioned cluster is a shell action, not SQL. Run:
--         bash run-share.sh teardown
--       which runs this cleanup AND deletes analytics-cluster (~$0.543/hr).
-- =============================================================================

-- ---- On the CONSUMER (analytics-cluster, database `dev`) ----
-- Drop the local database that points at the share (no producer data is affected).
-- (Redshift DROP DATABASE has no IF EXISTS; ignore "database does not exist".)
DROP DATABASE anycompany_shared;

-- Remove the demo "live proof" row if you inserted it during the demo.
-- (Run this one on the PRODUCER.)
-- DELETE FROM anycompany_demo.transactions_incoming WHERE transaction_id = 100999;


-- ---- On the PRODUCER (default-workgroup, database `dev`; run as admin/superuser) ----
-- Drop the datashare. (No IF EXISTS in Redshift; ignore "datashare does not exist".)
DROP DATASHARE anycompany_share;

-- Confirm it's gone (should not list anycompany_share).
SHOW DATASHARES;

-- -----------------------------------------------------------------------------
-- Cluster deletion (run in your shell, NOT here) — this is the billable resource:
--
--   aws redshift delete-cluster \
--     --cluster-identifier analytics-cluster \
--     --skip-final-cluster-snapshot \
--     --profile demo-admin --region eu-west-1
--
-- `bash run-share.sh teardown` does the SQL cleanup above and this delete for you.
-- -----------------------------------------------------------------------------
