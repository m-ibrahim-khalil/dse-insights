# An assertion failed

A `*.test` task went red. The data reached the warehouse and is wrong.

## Confirm it

The task name says which model. The log says which rule:

```
FAIL 1 fact_daily_price_ohlc_is_sane
Got 1 result, configured to fail if != 0
```

Find the offending rows — every assertion selects the trading code and date
precisely so this is one query:

```bash
make db-shell
```

```sql
select i.trading_code, f.trade_date, f.open_price, f.high_price, f.low_price, f.close_price
from marts.fact_daily_price f
join marts.dim_instrument i using (instrument_key)
where not f.did_not_trade
  and (f.high_price < f.low_price or f.high_price < f.close_price);
```

## What it usually is

**The exchange published something wrong.** It happens. The assertion did its
job; the pipeline stopped rather than propagating it.

**A parser change.** If *many* rows fail at once, suspect the source's table
markup rather than the market. The column order is
`LTP, HIGH, LOW, OPENP, CLOSEP` — not OHLC — and a transposition produces
plausible, correctly typed, wrong prices. Reparse a landed file and compare
against `tests/expectations.py`.

**An assertion applied to the wrong rows.** OHLC rules must exclude non-traded
rows, which are roughly 39% of the data. If an assertion suddenly fails on a
third of everything, it is the rule that is wrong, not the market.

## Do this

Do **not** relax the assertion to make the build pass. If the source is wrong,
leave it failing and decide deliberately whether to exclude that row, correct
it in a model, or accept the gap.

Because landing is immutable, a parser fix is a reparse rather than a refetch:

```bash
make reload
```

## Check afterwards

`make reload` ends with `PASS=14 ERROR=0`, and **Failing assertions** on the
pipeline dashboard returns to zero.
