-- =============================================================================
-- Demo 2 teardown (run in database `dev`)
-- Removes the copy job and the landing table. Does NOT touch the rest of
-- anycompany_demo or the Serverless workgroup.
-- =============================================================================

-- Drop the copy job (cannot run inside a transaction block).
COPY JOB DROP anycompany_autocopy_txns;

-- Drop the landing table.
DROP TABLE IF EXISTS anycompany_demo.transactions_incoming;

-- Confirm the job is gone (should not list anycompany_autocopy_txns).
COPY JOB LIST;

-- -----------------------------------------------------------------------------
-- Also clean up outside Redshift (run in your shell, not here):
--
--   aws s3 rm "s3://$DEMO_BUCKET/$DEMO_PREFIX/" --recursive --region "$AWS_REGION"
--   # and, if you created a throwaway bucket:
--   aws s3 rb "s3://$DEMO_BUCKET" --region "$AWS_REGION"
--
-- If you set up an S3 event integration (Path B), delete it from the
-- Redshift console → Integrations, and remove the bucket policy statement.
-- -----------------------------------------------------------------------------
