-- =============================================================================
-- Demo 2: create the auto-copy job
-- Run AFTER 01-setup.sql. Run this BEFORE uploading any files
-- (a COPY JOB only ingests files created after the job exists).
--
-- Provisioned for account 123456789012 (profile amplify-dev, region eu-west-1):
--   bucket   : any-company-demo-autocopy-123456789012
--   IAM role : arn:aws:iam::123456789012:role/any-company-demo-autocopy-role
-- =============================================================================

-- Notes / constraints for COPY JOB:
--   * IAM_ROLE must be an explicit ARN (namespace default role is NOT used).
--   * MAXERROR / IGNOREALLERRORS / manifest / key-based auth are NOT allowed.
--   * IGNOREHEADER, FORMAT CSV, TIMEFORMAT etc. are fine.
--
-- IMPORTANT: This Redshift version requires an S3 EVENT INTEGRATION for AUTO ON
-- ("ERROR: Cannot find integration for bucket ..."). For the demo we use AUTO OFF
-- and trigger loads with `COPY JOB RUN` (deterministic, no integration needed).
-- To get true hands-off loading, set up the S3 event integration (see 00-prereqs.md
-- Path B) and then ALTER the job to AUTO ON:  COPY JOB ALTER anycompany_autocopy_txns AUTO ON;

COPY anycompany_demo.transactions_incoming
FROM 's3://any-company-demo-autocopy-123456789012/any-company-demo/auto-copy/incoming/'
IAM_ROLE 'arn:aws:iam::123456789012:role/any-company-demo-autocopy-role'
FORMAT AS CSV
IGNOREHEADER 1
TIMEFORMAT 'auto'
JOB CREATE anycompany_autocopy_txns
AUTO OFF;

-- Inspect the job you just created
COPY JOB LIST;
COPY JOB SHOW anycompany_autocopy_txns;
