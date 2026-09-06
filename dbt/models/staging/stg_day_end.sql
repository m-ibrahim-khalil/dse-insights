-- The boundary where the source's language stops and the project's begins.
--
-- Everything the source does oddly is corrected here and only here: the column
-- order that is not OHLC, the thousands separators, and turnover published in
-- millions. Doing any of these again downstream would double-convert.

with source as (
    select * from {{ source('raw', 'day_end') }}
),

typed as (
    select
        trade_date::date                                  as trade_date,
        trading_code,

        -- The exchange's official (weighted) close. Not the last trade -- ADR 0007.
        {{ to_number('closep') }}                         as close_price,
        {{ to_number('ltp') }}                            as last_traded_price,
        {{ to_number('openp') }}                          as open_price,
        {{ to_number('high') }}                           as high_price,
        {{ to_number('low') }}                            as low_price,
        {{ to_number('ycp') }}                            as previous_close,

        {{ to_number('volume') }}::bigint                 as volume,
        {{ to_number('trade') }}::bigint                  as trade_count,

        -- Published in millions of taka. Converted once, here.
        {{ to_number('value_mn') }} * 1000000             as turnover

    from source
)

select
    *,
    -- An instrument was listed but nothing traded. Both fields, not either: the
    -- rule should not rest on a single source field being reliable. ADR 0006.
    (volume = 0 and trade_count = 0)                      as did_not_trade
from typed
