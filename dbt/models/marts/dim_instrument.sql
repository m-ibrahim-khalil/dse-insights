-- An Instrument is the tradable thing with a trading code. Not a company: the
-- feed carries bonds and funds too, so a dim_company would be named after
-- something the data does not contain. ADR 0005.
--
-- The Day End Archive publishes no name, sector, type or category, so this
-- dimension carries none. They are not guessed from the trading code -- an
-- attribute that is right most of the time is worse than an absent one.

with observed as (
    select
        trading_code,
        min(trade_date) as first_seen_on,
        max(trade_date) as last_seen_on
    from {{ ref('stg_day_end') }}
    group by trading_code
)

select
    -- Surrogate key. Currently derived from the trading code, because no alias
    -- table exists yet; when renames are handled this becomes the stable anchor
    -- and the alias table maps codes onto it.
    md5(trading_code) as instrument_key,
    trading_code,
    first_seen_on,
    last_seen_on
from observed
