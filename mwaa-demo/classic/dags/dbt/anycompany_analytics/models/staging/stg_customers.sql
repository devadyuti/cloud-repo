-- Cleaned customer reference data. One row per customer.
select
    customer_id,
    customer_name,
    lower(trim(segment))            as segment,
    lower(trim(home_region))        as home_region,
    cast(onboarded_date as date)    as onboarded_date
from {{ ref('raw_customers') }}
