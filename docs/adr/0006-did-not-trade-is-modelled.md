---
status: accepted (amended 2026-09-07, superseding the original nulling rule)
---

# Instruments that did not trade are stored, not filtered

A non-traded instrument keeps its row. An instrument counts as not having traded
when its volume and trade count are **both** zero.

At the `staging` boundary its three zeroed prices — open, high, low — and its
zeroed last traded price become NULL, and a `did_not_trade` flag is set.

**Close price and previous close are kept exactly as published.** Volume,
turnover and trade count are kept as zero.

## Consequences

Roughly 39% of rows on a given trading day did not trade, so how they are
modelled decides the shape of more than a third of the data.

**Zero is not a price.** Left as zero, the four zeroed price fields would drag
any moving average, return or volatility toward zero across a third of their
inputs — silently, with no failing test. NULL propagates instead of lying.

**But zero is the truth about activity.** No shares changed hands, and that is a
fact rather than missing data. A zero in a volume average is correct where a zero
in a price average is not, so volume, turnover and trade count stay zero.

**Price rules must be restricted to traded rows.** `high >= close` evaluates
`0 >= 1060` on a non-traded row and fails on every one of them. OHLC assertions
apply `WHERE NOT did_not_trade`, or they fail on a third of the data — and a test
that fails on a third of the data is a test that gets switched off.

The rows are kept rather than filtered because `raw` must mirror the source, and
because "listed, still priced, but nobody traded it" is information.

## Why the close survives

This is the part of the decision most likely to be reversed by someone tidying
up, so the evidence is recorded here. Measured across 30,292 non-traded rows
spanning 121 trading days:

| Field on a non-traded row | Zero | Populated |
|---|---:|---:|
| last traded price, high, low, open | 30,292 | 0 |
| turnover | 30,292 | 0 |
| **close** | **3** | **30,289** |
| **previous close** | **0** | **30,292** |

The close is not zeroed, and it is not merely the previous close carried
forward: the two differ on 25,104 of those rows.

The reason is that the exchange publishes a daily valuation for instruments that
do not trade. `TB10Y0127`, a ten-year treasury bond, has not traded once inside
the archive window, and closed at 97.38, 97.40, 96.97, 97.49 on consecutive days.
For instruments like it — bonds, treasury bills, permanently illiquid listings —
the published close is the **only** price that will ever exist.

Nulling it would erase that, and would put a NULL in the one field every
downstream consumer reaches for first.

## Amendment

The original version of this ADR listed close among the fields to null, while its
own first paragraph of consequences stated that close carries a price on those
rows. It contradicted itself, and the nulling half was written before the
non-traded rows had been measured.

The rule is now stated as: **fields the exchange zeroes become NULL; fields it
populates are kept.** That is a single rule rather than a list to remember, and
it stays correct if the exchange starts publishing a field it currently zeroes.
