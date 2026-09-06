-- The high must be the highest and the low the lowest, on days something traded.
--
-- Restricted to traded rows deliberately. On a non-traded day the exchange
-- zeroes open, high and low while still publishing a close, so an unrestricted
-- "high >= close" evaluates 0 >= 1060 and fails on roughly 39% of all rows
-- (ADR 0006). A test that fails on a third of the data is a test that gets
-- switched off.
--
-- Selecting the trading code and date means a failure names the instrument and
-- the day rather than only a count.

select
    i.trading_code,
    f.trade_date,
    f.open_price,
    f.high_price,
    f.low_price,
    f.close_price
from {{ ref('fact_daily_price') }} f
join {{ ref('dim_instrument') }} i using (instrument_key)
where not f.did_not_trade
  and (
        f.high_price < f.low_price
     or f.high_price < f.open_price
     or f.high_price < f.close_price
     or f.low_price  > f.open_price
     or f.low_price  > f.close_price
  )
