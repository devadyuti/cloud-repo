-- =============================================================================
-- Demo 2 setup: target table for auto-copy ingestion
-- Run in database `dev` (same as Demo 1). Reuses the anycompany_demo schema.
-- Re-runnable.
-- =============================================================================

-- Landing table for files arriving from the "pipeline" (S3 prefix).
DROP TABLE IF EXISTS anycompany_demo.transactions_incoming;

CREATE TABLE anycompany_demo.transactions_incoming (
    transaction_id   INTEGER        NOT NULL,
    member_id        INTEGER        NOT NULL,
    merchant_id      INTEGER        NOT NULL,
    txn_ts           TIMESTAMP,
    amount           DECIMAL(10,2),
    cashback_earned  DECIMAL(10,2),
    channel          VARCHAR(20)
);

-- Confirm it starts empty (auto-copy will fill it).
SELECT COUNT(*) AS starting_rows FROM anycompany_demo.transactions_incoming;
