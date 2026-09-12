# 02 — Landed fixture to a queryable price fact

**What to build:** The narrow complete path from a landed Day End Archive
response to `fact_daily_price`. A reduced fixture loads into `raw` untouched, a
`staging` model types and renames it into project vocabulary, and
`dim_instrument` and `fact_daily_price` build on top. At the end of this ticket
the warehouse can answer "what did this Instrument close at on this Trading Day"
with the correct number.

The exact-value assertions land here, and they are the point of the ticket. The
source publishes its columns in the order Last Traded Price, High, Low, Open,
Close — so a parser assuming OHLC produces plausible, correctly typed, wrong
numbers that no schema assertion would catch. Assert real values for named
Instruments on named Trading Days, and keep those expected values in one place;
a later ticket reads the same expectations back over HTTP.

Structural assertions belong here too. A fact table without a uniqueness test on
its own grain is not finished.

Instruments that Did Not Trade are out of scope — the fixture rows for this
ticket are all traded rows. That is deliberate and the next ticket fixes it.

**Blocked by:** 01 — Warehouse and dbt skeleton

**Status:** ready-for-agent

- [ ] A hand-reduced fixture exists covering a handful of traded Instruments,
      including a price carrying a thousands separator and a Trading Code long
      enough to catch column truncation
- [ ] The fixture contains no bulk exchange data, per
      [ADR 0001](../../adr/0001-two-sources-and-private-data.md)
- [ ] Landed responses load into `raw` as text, with no interpretation, per
      [ADR 0004](../../adr/0004-python-ingests-dbt-transforms.md)
- [ ] Each `raw` row records which landed file it came from, that file's content
      hash, and when it was loaded
- [ ] A `staging` model types the feed, strips thousands separators, and renames
      every column into the vocabulary in [CONTEXT.md](../../../CONTEXT.md)
- [ ] Turnover is converted from millions to taka exactly once, in `staging`
- [ ] Close Price is the exchange's official close and Last Traded Price is kept
      separately, per [ADR 0007](../../adr/0007-close-price-is-the-official-close.md)
- [ ] `dim_instrument` has a surrogate key and Trading Code as its natural key,
      per [ADR 0005](../../adr/0005-instrument-is-the-entity.md)
- [ ] `dim_instrument` carries no name, sector, type or category, and none are
      guessed from the Trading Code
- [ ] `fact_daily_price` is one row per Instrument per Trading Day, holding
      Unadjusted Prices only, per
      [ADR 0008](../../adr/0008-adjusted-prices-are-derived.md)
- [ ] A test asserts exact Open, High, Low, Close, Last Traded Price and Previous
      Close for named Instruments on named Trading Days
- [ ] A test asserts Turnover in taka at the right magnitude, proving the
      conversion happened exactly once
- [ ] Data assertions enforce grain uniqueness, non-null Trading Code and Trading
      Day, and that every fact row resolves to an Instrument in the dimension
