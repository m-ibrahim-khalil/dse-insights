-- Nothing here can legitimately be below zero. A negative price or volume means
-- a parsing sign error, and it should surface on the day it arrives.
--
-- Activity columns are checked on every row: on a non-traded day they are zero,
-- which is a fact and passes. Prices are checked only where they exist, since
-- they are null on a non-traded day.

select
    i.trading_code,
    f.trade_date,
    f.close_price,
    f.volume,
    f.turnover,
    f.trade_count
from {{ ref('fact_daily_price') }} f
join {{ ref('dim_instrument') }} i using (instrument_key)
where f.volume < 0
   or f.turnover < 0
   or f.trade_count < 0
   or f.open_price        < 0
   or f.high_price        < 0
   or f.low_price         < 0
   or f.close_price       < 0
   or f.last_traded_price < 0
   or f.previous_close    < 0
