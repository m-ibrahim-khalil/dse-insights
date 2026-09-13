---
status: accepted and implemented; the reasoning below is the agent's and awaits the owner's
author: written by Claude, 2026-09-10, from measurements described below
supersedes: the original version of this ADR, which nulled the close
---

# Instruments that did not trade are stored, not filtered

> **On authorship.** PLAN.md §6 says ADRs are written by hand, by the repository
> owner, before implementation — "the build is agentic; the reasoning is not."
> This one was not. I wrote it, after implementing, from data I measured. It is
> recorded in my voice rather than the project's so that nobody mistakes the
> judgement in it for the owner's.
>
> The measurements are facts and will survive whoever rewrites this. The
> conclusions drawn from them are mine and are the part worth arguing with. The
> section "What would change my mind" exists so they can be attacked without
> re-deriving anything.

## Decision

A non-traded instrument keeps its row. An instrument counts as not having traded
when its volume and trade count are **both** zero.

At the `staging` boundary the fields the exchange zeroes — open, high, low, and
last traded price — become NULL, and a `did_not_trade` flag is set. Close price
and previous close are kept exactly as published. Volume, turnover and trade
count are kept as zero.

Stated as one rule rather than a list to memorise: **fields the exchange zeroes
become NULL; fields it populates are kept.** The rule is applied per row, not per
column — which is the part I got wrong the first time.

## What I measured

I pulled the day-end archive for **2026-03-01 to 2026-09-03**, measured on
2026-09-06 — 121 trading days, 77,705 instrument-days — and looked at every row
where volume and trade count were both zero. There were 30,292 of them, 39.0%
of the total.

The window is stated so the figures below can be reproduced or contradicted.
Re-running over a different window will not match exactly, and the archive is a
rolling two-year one, so this window will eventually age out of it entirely.

| Field on a non-traded row | Zero | Populated |
|---|---:|---:|
| last traded price, high, low, open | 30,292 | 0 |
| turnover | 30,292 | 0 |
| **close** | **3** | **30,289** |
| **previous close** | **0** | **30,292** |

Two further facts, both of which surprised me:

The close on a non-traded row is **not** the previous close carried forward. The
two differ on 25,104 of the 30,292 rows.

Following one instrument explains why. `TB10Y0127` is a ten-year treasury bond.
It has not traded once inside the archive window, and yet it closed at 97.38,
97.40, 96.97, 97.49 on consecutive days. The exchange publishes a daily
valuation for instruments that do not trade.

## What I concluded

**Zero is not a price, so the four zeroed price fields become NULL.** Left as
zero they would drag any moving average, return or volatility toward zero across
39% of their inputs — silently, with nothing failing. NULL propagates instead of
lying.

**Zero is the truth about activity, so volume, turnover and trade count stay
zero.** No shares changed hands. That is a fact, not missing data, and a zero in
a volume average is correct where a zero in a price average is not. I think the
instinct to null these alongside the prices is the most likely way this decision
gets quietly undone.

**The close is real information, so it is kept.** This is the conclusion I hold
most firmly and the one that most looks like an oversight from the outside. For
bonds, treasury bills and permanently illiquid listings, the published close is
the only price that will ever exist. Nulling it would put a NULL in the field
every downstream consumer reaches for first, and would leave a whole class of
instrument with no price at all.

**Price assertions must be scoped to traded rows.** `high >= close` evaluates
`0 >= 1060` on a non-traded row. Unscoped, it fails on a third of the data — and
a test that fails on a third of the data is a test somebody switches off.

**The rows are kept rather than filtered** because `raw` must mirror the source,
and because "listed, still priced, but nobody traded it" is information a
consumer may want.

## What would change my mind

- If the exchange's published close on a non-traded day turned out to be derived
  rather than observed — a model output rather than a settlement or reference
  price — then presenting it in the same column as a traded close would be
  mixing two different things, and it should move to a column of its own.
- If a consumer computing returns were found treating a non-traded close as a
  tradeable price, the flag is not doing its job and the contract needs to be
  louder than a boolean.
- ~~The three non-traded rows with a zero close are unexplained.~~ **Chased, and
  they were a category.** See below.

## Why the original version was wrong

The first version of this ADR contradicted itself. It stated that close and
previous close carry a price on non-traded rows, then listed close among the
fields to null. I wrote both sentences, and the nulling half was written before
I had measured anything — it was inherited from the assumption that a
non-traded row is empty.

That assumption is wrong for this exchange, and the disagreement between the two
halves of the document is the trace it left.


## Amendment, 2026-09-13: the zero closes were a category

The section above left three non-traded rows with a zero close unexplained, and
predicted that if they were a category rather than noise the rule would need a
case for them. Over the full two years there are twelve, and they are two
categories, both meaning *absent*:

- **An instrument's final day.** Five treasury bonds each show a zero close on
  exactly the day they were last seen, which is their maturity — `TB15Y1125` on
  2025-11-10, `TB2Y0626` on 2026-06-07, and so on. The instrument names encode
  the maturity and the data agrees.
- **A delisting after suspension.** `SALVOCHEM` traded normally to 2025-12-02,
  then posted seven consecutive sessions with a zero close and no trades, and was
  never seen again.

A zero *previous* close is the mirror image: 28 of 29 are an instrument's first
day, and the twenty-ninth is `TB2Y0727` returning after a 270-day absence. In
every case the exchange is saying "there was no prior session", not "the prior
close was zero".

The implementation had applied the rule to four columns rather than to whatever
the exchange actually zeroed, so these survived as genuine zeros. That is not a
cosmetic difference. A bond that matured at par reported a **-100% return** on
its final day, in a project whose entire argument is that zero is not a price.
Twelve rows, confidently wrong, and quiet for two years.

Both now become NULL, and an assertion —
`fact_daily_price_no_price_is_zero` — fails the build if a zero ever appears in
any price column again.
