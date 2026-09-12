# DSE Market Intelligence Platform

A data platform over Dhaka Stock Exchange market data: daily prices captured,
loaded, modelled, asserted, and served over HTTP.

Built to be **operated and explained**, not to accumulate technologies. Every
non-obvious decision has an [ADR](docs/adr/) saying why the obvious approach was
wrong.

---

## Quick start

From a fresh clone to a queried price series. Requires Docker and
[uv](https://docs.astral.sh/uv/); nothing else, and no cloud account.

```bash
uv sync                    # install pinned dependencies (uv.lock)
make db-up                 # start the warehouse, create the layer schemas
make test                  # loads a fixture, builds the models, queries the API
```

`make test` is the honest proof the platform works: it drives a landed response
all the way to an HTTP response. If it passes, everything below will too.

To serve real data:

```bash
python ingestion/capture_day_end.py --days 7 --landing landing/dse/day_end
uv run python -m ingestion.load_day_end --landing landing/dse/day_end
cd dbt && uv run dbt build && cd ..
make api
```

```bash
curl 'localhost:8000/v1/instruments/GP/prices?start_date=2026-09-01'
curl localhost:8000/v1/trading-days
open http://localhost:8000/docs        # the published schema
```

`make db-down` destroys the warehouse and everything in it.

---

## How data moves

```
     DSE day-end archive  (rolling 2-year window)
                │
                ▼
   landing   original response bytes, gzipped, never modified
                │           ingestion/capture_day_end.py
                ▼
   raw       one table per feed, the exchange's own column names, all text
                │           ingestion/load_day_end.py
                ▼
   staging   typed, renamed into this project's vocabulary
                │
                ▼
   marts     dim_instrument, fact_daily_price
                │           dbt
                ▼
   FastAPI   read-only price series
```

Those five names are the only layer vocabulary in the project. Bronze, silver
and gold are not used ([ADR 0003](docs/adr/0003-layer-vocabulary.md)) — three
overlapping vocabularies for the same thing is how a pipeline becomes
unexplainable.

**Python owns everything above `raw`; dbt owns everything below it**
([ADR 0004](docs/adr/0004-python-ingests-dbt-transforms.md)). Python fetches
bytes, lands them, and loads them with no coercion beyond "make it text". Every
join, derivation and business rule after that is SQL. That constraint is what
keeps the lineage graph honest.

---

## Things that will surprise you

Each of these has already invalidated an assumption, and each is why some piece
of the code looks the way it does.

**The source column order is `LTP, HIGH, LOW, OPENP, CLOSEP` — not OHLC.**
A parser that assumes OHLC produces plausible, correctly typed, wrong prices
that no schema assertion rejects. This is the highest-risk failure in the
project, which is why `tests/expectations.py` asserts every price field exactly
and why every value in the fixture differs from every other on its row.

**The archive is a rolling two-year window.** A trading day not captured is
unrecoverable. That is why capture runs on a schedule before the rest of the
platform existed, and why `landing` stores original bytes rather than parsed
Parquet — a parsing bug found in month eighteen is fixable by reparsing, but not
by refetching ([ADR 0002](docs/adr/0002-landing-holds-original-bytes.md)).

**Roughly 39% of daily rows did not trade.** Open, high, low and last traded
price arrive as zero. Zero is not a price, so they become NULL and
`did_not_trade` is set; left as zero they would drag every moving average toward
zero across a third of the data with nothing failing
([ADR 0006](docs/adr/0006-did-not-trade-is-modelled.md)).

But the **close survives**, because the exchange publishes one even for
instruments that never trade. `TB10Y0127`, a treasury bond, has never traded in
the window and still closed at 97.38, 97.40, 96.97, 97.49 on consecutive days —
a valuation. Nulling it would erase the only price such instruments have.
Volume, turnover and trade count stay zero, because zero is the truth.

**The close is not the last traded price.** The exchange publishes both and they
differ; `close_price` is the official weighted close, which is what the published
previous close compares against
([ADR 0007](docs/adr/0007-close-price-is-the-official-close.md)).

**Turnover is published in millions of taka.** Converted once, in `staging`.
Converting again in the loader would silently multiply by a million.

**636 instruments, not ~300 companies** — including bonds and treasury bills. The
dimension is `dim_instrument`, never `dim_company`
([ADR 0005](docs/adr/0005-instrument-is-the-entity.md)).

**The exchange's TLS chain is incomplete.** It omits its Sectigo intermediate, so
`ingestion/certs/` pins it. `curl` only appears to work because it chases the
certificate's AIA URL. Do not "fix" this by disabling verification.

---

## Prices are unadjusted

`fact_daily_price` holds **unadjusted prices and always will**. There is
deliberately no `adjusted_close` column.

An adjusted price is not a fact about a trading day — it is a function of every
corporate action *since* that day. Stored as a column, a bonus issue declared
next year silently changes prices you published this year, with no row updated
and nothing recording why. So adjusted series are derived, never stored
([ADR 0008](docs/adr/0008-adjusted-prices-are-derived.md)).

Series are **price return**, never total return: cash dividends are never
adjusted for ([ADR 0010](docs/adr/0010-price-return-not-total-return.md)). The
API says so in every response, as `price_basis`.

Adjustment is decided but not yet built. See [PLAN.md](PLAN.md) §4.

---

## Grain

`fact_daily_price` is **one row per instrument per trading day**, unique on
`(instrument_key, trade_date)`. A row exists whether or not the instrument
traded, so a gap in a series means missing data rather than a quiet day.

---

## Data assertions

These are contracts on the data, not tests of code. They run in `dbt build`, in
operation, and their job is to fail when the exchange publishes something wrong.

| Assertion | Scope |
|---|---|
| Grain is unique | every row |
| Trading code, trade date, flag not null | every row |
| Every fact resolves to an instrument | every row |
| High is highest, low is lowest | traded rows only |
| Nothing is negative | every row |

The OHLC rules are restricted to traded rows because an unrestricted
`high >= close` evaluates `0 >= 1060` on a non-traded row and fails on 39% of
the data. A test that fails on a third of the data is a test that gets switched
off. Each assertion is watched failing against deliberately corrupt data in
`tests/test_value_assertions.py` — a green suite says nothing about an assertion
that could never fire.

---

## Configuration

All configuration is environment-driven. `make db-up` creates `.env` from
[.env.example](.env.example), which lists every variable. No credential is
committed, and `.env` is gitignored.

**Exchange data never enters this repository.** The exchange permits personal,
non-commercial use and prohibits redistribution, so `landing/` is gitignored, the
capture workflow commits to a separate private repo, and there is no public price
endpoint. Test fixtures are hand-built responses of a few instruments, never a
captured day ([ADR 0001](docs/adr/0001-two-sources-and-private-data.md)).

---

## Where to look

| | |
|---|---|
| [PLAN.md](PLAN.md) | scope, sequence, what is deliberately not built, open questions |
| [CONTEXT.md](CONTEXT.md) | the glossary. Prescriptive: terms to use, and to avoid |
| [docs/adr/](docs/adr/) | ten decisions, each because the obvious approach was wrong |
| [docs/specs/](docs/specs/) | the spec for this slice |
| [docs/tickets/](docs/tickets/) | how it was broken down and built |
