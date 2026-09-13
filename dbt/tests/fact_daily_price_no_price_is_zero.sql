-- Zero is never a price, in any price column.
--
-- The exchange encodes absence as zero in more places than the obvious one. It
-- zeroes open, high, low and last-traded on any day an instrument did not trade,
-- and it also zeroes the close on an instrument's final day -- a bond reaching
-- maturity, or a delisting after suspension -- and the previous close on a first
-- day. Every one of those is absence, and every one must be null by the time it
-- reaches the marts.
--
-- This exists because a zero close survived the original rule for two years. It
-- was not loud: twelve rows, each reporting a -100% return on an instrument that
-- had matured at par.

select
    i.trading_code,
    f.trade_date,
    f.close_price,
    f.previous_close
from {{ ref('fact_daily_price') }} f
join {{ ref('dim_instrument') }} i using (instrument_key)
where 0 in (f.open_price, f.high_price, f.low_price,
            f.close_price, f.last_traded_price, f.previous_close)
