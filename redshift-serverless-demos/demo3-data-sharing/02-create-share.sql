-- =============================================================================
-- Demo 3: create the datashare on the PRODUCER
-- Run on the Serverless producer (default-workgroup, database `dev`) AFTER 01-setup.sql.
--
-- Producer namespace (this side): 0a84a6f2-df5c-42ff-a5c4-83c12b5b8f37
-- Consumer namespace (analytics-cluster): <CONSUMER_NAMESPACE_GUID>  <-- EDIT THIS
--   Get it with:  bash run-share.sh consumer-ns
--   (or: aws redshift describe-clusters --cluster-identifier analytics-cluster
--         --query 'Clusters[0].ClusterNamespaceArn')
-- =============================================================================

-- Notes / constraints:
--   * Producer and consumer must both be RA3 (Serverless is RA3-class).
--   * Same account => GRANT USAGE ... TO NAMESPACE is enough (no authorize/associate).
--   * Run this as a SUPERUSER / the owner of schema anycompany_demo (IAMR:admin). A
--     non-privileged user (e.g. IAM:amplify-dev) gets "cannot create datashare ...
--     permission denied".
--   * Redshift DROP DATASHARE has NO "IF EXISTS". Re-running this file? Uncomment the
--     next line first (it errors harmlessly the very first time, when nothing exists):
-- DROP DATASHARE anycompany_share;

-- 1) Create the datashare.
CREATE DATASHARE anycompany_share;

-- 2) Add the schema, then the table (schema must be added before its objects).
ALTER DATASHARE anycompany_share ADD SCHEMA anycompany_demo;
ALTER DATASHARE anycompany_share ADD TABLE anycompany_demo.transactions_incoming;
--   Alternatively share everything in the schema:
--   ALTER DATASHARE anycompany_share ADD ALL TABLES IN SCHEMA anycompany_demo;

-- 3) Grant it to the consumer namespace (same account).
GRANT USAGE ON DATASHARE anycompany_share
    TO NAMESPACE '<CONSUMER_NAMESPACE_GUID>';

-- 4) Inspect what you just published.
SHOW DATASHARES LIKE 'anycompany_share';
SELECT share_name, share_type, is_publicaccessible
FROM svv_datashares
WHERE share_name = 'anycompany_share';

-- Objects included in the share:
SELECT share_name, object_type, object_name
FROM svv_datashare_objects
WHERE share_name = 'anycompany_share'
ORDER BY object_type, object_name;

-- Who it's granted to (namespaces / accounts):
SELECT share_name, consumer_namespace, consumer_account, share_date
FROM svv_datashare_consumers
WHERE share_name = 'anycompany_share';
