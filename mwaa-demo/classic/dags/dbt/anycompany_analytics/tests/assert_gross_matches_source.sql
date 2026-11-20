-- Singular test: the mart's gross total must reconcile with the staging layer.
-- Returns rows (= test failure) only when the two totals differ.
with mart as (
    select sum(gross_amount) as total from {{ ref('fct_daily_region_revenue') }}
),
source as (
    select sum(amount) as total from {{ ref('stg_transactions') }}
)
select mart.total as mart_total, source.total as source_total
from mart cross join source
where mart.total <> source.total
