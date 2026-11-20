-- One row per customer, enriched with lifetime activity.
with activity as (
    select
        customer_id,
        count(*)                                                            as transaction_count,
        sum(signed_amount)                                                  as net_balance,
        sum(case when category = 'investment' then amount else 0 end)       as total_invested,
        min(transaction_date)                                               as first_transaction_date,
        max(transaction_date)                                               as last_transaction_date
    from {{ ref('stg_transactions') }}
    group by 1
)

select
    c.customer_id,
    c.customer_name,
    c.segment,
    c.home_region,
    c.onboarded_date,
    coalesce(a.transaction_count, 0)    as transaction_count,
    coalesce(a.net_balance, 0)          as net_balance,
    coalesce(a.total_invested, 0)       as total_invested,
    a.first_transaction_date,
    a.last_transaction_date
from {{ ref('stg_customers') }} c
left join activity a using (customer_id)
