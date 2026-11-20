# Stream 2 — Security (Lake Formation personas)

This document covers the multi-session persona roles used for the Stream 2
security exercises: how to switch into them, the region gotcha, and the
Lake Formation access model that was validated.

- **Account:** `123456789012`
- **Region:** `eu-west-1` (Ireland) — all data-lake resources live here
- **Assuming principal:** the account `admin` role (`arn:aws:iam::123456789012:role/admin`)

The persona roles are created by `templates/stream-2-security.yaml` (deployed as
stack `mda-pre-setup` — the stack name predates the file rename). Lake Formation
grants / data cell filters / LF-Tags are applied during the security exercises
(see "Access model validated" below).

## Persona roles

| Role | Purpose | Managed policies |
|------|---------|------------------|
| `mda-SalesManagerUS` | Sales manager, scoped to US data (row-level) | S3FullAccess, AthenaFullAccess |
| `mda-SalesManagerUK` | Sales manager, scoped to UK data (row-level) | S3FullAccess, AthenaFullAccess |
| `mda-DataAnalyst` | Broad analyst; column-level PII masking | S3FullAccess, AthenaFullAccess, DataZoneFullUserAccess |
| `mda-SalesAnalyst` | Sales-scoped analyst | S3FullAccess, AthenaFullAccess |

All four also carry an inline `LakeFormationQueryAccess` policy (LF query APIs +
Athena query/workgroup actions) and trust the `admin` role for `sts:AssumeRole`.

## Switching into the personas (region-pinned links)

**Important — region gotcha:** the AWS console "Switch Role" flow does *not*
inherit your current region. Without a pinned region it can land the session in
a different region (e.g. Stockholm / `eu-north-1`), where none of our resources
exist — you then see only the `primary` Athena workgroup and an empty catalog
tree. The links below pin `region=eu-west-1` so every switch lands in Ireland.

Bookmark these (colors are the console swatch; adjust as you like):

```
# SalesManagerUS (red)
https://signin.aws.amazon.com/switchrole?account=123456789012&roleName=mda-SalesManagerUS&displayName=SalesManagerUS&color=F2B0A9&region=eu-west-1

# SalesManagerUK (blue)
https://signin.aws.amazon.com/switchrole?account=123456789012&roleName=mda-SalesManagerUK&displayName=SalesManagerUK&color=99BCE3&region=eu-west-1

# DataAnalyst (green)
https://signin.aws.amazon.com/switchrole?account=123456789012&roleName=mda-DataAnalyst&displayName=DataAnalyst&color=B7CA9D&region=eu-west-1

# SalesAnalyst (yellow)
https://signin.aws.amazon.com/switchrole?account=123456789012&roleName=mda-SalesAnalyst&displayName=SalesAnalyst&color=FAD791&region=eu-west-1
```

### Making eu-west-1 the default more broadly

Pinning the links above is per-bookmark. To default *all* console sessions
(including switched roles) to Ireland in your browser:

1. Top-right region menu → **Change default Region** (or Unified Settings →
   Localization → Default Region).
2. Select **Europe (Ireland) eu-west-1** and enable "always use this Region".

Existing switch-role history entries were saved without a region — remove and
re-add them via the pinned URLs above so the saved shortcuts carry the region.

> Note: landing region is a console/browser behavior, not a property of the IAM
> role. It cannot be set on the role or in CloudFormation.

## Athena Query Editor notes

- **Catalog / data source dropdown:** only `AwsDataCatalog` (the default Glue
  Data Catalog) is registered as an Athena data source, so it's the only entry.
  The account has other Glue catalogs (from unrelated workshops) that show in
  Lake Formation but are not registered in Athena — ignore them. `None` is just
  the unselected placeholder.
- The **left-nav tree** is empty until you select the Data source
  (`AwsDataCatalog`) and a Database. If it stays empty for a principal that can
  still run queries, check the region is `eu-west-1` and hard-refresh.
- Queries run through `mda-workgroup` (results: `s3://mda-stage-123456789012-eu-west-1/athena-results/`).

## Access model validated

All grants below are on the default account Glue catalog, `eu-west-1`.

- **Role-based (named resource):** each persona granted `DESCRIBE` on the
  database(s) it should see + `SELECT` on the permitted table(s). A persona sees
  a database in the Athena dropdown only if it holds `DESCRIBE` on that database
  (table SELECT alone is not enough).
- **DataAnalyst column-level PII masking:** data cell filter
  `mda-stage_customers_pii` on `stage.stage_customers` excludes the sensitive
  columns `address`, `birthday`, `email`. DataAnalyst sees only `stage` →
  `stage_customers`, with those columns hidden.
- **SalesManagerUS / SalesManagerUK:** row-level scoping so each sees only its
  region's rows.
- **Tag-based access control (LF-TBAC):** validated via LF-Tags and tag-based
  grants.

> The Lake Formation grants, data cell filters, and LF-Tags are currently
> live-account state (applied via the console/CLI during the exercises) and are
> not yet captured in a template. To make Stream 2 reproducible, these can be
> codified later (LF-Tags and tag associations are template-able; some grants
> are more practical as documented CLI steps).
