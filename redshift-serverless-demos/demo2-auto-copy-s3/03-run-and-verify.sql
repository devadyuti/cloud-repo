-- =============================================================================
-- Demo 2: verify the auto-copy load
-- Run these AFTER uploading a batch file to the S3 prefix.
-- =============================================================================

-- 1) With the S3 event integration active, loads happen automatically when
--    files land in the watched prefix. No manual COPY JOB RUN is needed.
--    (COPY JOB RUN is not allowed while auto copy is enabled.)
--    If rows show 0 below, wait ~30 seconds and re-run — auto-detection
--    takes a moment after file upload.

-- 2) The rows from the uploaded file should now be present.
SELECT COUNT(*) AS rows_loaded FROM anycompany_demo.transactions_incoming;
SELECT * FROM anycompany_demo.transactions_incoming ORDER BY transaction_id;

-- 3) Job-level view: definition, state, run counts.
COPY JOB SHOW anycompany_autocopy_txns;

-- 4) System views — which files were loaded, and load history.
--    SYS_COPY_JOB: registered jobs.  SYS_LOAD_HISTORY: per-file load records.
SELECT * FROM sys_copy_job;

SELECT table_name, data_source, loaded_rows, status, start_time
FROM sys_load_history
ORDER BY start_time DESC
LIMIT 20;

-- 5) File-level commits + any errors (useful if a file fails to load).
--    Note: stl_load_errors requires superuser. Use sys_load_error_detail instead.
SELECT query_id, file_name, line_number, column_name, error_code, error_message
FROM sys_load_error_detail
ORDER BY start_time DESC
LIMIT 20;

-- 6) Optional: aggregate the freshly ingested data (nice closer)
SELECT channel, COUNT(*) AS txns, ROUND(SUM(amount),2) AS total_amount
FROM anycompany_demo.transactions_incoming
GROUP BY channel
ORDER BY total_amount DESC;
