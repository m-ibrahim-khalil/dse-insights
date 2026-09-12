# Close Price means the exchange's official close

`close_price` is the exchange's published closing price. The last traded price is
kept as its own column, `last_traded_price`, and is never used as the close.

## Consequences

The exchange publishes both, and they differ — the official close is weighted, the
last traded price is simply the final execution. Every return, moving average and
indicator in the project depends on which one is chosen, and the choice is
invisible once it is buried in a model.

We choose the official close because it is the value the published previous close
compares against, so our computed returns reconcile against the exchange's own
numbers rather than drifting from them by an unexplained amount.

Price adjustment is a separate and unresolved problem: the exchange publishes no
adjustment factor, bonus issues and splits are common, and every indicator is
wrong on an unadjusted series. See the open question in PLAN.md; it will get its
own ADR.
