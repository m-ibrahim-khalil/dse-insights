# Instruments that did not trade are stored, not filtered

A non-traded instrument keeps its row. At the `staging` boundary its zeroed
open, high, low, close, volume and turnover become NULL, and a `did_not_trade`
flag is set. Previous close is retained.

## Consequences

About 39% of rows on a given trading day arrive with OHLC of zero while close and
previous close carry the last known price. Two things follow.

First, the price validation rules as originally written are wrong: `high >= close`
evaluates `0 >= 1060` and fails on every one of those rows. OHLC rules must apply
`WHERE NOT did_not_trade`.

Second, zero is not a price. Left as zero, those rows drag any moving average,
return or volatility toward zero on more than a third of their inputs — silently,
with no failing test. NULL propagates instead of lying.

We keep the rows rather than filtering them because `raw` must mirror the source,
and because "listed, still priced, but nobody traded it" is information.
