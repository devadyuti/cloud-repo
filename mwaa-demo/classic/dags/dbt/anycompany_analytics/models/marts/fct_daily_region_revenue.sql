-- Daily totals per region and category. Grain: transaction_date x region x category.
select
    transaction_date,
    region,
    category,
    count(*)                as transaction_count,
    sum(amount)             as gross_amount,
    sum(signed_amount)      as net_amount
from {{ ref('stg_transactions') }}
group by 1, 2, 3
