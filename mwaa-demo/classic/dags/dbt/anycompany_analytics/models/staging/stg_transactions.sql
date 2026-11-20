-- Cleaned, typed transactions. One row per transaction.
select
    transaction_id,
    customer_id,
    cast(amount as decimal(12, 2))      as amount,
    lower(trim(region))                 as region,
    cast(date as date)                  as transaction_date,
    lower(trim(category))               as category,
    -- Signed amount: withdrawals and fees reduce the customer's balance
    case
        when lower(trim(category)) in ('withdrawal', 'fee') then -cast(amount as decimal(12, 2))
        else cast(amount as decimal(12, 2))
    end                                 as signed_amount
from {{ ref('raw_transactions') }}
