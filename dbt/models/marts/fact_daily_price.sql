-- Grain: one row per Instrument per Trading Day. A row exists whether or not the
-- instrument traded, so a gap in a series means missing data rather than a quiet
-- day.
--
-- Prices here are unadjusted, always. There is deliberately no adjusted_close
-- column: an adjusted price is a function of every corporate action since the
-- day in question, so storing it would make published history change silently.
-- Adjusted series are derived in intermediate. ADR 0008.

select
    i.instrument_key,
    s.trade_date,

    s.open_price,
    s.high_price,
    s.low_price,
    s.close_price,
    s.last_traded_price,
    s.previous_close,

    s.volume,
    s.turnover,
    s.trade_count,
    s.did_not_trade

from {{ ref('stg_day_end') }} s
join {{ ref('dim_instrument') }} i on i.trading_code = s.trading_code
