-- =============================================================================
-- Demo 1 teardown: removes ONLY the demo schema and its objects.
-- This does NOT delete the Redshift Serverless workgroup/namespace.
-- (To stop compute charges, delete the workgroup — see 00-provision-serverless.md)
-- =============================================================================

DROP SCHEMA IF EXISTS anycompany_demo CASCADE;

-- Confirm it's gone (should return 0 rows)
SELECT nspname
FROM pg_namespace
WHERE nspname = 'anycompany_demo';
