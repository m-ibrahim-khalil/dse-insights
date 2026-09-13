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
),

flagged as (
    select
        *,
        -- Listed, but nothing traded. Both fields, not either: the rule should
        -- not rest on a single source field being reliable. ADR 0006.
        (volume = 0 and trade_count = 0)                  as did_not_trade
    from typed
)

select
    trade_date,
    trading_code,

    -- On a non-traded day the exchange zeroes these four. Zero is not a price of
    -- zero, it is the absence of a trade, so it becomes null: left as zero it
    -- would drag every moving average toward zero across 39% of all rows.
    case when did_not_trade then null else open_price        end as open_price,
    case when did_not_trade then null else high_price        end as high_price,
    case when did_not_trade then null else low_price         end as low_price,
    case when did_not_trade then null else last_traded_price end as last_traded_price,

    -- Close and previous close are normally populated even on a non-traded day,
    -- and are kept exactly as published. This is evidence-led: across two years
    -- the close is present on all but 12 non-traded rows, and it moves daily for
    -- instruments that never trade at all. TB10Y0127, a treasury bond, has never
    -- traded and yet closed at 97.38, 97.40, 96.97, 97.49 on consecutive days --
    -- a published valuation. Nulling it wholesale would erase the only price
    -- such instruments ever have.
    --
    -- But when the exchange DOES zero them, that is absence, not a price of
    -- zero, and the same rule applies as to the other four. A zero close marks
    -- an instrument's last day -- a bond reaching maturity, or a delisting after
    -- suspension -- and a zero previous close marks a first day, either a new
    -- listing or a return after a long absence. Left as 0, a bond that matured
    -- at par reports a -100% return on its final day.
    nullif(close_price, 0)                            as close_price,
    nullif(previous_close, 0)                         as previous_close,

    -- These really are zero on a non-traded day, and zero is the truth: no
    -- shares changed hands. Nulling them would lose that, and a zero volume in
    -- a volume average is correct where a zero price is not.
    volume,
    turnover,
    trade_count,

    did_not_trade
from flagged
