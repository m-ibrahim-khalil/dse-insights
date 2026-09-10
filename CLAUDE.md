# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A data platform over Dhaka Stock Exchange (DSE) market data. It is currently
**documentation plus one running script**: `ingestion/capture_day_end.py` captures
the exchange's day-end archive daily via GitHub Actions. Nothing below `landing`
exists yet — no warehouse, no dbt project, no API.

Read these before writing code:

- `PLAN.md` — scope, sequence, what is deliberately *not* being built, open questions
- `CONTEXT.md` — the project glossary. It is prescriptive: it lists terms to use and terms to **avoid**
- `docs/adr/` — the decisions. Ten ADRs; each one exists because the obvious approach was wrong
- `docs/specs/daily-price-slice.md` — the spec for the next piece of work (`ready-for-agent`)

## Commands

```bash
pip install -r ingestion/requirements.txt        # just certifi

# Capture the last N days into landing (default 7 days, landing/dse/day_end)
python ingestion/capture_day_end.py --days 7 --landing <path>
```

There is no test suite, linter, or build yet. The first tests will be written as
part of the daily-price slice; `docs/specs/daily-price-slice.md` defines their
seams, and its "Prior art: none" note means whatever is written sets the convention.

## Architecture

```
CC BY 4.0 historical seed          DSE day-end archive
(2012 → early 2026, adjusted)      (rolling 2 years, daily)
          └──────────────┬───────────────────┘
                landing  ── original response bytes, immutable
                raw      ── one table per feed, mirrors the source, all text
                staging  ── typed, deduplicated, project vocabulary
                intermediate
                marts    ── dim_instrument, fact_daily_price
                FastAPI
```

**Python owns everything above `raw`; dbt SQL owns everything below it**
(ADR 0004). Python may fetch bytes, land them, and load them into `raw` with no
coercion beyond "make it text". No pandas transformations, no Python-computed
indicators, no SQL in Python beyond the load statement. This is a hard constraint,
not a preference — it is what keeps the lineage graph honest.

Those five layer names are the only vocabulary. Bronze/silver/gold are not used
anywhere (ADR 0003).

## Source facts that break naive code

These are verified against the live endpoint and each one has already invalidated
an assumption:

- **Column order is `LTP, HIGH, LOW, OPENP, CLOSEP` — not OHLC.** A parser that
  assumes OHLC produces plausible, correctly typed, wrong prices that no schema
  test rejects. This is the highest-risk failure in the project.
- **Turnover is in BDT millions**, not BDT. Convert to taka in `staging` only —
  never also in the loader, or it double-converts.
- **~39% of daily rows did not trade**: open, high, low and last traded price
  arrive as zero, while close and previous close are populated. Zero is not a
  price, so in `staging` those four become NULL and `did_not_trade` is set. The
  close and previous close are KEPT as published, and volume, turnover and trade
  count are kept as zero -- zero is the truth about activity. The rule is "fields
  the exchange zeroes become NULL; fields it populates are kept". Do not null the
  close: the exchange publishes a daily valuation for instruments that never
  trade, and for a treasury bond it is the only price that exists. OHLC
  assertions must be restricted to `WHERE NOT did_not_trade` or they fail on a
  third of all rows (ADR 0006).
- **`close_price` is the exchange's official (weighted) close.** `last_traded_price`
  is a separate column and is never substituted for the close (ADR 0007).
- **The archive is a rolling two-year window.** A trading day not captured is
  unrecoverable. This is why capture runs before the platform exists and why
  `landing` stores original bytes rather than parsed Parquet — a parsing bug found
  in month eighteen is fixable by reparsing, not by refetching (ADR 0002).
- **636 instruments, not ~300 companies** — includes bonds and funds. The dimension
  is `dim_instrument`, keyed by surrogate `instrument_key` with `trading_code` as
  natural key. No `dim_company`, no issuer dimension yet (ADR 0005).
- **Previous Close is mechanically the prior close and is never adjusted** —
  77,053 comparisons, zero exceptions. Corporate actions are invisible in it, so
  do not try to derive adjustment factors from it (ADR 0009).
- **A ±10% circuit limit per trading day** means any adjustment factor below ~1.11
  produces a price step indistinguishable from an ordinary bad day. Corporate
  actions cannot be detected from price movement alone (ADR 0009).
- **The trading week is Sunday–Thursday, but not only.** Three Saturday sessions
  occurred in the two years to September 2026 (2025-05-17, 2025-05-24,
  2026-05-23), each with ~396 instruments actually trading. Never infer whether a
  date was a Trading Day from its weekday, and never from the exchange's
  published holiday page, which contradicts itself and carries moon-dependent
  dates. Derive it from which dates return rows.
- Prices may carry thousands separators.
- The instrument count is not fixed: 655 in May 2025, 643 in May 2026, 636 in
  September 2026. Anything comparing row counts across time must tolerate drift.
- The exchange's TLS chain is incomplete (omits its Sectigo intermediate), so
  `ingestion/certs/sectigo-dv-r36.pem` is pinned and loaded explicitly. Do not
  "fix" this by disabling verification; curl only appears to work because it
  chases the AIA URL.

## Exchange data never enters this repository

ADR 0001: the exchange permits personal, non-commercial download and prohibits
redistribution. `landing/` and `*.html.gz` are gitignored, and the CI workflow
commits landed files to a **separate private repo** (`vars.LANDING_REPO`,
currently `m-ibrahim-khalil/dse-insights-landing`) using a write-scoped deploy
key (`secrets.LANDING_DEPLOY_KEY`) rather than an account-wide token. This
repository is public, so the capture workflow must never gain a `pull_request`
trigger -- a fork's PR would then run with access to that key. Test
fixtures are hand-reduced responses of ~5 instruments, never a captured day.
There is no public price endpoint, and this is a design constraint rather than an
omission.

## Working rules from PLAN.md §6

- **ADRs are written by hand, by the repository owner, before implementation.**
  "The build is agentic; the reasoning is not." Propose that a decision needs an
  ADR; do not author one unasked.
- Before adding any technology, it must have a problem it solves, something tried
  first, a stated cost, and a two-sentence explanation.
- Airflow, Docker, S3, AWS, CI beyond capture, indicators, dashboards, news, ML,
  Kafka/Spark/Kubernetes are all explicitly out of the MVP and sequenced (or
  refused) in PLAN.md §4 and §7. Don't reach for them.

## Price adjustment

Settled in ADRs 0008–0010, and easy to get wrong:

- `fact_daily_price` holds **unadjusted prices only** and is immutable once loaded.
  There is no `adjusted_close` column — an adjusted price is a function of every
  corporate action since that day, so storing it makes history change silently
  (ADR 0008).
- Corporate actions live in their own **append-only** table (instrument, ex-date,
  adjustment factor). Adjusted prices are derived in `intermediate` and rebuilt in
  full whenever that table changes.
- Factors come from the exchange's declarations; ex-dates come from observed price
  steps. Where a declared action cannot be matched to an ex-date, the series is
  marked **adjustment-incomplete** from that date backwards and the flag is exposed
  to consumers (ADR 0009).
- Series are **price return**, never total return: cash dividends are never
  adjusted for, and models saying so is part of the contract (ADR 0010).

## Open questions that block work

The historical seed's adjustment methodology is unverified, ex-date detection
cannot reach before the archive window, and reconciliation policy and the first
endpoint's shape are open. See PLAN.md §5.
