# Corporate actions are sourced by cross-validating two weak signals

Neither available source is sufficient alone, so we use both and treat their
disagreement as a data-quality signal. The exchange's company page declares
Bonus Issues and Rights Issues as a percentage against a *year*. The Day End
Archive reveals an Ex-Date as an observable price step but gives a noisy factor.
We take the factor from the declaration and the Ex-Date from the price data, and
alert when they disagree.

## Considered Options

Detecting Corporate Actions from price movement alone was tested and rejected as
insufficient. The exchange applies a Circuit Limit of 10% per Trading Day, so any
Adjustment Factor below about 1.11 produces a step indistinguishable from an
ordinary bad day. Measured over 121 Trading Days and 77,053 instrument-day
comparisons: 54 instruments moved exactly -10%, only 8 moved beyond -10.5%.

Deriving factors from the exchange's Previous Close was tested and rejected
outright. Previous Close is mechanically the prior Trading Day's Close Price with
no adjustment ever applied — 77,053 comparisons produced zero exceptions,
including across a confirmed Bonus Issue. Corporate Actions are invisible in it.

## Consequences

The Ex-Date signal is specific: a Record Date on which the instrument Did Not
Trade, immediately followed by an opening gap that breaches the Circuit Limit.
All four Corporate Actions observed in six months match that shape, and the
sharpest of them cross-validates exactly — UTTARABANK declared a 25% Bonus Issue
and the observed step on 2026-05-21 implies a factor of 1.251.

Below the Circuit Limit we are blind, and Cash Dividends are far below it. This
is a permanent limitation of the sources, not a gap to be closed later, so it is
made visible rather than hidden: where a declared Corporate Action cannot be
matched to an observed Ex-Date, that instrument's series is marked
adjustment-incomplete from that date backwards, and the flag is exposed to
consumers. Adjustment Coverage is a published property of the data.

Both facts above were measured against live data in September 2026 and should be
re-tested if the exchange changes its Circuit Limit.
