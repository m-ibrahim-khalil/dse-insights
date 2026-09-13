# DSE Market Intelligence Platform

> **Status:** MVP not started. Daily capture is running.
> **Goal:** An end-to-end data platform over Dhaka Stock Exchange market data, built
> to be operated and explained — not to accumulate technologies.

Vocabulary is defined in [CONTEXT.md](./CONTEXT.md). Decisions are in
[docs/adr/](./docs/adr/). This document holds scope and sequence only.

---

## 1. What we actually know about the source

Verified against the live endpoint, not inferred from documentation. These facts
drove most of the decisions below and several of them contradict what this plan
originally assumed.

| | |
|---|---|
| **Endpoint** | `day_end_archive.php?startDate=&endDate=&inst=All Instrument&archive=data` |
| **One request returns** | every instrument for a date range — ~710 KB, 636 rows for one day |
| **Rendering** | server-side HTML. `requests` + `BeautifulSoup` is enough; no browser needed |
| **Columns** | `DATE, TRADING CODE, LTP, HIGH, LOW, OPENP, CLOSEP, YCP, TRADE, VALUE (mn), VOLUME` |
| **History** | **rolling two-year window.** 2010 and 2015 return zero rows |
| **Instruments** | 636, including bonds — not ~300, and not all companies |
| **Non-traded** | ~39% of daily rows have OHLC of zero with close/previous close populated |
| **Trading week** | Sunday–Thursday |
| **Rate limiting** | none observed over ~40 requests |
| **TLS** | chain is incomplete — the intermediate certificate must be pinned |
| **Turnover unit** | BDT **millions**, not BDT |
| **Circuit limit** | ±10% per Trading Day. 54 moves at exactly −10% in 6 months, only 8 beyond −10.5% |
| **Previous Close** | mechanically the prior close, **never adjusted** — 77,053 comparisons, zero exceptions |
| **Corporate actions** | declared on company pages as a percentage against a *year*, back to 2005 |

Two of these shape everything:

**The archive window is a deadline.** A trading day not captured is lost once it
ages out. This is why capture runs before the platform exists, and why landing
stores original bytes ([ADR 0002](./docs/adr/0002-landing-holds-original-bytes.md)).

**39% of rows did not trade.** Zero is not a price. This is a modelling problem
before it is a validation problem ([ADR 0006](./docs/adr/0006-did-not-trade-is-modelled.md)).

---

## 2. Architecture

```text
  CC BY 4.0 historical seed          DSE day-end archive
  (2012 → early 2026, adjusted)      (rolling 2 years, daily)
            │                                  │
            └──────────────┬───────────────────┘
                           ▼
                    landing  ── original response bytes, immutable
                           ▼
                    raw      ── one table per feed, mirrors the source
                           ▼
                    staging  ── typed, deduplicated, our language
                           ▼
                  intermediate
                           ▼
                    marts    ── dim_instrument, fact_daily_price, …
                           ▼
                    FastAPI
```

Python owns everything above `raw`. dbt owns everything below it
([ADR 0004](./docs/adr/0004-python-ingests-dbt-transforms.md)). These five layer
names are the only ones used; bronze/silver/gold are not working vocabulary
([ADR 0003](./docs/adr/0003-layer-vocabulary.md)).

---

## 3. The MVP

One sentence: **a daily price history for every DSE instrument, correct enough to
trust, queryable over HTTP.**

Done when all of these are true:

- [ ] Daily capture has been running unattended for a month, with gaps visible
- [ ] Historical seed loaded and reconciled against the archive where they overlap
- [ ] `raw` loads are idempotent — rerunning a date changes nothing
- [ ] `dim_instrument` and `fact_daily_price` exist, at a stated grain
- [ ] Non-traded days are flagged, not zeroed and not dropped
- [ ] dbt tests cover uniqueness, nullability, and OHLC sanity on traded rows
- [ ] One FastAPI endpoint returns a price series for one instrument
- [ ] A new machine can reproduce all of it from the README

**Orchestration and observability are in the MVP** (decided 2026-09-12, revising
an earlier decision to defer them):

- [ ] The whole platform comes up with one command
- [ ] Airflow runs capture → load → dbt as one dependent pipeline, on a schedule
- [ ] Each dbt model and assertion is its own task, so the lineage is visible
- [ ] Backfill and catch-up are possible from the UI
- [ ] A failure, and staleness without a failure, reach a human
- [ ] Prometheus and Grafana show both pipeline health and data health
- [ ] Runbooks exist for each failure mode

The earlier reasoning — that Airflow waits until there is more than one thing to
schedule with a dependency between them — was engineering-first and sat badly
against §2's stated career goal. It was also overtaken: capture became automated
while load and dbt stayed manual, and the warehouse silently drifted behind
landing within two days. The condition has been met, and the goal always wanted
this. See `docs/tickets/orchestration/`.

Still explicitly **not** in the MVP: S3, technical indicators, news, a dashboard
over the *data*, AWS, CI beyond capture. Each has a place in §4 and a reason for
being there.

### Grain

`fact_daily_price` is one row per instrument per trading day. `(trading_code,
trade_date)` is unique. A row exists whether or not the instrument traded.

---

## 4. After the MVP, in order

Each step is here because of a problem, not because it is a well-known tool.

**1. Reconciliation.** Two sources overlap for ~18 months. Do they agree? This is
the first real data-quality work and it produces a genuine finding either way.

**2. Trading calendar.** Derived from which dates return rows, because the
published holiday calendar contradicts itself and includes dates that depend on
lunar observation. Needed before "is data missing?" can be answered at all.

**3. Data quality and freshness.** Meaningful once the calendar exists, because
until then "no data today" and "no session today" are indistinguishable.

**4. Testing and CI.** Parser tests first — the column order is a live trap.

*(Airflow, Docker and observability were steps 3, 5 and 9 here. They moved into
the MVP — see §3.)*

**5. Corporate action feed.** A second landing feed over company pages, giving
declared Bonus Issues and Rights Issues. Combined with Ex-Dates detected from
price steps, this produces the Adjustment Factor table
([ADR 0009](./docs/adr/0009-corporate-actions-by-cross-validation.md)).

**6. Technical indicators.** Needs step 5 — computing an RSI on an unadjusted
series produces confident, wrong numbers
([ADR 0010](./docs/adr/0010-price-return-not-total-return.md)).

**7. AWS.** As a deliberate exercise, not as hosting. A VPS is cheaper and enough.

**8. Dashboard.** Constrained by [ADR 0001](./docs/adr/0001-two-sources-and-private-data.md)
— it may only show data we are licensed to show.

---

## 5. Open questions

Unresolved. Each blocks something in §4. Price adjustment used to head this
list; it is now settled in ADRs
[0008](./docs/adr/0008-adjusted-prices-are-derived.md),
[0009](./docs/adr/0009-corporate-actions-by-cross-validation.md) and
[0010](./docs/adr/0010-price-return-not-total-return.md).

**Historical seed methodology.** Whether the CC BY 4.0 dataset genuinely carries
an unadjusted series, and what adjustment method its adjusted series uses. If the
method is undocumented we take its unadjusted prices and apply our own factors
uniformly, rather than joining two methodologies at a seam. Unverified — needs
research.

**Ex-date reach.** Company pages declare Bonus Issues back to 2005, but Ex-Dates
can only be detected inside the Archive Window. Actions declared before roughly
2024 have a factor and no observable date, so the Historical Seed period may be
adjustable only where the seed itself already accounts for it.

**Reconciliation policy.** When the two sources disagree on a close price, which
wins, and is the disagreement recorded or silently resolved?

**First endpoint shape.** What `GET /instruments/{trading_code}/prices` actually
returns — how much, in what order, paginated how.

**Instrument renames.** Assumed to rewrite history under current codes, based on
endpoint behaviour rather than an observed case
([ADR 0005](./docs/adr/0005-instrument-is-the-entity.md)). Needs a real example.

---

## 6. Working rules

**ADR first.** For any decision worth an ADR, the ADR gets written — by hand, in
your own words — before the implementation. The build is agentic; the reasoning
is not. Every question in §8 is a decision question, and delegated decisions
cannot be defended.

**Re-derive one thing per phase.** After each step in §4, pick something and
rebuild it from an empty file without assistance.

**Before adding any technology:** what problem does it solve, what did we try
first, what does it cost, and can that be explained in two sentences?

---

## 7. Not doing

Recorded so the decision is visible, not to be revisited quietly.

**Machine learning and an LLM analyst.** Removed from the plan. An unfinished ML
phase reads worse than an absent one, and the platform is the point. If the data
platform is finished, operated, and reliable, this can be reconsidered from a
position of strength.

**Kafka, Spark, Kubernetes.** No streaming source, no dataset that exceeds one
Postgres instance, no deployment complexity. Roughly 11 MB of compressed source
data accrues per year. Adding any of these would be a claim we could not defend.

**News.** Deferred until prices are trustworthy. It multiplies sources and adds
NLP to a project whose value is data engineering.

**A public price API.** Prohibited by the source's terms
([ADR 0001](./docs/adr/0001-two-sources-and-private-data.md)).

---

## 8. Interview questions this project should answer

The real output. If the project cannot answer these, it has not worked.

- Why is the fact grain one row per instrument per trading day, including days
  with no trades?
- Why does landing hold HTML rather than Parquet?
- What happens when the source renames an instrument?
- How do you know yesterday's data is complete?
- Why is the closing price not the last traded price?
  ([ADR 0007](./docs/adr/0007-close-price-is-the-official-close.md))
- What breaks if you compute a moving average on unadjusted prices?
- Why is there no Spark in this project?
- How would you recover if the pipeline had been silently broken for a month?
- What did the two sources disagree about?

---

## 9. Skills this is meant to build

In priority order: SQL depth (window functions, query plans, indexing),
dimensional modelling, data quality, Python for ingestion, dbt, Airflow, Docker,
AWS. Depth over coverage — one platform explained thoroughly beats eight tools
listed.

---

## Appendix — original plan

The first draft of this document is at `git show 99d7224:PLAN.md`. It contains
the long-form architecture sketches, the full analytics catalogue, the ML and AI
phases, and the learning roadmap. Kept for reference; superseded by this file.
