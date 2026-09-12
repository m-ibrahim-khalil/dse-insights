# Adjusted prices are derived, never stored

`fact_daily_price` holds Unadjusted Prices only, and is immutable once loaded.
Corporate Actions live in their own append-only table carrying instrument,
Ex-Date and Adjustment Factor. Adjusted Prices are computed in `intermediate`
from those two, and rebuilt in full whenever the Corporate Action table changes.

## Consequences

The obvious design is an `adjusted_close` column on the fact table. It is wrong
in a way that takes months to notice.

An Adjusted Price is not a fact about a Trading Day. It is a function of every
Corporate Action that has happened *since* that day, so it changes retroactively.
When an instrument declares a Bonus Issue next May, every adjusted price in its
history changes. Stored as a column, yesterday's query result differs from
today's with no row having been updated and nothing in the warehouse recording
why — the precise failure that makes people stop trusting a warehouse.

Keeping the Corporate Action table append-only means any historical adjusted view
can be reconstructed as of a past date, which is what makes it possible to
investigate a number someone saw last month.

The cost is that no adjusted price is available without a join, and the
`intermediate` rebuild is a full refresh rather than incremental.
