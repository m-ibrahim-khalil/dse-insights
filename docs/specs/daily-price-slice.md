# Spec — First vertical slice: daily price history over HTTP

**Status:** ready-for-agent
**Scope:** Day End Archive → landing → raw → staging → marts → one HTTP endpoint
**Vocabulary:** [CONTEXT.md](../../CONTEXT.md) · **Decisions:** [docs/adr/](../adr/)

---

## Problem Statement

Landed Day End Archive responses are accumulating daily, and they are the only
copy that will exist once each Trading Day ages out of the Archive Window. Right
now they are opaque: gzipped HTML on disk that nobody can query, validate, or
read a price out of. There is no way to answer "what did this Instrument close
at last Tuesday", no way to know whether a Trading Day was captured completely
or at all, and no way to detect that the capture has been silently producing
garbage.

Every later ambition — reconciliation, indicators, freshness monitoring, an
analytical API — is blocked on the same missing thing: a trustworthy price
history in a database, with the transformation from source bytes to modelled
fact being something that can be re-run, inspected, and defended.

## Solution

Turn landed bytes into a queryable daily price history, and expose one endpoint
over it.

A load step reads landed responses and writes them into `raw` without
interpretation. dbt turns `raw` into a typed `staging` model, then into
`dim_instrument` and `fact_daily_price`. One HTTP endpoint returns the price
series for a single Instrument.

The slice deliberately uses a single source. It does not load the Historical
Seed, does not adjust prices, and does not reconcile anything — those depend on
decisions that are still open, and building on them now would bake in a guess.

What the slice does establish is the shape everything else plugs into: the layer
boundaries, the grain, the treatment of Instruments that Did Not Trade, and the
place where data assertions live.

## User Stories

**Getting data into the warehouse**

1. As a platform operator, I want landed responses loaded into `raw` without
   interpretation, so that a parsing mistake can be corrected by re-reading
   landing rather than by refetching data that no longer exists.
2. As a platform operator, I want to re-run a load for a Trading Day I have
   already loaded and see nothing change, so that recovering from a failure
   never means reasoning about duplicates.
3. As a platform operator, I want to load a range of Trading Days in one
   command, so that catching up after an outage is one action.
4. As a platform operator, I want a load to record which landed file each `raw`
   row came from, so that any surprising number can be traced back to the exact
   bytes it came from.
5. As a platform operator, I want a load that encounters a malformed landed file
   to fail loudly for that file and continue with the others, so that one bad
   response does not block a week of recovery.
6. As a platform operator, I want to see how many rows were read and how many
   were written for each Trading Day, so that a silent partial load is visible.
7. As a maintainer, I want the load to refuse to write a Trading Day whose row
   count is implausibly low, so that a truncated response is caught before it
   reaches the warehouse rather than after.

**Trusting the numbers**

8. As an analyst, I want the Close Price to be the exchange's official close and
   never the Last Traded Price, so that my returns reconcile against the
   exchange's own published figures.
9. As an analyst, I want the Last Traded Price kept as its own value, so that the
   difference between it and the Close Price remains available rather than
   discarded.
10. As an analyst, I want an Instrument that Did Not Trade to have no Open, High,
    Low or Close Price at all, rather than a price of zero, so that averages and
    other aggregates over my series are not silently dragged toward zero.
11. As an analyst, I want an Instrument that Did Not Trade to keep its Previous
    Close, so that I can tell the difference between "listed but untraded" and
    "not listed".
12. As an analyst, I want an Instrument that Did Not Trade to still have a row on
    that Trading Day, so that a gap in my series means a gap in the data and not
    merely a quiet day.
13. As an analyst, I want Turnover expressed in taka, so that I never have to
    remember that the source publishes millions.
14. As an analyst, I want Volume and Trade Count as whole numbers, so that they
    can be summed without surprise.
15. As an analyst, I want prices that the source formats with thousands
    separators parsed correctly, so that a price above a thousand is not silently
    truncated or rejected.
16. As an analyst, I want to know which Trading Days are present in the warehouse,
    so that I can tell a missing day from an untraded one before drawing a
    conclusion from a chart.

**Modelling**

17. As an analyst, I want one row per Instrument per Trading Day, so that I know
    the grain of what I am querying without inspecting it.
18. As an analyst, I want each Instrument to have a stable key that does not
    change when the exchange changes its Trading Code, so that history does not
    fracture on a rename.
19. As an analyst, I want to look an Instrument up by its Trading Code, so that I
    can use the identifier the market actually uses.
20. As an analyst, I want to know when an Instrument was first and last seen in
    the data, so that a delisting or a new listing is visible in the dimension
    rather than inferred from the fact.
21. As a maintainer, I want the dimension to describe Instruments rather than
    companies, so that bonds and funds are not misrepresented as issuers.
22. As a maintainer, I want the project's own language used from `staging`
    onward, so that source quirks like `CLOSEP` and `YCP` stop at the boundary.

**Assertions**

23. As a maintainer, I want a failing assertion when the same Instrument appears
    twice on the same Trading Day, so that a duplicate load is impossible to miss.
24. As a maintainer, I want a failing assertion when a Trading Code or Trading
    Day is null, so that unusable rows cannot enter the marts.
25. As a maintainer, I want OHLC sanity assertions that apply only to Instruments
    that traded, so that the 39% of rows that Did Not Trade do not produce a
    permanent wall of false failures.
26. As a maintainer, I want an assertion that High is not below Low, Open or
    Close on rows that traded, so that a transposed column is caught by the
    warehouse and not by a reader noticing something odd.
27. As a maintainer, I want an assertion that Volume and Turnover are never
    negative, so that a parsing sign error surfaces immediately.
28. As a maintainer, I want an assertion that every fact row points at an
    Instrument that exists in the dimension, so that the star schema cannot rot.
29. As a maintainer, I want the assertions to run against production data and not
    only in tests, so that a bad source day is caught in operation.

**Reading it back**

30. As a data consumer, I want to request the price series for one Instrument by
    its Trading Code, so that I can chart or analyse it.
31. As a data consumer, I want to bound the series by a date range, so that I do
    not have to fetch years to look at a month.
32. As a data consumer, I want the series ordered by Trading Day, so that I can
    use it without sorting it.
33. As a data consumer, I want days on which the Instrument Did Not Trade to be
    identifiable in the response, so that I can decide myself whether to skip or
    carry them.
34. As a data consumer, I want an unknown Trading Code to produce a clear
    not-found response, so that a typo is distinguishable from an Instrument with
    no price history.
35. As a data consumer, I want a malformed date range rejected with a reason, so
    that I can correct the request.
36. As a data consumer, I want a documented response schema, so that I can build
    against it without reading the implementation.
37. As a maintainer, I want the endpoint to have a version in its path, so that
    the response shape can change later without breaking existing callers.

**Reproducing it**

38. As a maintainer, I want to bring up an empty warehouse, load a fixture, build
    the models and query the endpoint from documented commands, so that the
    project is reproducible on a machine that has never run it.
39. As a maintainer, I want the whole slice runnable without any cloud account,
    so that local development has no external dependency.

## Implementation Decisions

**Layer responsibilities.** Python reads landing and writes `raw`, coercing to
text and nothing more. Every derivation from `raw` onward is dbt SQL, per
[ADR 0004](../adr/0004-python-ingests-dbt-transforms.md). The load step
contains no business rule — not the Turnover unit conversion, not the Did Not
Trade determination, not the zero-to-null substitution. All of those are
`staging` concerns.

**`raw` shape.** One table per source feed, mirroring the Day End Archive's
published columns under their published names, all text. It additionally carries
provenance: the landed file the row came from, its content hash, and the load
timestamp. `raw` is never corrected in place; a fix is a reload.

**Idempotency.** The unit of loading is a Trading Day. Loading a Trading Day
replaces that day's `raw` rows atomically — delete-then-insert inside one
transaction, keyed on the Trading Day. This is chosen over per-row upserts
because the source publishes a complete day at a time, so a day is the natural
unit of truth, and because it makes a shrinking row count self-correcting rather
than leaving orphaned rows from a previous larger load.

**Staging model.** One `staging` model over the `raw` price feed. It performs:
type coercion; thousands-separator removal; renaming to project vocabulary;
Turnover conversion from millions to taka; determination of `did_not_trade`; and
substitution of null for the zeroed Open, High, Low, Close, Volume, Turnover and
Trade Count on rows that Did Not Trade. Previous Close survives that
substitution. See
[ADR 0006](../adr/0006-did-not-trade-is-modelled.md).

**Did Not Trade rule.** An Instrument Did Not Trade on a Trading Day when its
Volume and Trade Count are both zero. Volume alone is not sufficient — the rule
should not depend on a single field being reliable — and Open Price being zero is
a symptom rather than the definition.

**Close Price.** `close_price` is the exchange's official close;
`last_traded_price` is carried separately and is never substituted for it, per
[ADR 0007](../adr/0007-close-price-is-the-official-close.md).

Prices in this slice are unadjusted, and the models must say so in their
descriptions so that no consumer mistakes them for a continuous series. This is
now a permanent property of the fact table rather than a simplification: adjusted
prices are always derived and never stored, per
[ADR 0008](../adr/0008-adjusted-prices-are-derived.md). Nothing about this slice
changes when adjustment arrives — it gains a sibling model, not a column.

**`dim_instrument`.** Surrogate `instrument_key`, natural key `trading_code`,
plus first-seen and last-seen Trading Day. Built from the distinct Trading Codes
observed in the price feed, because the Day End Archive publishes no name,
sector, type or category. `instrument_type`, `sector` and category are therefore
**not** populated in this slice and must not be guessed from the Trading Code —
enriching the dimension needs the exchange's listing feed, which is a separate
feed and out of scope. Per
[ADR 0005](../adr/0005-instrument-is-the-entity.md), no Issuer dimension.

**`fact_daily_price`.** Grain is one row per Instrument per Trading Day, carrying
`instrument_key` and `trade_date` plus Open, High, Low, Close, Last Traded Price,
Previous Close, Volume, Turnover, Trade Count and `did_not_trade`. Unique on
`(instrument_key, trade_date)`. Rows exist for Instruments that Did Not Trade.

**No `dim_date` yet.** A date dimension is only meaningful once the Trading
Calendar is derived, and that is a later step with its own open question. Until
then `trade_date` is a plain date and "which days exist" is answered from the
fact itself.

**Materialisation.** Everything is a table or view chosen for simplicity; no
incremental models in this slice. The dataset is small enough that a full rebuild
is fast, and incremental models introduce a class of correctness bug that is not
worth taking on before the shape is settled.

**API contract.** A versioned path returning the price series for one Trading
Code, with optional start and end date bounds, ordered ascending by Trading Day.
Response rows use project vocabulary, prices are nullable, and `did_not_trade` is
present on every row. Unknown Trading Code returns not-found; invalid dates
return a validation error naming the offending parameter. Read-only; no write
endpoints. Per
[ADR 0001](../adr/0001-two-sources-and-private-data.md) this endpoint is
not exposed publicly.

**Pagination is deferred, deliberately.** A single Instrument's full history
within the Archive Window is a few hundred rows, so bounding by date is
sufficient and pagination would be speculative. Revisit when the Historical Seed
lands and a series can span a decade.

## Testing Decisions

**What makes a good test here.** A test asserts what a consumer of the platform
can observe — the numbers that come back — and never how they were produced. It
does not know whether parsing happened in one function or five, whether the load
uses delete-then-insert or upserts, or what the `staging` model is called.
Renaming a model or restructuring the parser must not break a single test. A test
that would have to change because the implementation improved is a test that will
be deleted the first time it is inconvenient.

**Seam 1 — the pipeline, end to end.** The primary and only code-test seam.
Input is a landing fixture; output is the HTTP response. Parsing, the `raw` load,
the dbt build and the query all sit behind it as implementation.

It covers:

- Exact Open, High, Low, Close, Last Traded Price and Previous Close for named
  Instruments on named Trading Days. These assertions are what catch a column
  transposition, and they matter because the source publishes its columns in the
  order Last Traded Price, High, Low, Open, Close — so a parser that assumes OHLC
  produces plausible, correctly typed, wrong numbers that no schema assertion
  would reject.
- An Instrument that Did Not Trade returning null prices with the flag set and
  its Previous Close intact.
- Turnover in taka, verifying the millions conversion happened exactly once.
- A price with a thousands separator parsed to the right magnitude.
- Loading the same Trading Day twice leaving the fact row count and contents
  identical.
- Loading a range covering a non-trading day succeeding, with no rows for it.
- An unknown Trading Code returning not-found.
- A date range narrowing the series.

**Seam 2 — dbt data assertions.** Not a test of code. These are contracts on the
data, they run in operation as well as in development, and their job is to fail
when a source day is bad. Uniqueness on the fact grain; not-null on Trading Code,
Trading Day and the fact's foreign key; referential integrity from fact to
dimension; OHLC sanity and non-negative Volume and Turnover restricted to rows
that traded.

**No parser seam.** Rejected deliberately. Seam 1's exact-value assertions catch
a transposition just as reliably, and a dedicated parser seam would freeze the
parser's signature — the part most likely to change when the Historical Seed
arrives with an entirely different shape. If Seam 1 proves too slow to run
often, a parser seam is the first thing to add back, and that is the trigger to
add it.

**The fixture.** A hand-reduced Day End Archive response of roughly five
Instruments, not a real captured day.
[ADR 0001](../adr/0001-two-sources-and-private-data.md) keeps exchange
data out of this repository, and a reduced fixture is better test design anyway:
it is chosen to cover a normally traded Instrument, one that Did Not Trade, a
price carrying a thousands separator, a Turnover that exercises the unit
conversion, and a Trading Code long enough to catch column truncation. Each
fixture row exists because it encodes a trap.

**Prior art.** None — this is the first test in the repository, so it sets the
convention rather than following one. The existing capture script has no tests
and is not in scope to gain any here.

## Out of Scope

- **The Historical Seed.** Blocked on the price-adjustment question. Loading it
  now would force that decision by accident.
- **Price adjustment and corporate actions.** Decided in
  [ADR 0008](../adr/0008-adjusted-prices-are-derived.md)–[0010](../adr/0010-price-return-not-total-return.md)
  but not built here. Prices in this slice are unadjusted and labelled as such,
  which is their permanent state.
- **Reconciliation between sources.** There is only one source in this slice.
- **The Trading Calendar**, and therefore any freshness or completeness check
  that needs to know whether a session was held.
- **Enriching `dim_instrument`** with name, sector, type or category — needs the
  listing feed.
- **Instrument rename handling.** The surrogate key makes it possible later; no
  alias table is built until a rename has actually been observed.
- **Airflow, Docker, CI, S3, AWS, observability.** Sequenced in PLAN.md §4, each
  behind a problem this slice does not have.
- **Technical indicators, returns, market statistics.** Blocked on adjustment.
- **News, dashboards, machine learning.** See PLAN.md §7.
- **Pagination, authentication, caching, rate limiting** on the endpoint.
- **Changes to the capture script.** It runs; it is not touched here.

## Further Notes

**The parser is the highest-risk component and the least likely to fail loudly.**
Every other failure mode in this slice announces itself — a load crashes, an
assertion fails, an endpoint 500s. A column transposition produces a complete,
correctly typed, fully valid price history that is wrong. The exact-value
assertions in Seam 1 are the only thing standing between that and a warehouse
nobody has reason to doubt. They should be written first.

**Two source quirks are easy to fix twice.** Turnover in millions and prices with
thousands separators both invite a fix in the loader and another in `staging`,
which either double-converts or cancels out confusingly. Both belong in
`staging` only, and the Seam 1 assertions on magnitude are what catch a
double conversion.

**`raw` is text on purpose.** It will be tempting to coerce numerics during the
load because the source columns look numeric. Doing so moves a business decision
— what a zero means — above the layer boundary, and makes a malformed value a
load failure rather than a visible bad row.

**This slice makes several PLAN.md §8 questions answerable.** The grain question,
the landing-format question, the close-versus-last-traded question and the
non-traded-row question are all settled and demonstrable once this is built. The
completeness question is not, and cannot be until the Trading Calendar exists.
