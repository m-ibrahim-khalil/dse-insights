-- The grain is one row per Instrument per Trading Day. A duplicate here means a
-- load wrote a day twice, which is the failure most likely to go unnoticed.
select instrument_key, trade_date, count(*) as rows
from {{ ref('fact_daily_price') }}
group by instrument_key, trade_date
having count(*) > 1
