# 03 — Instruments that Did Not Trade

**What to build:** Correct handling for the roughly 39% of rows on any Trading
Day where an Instrument was listed but nothing traded. The source publishes these
with zeroed prices and a populated Close Price and Previous Close.

Zero is not a price. Left as zero it silently drags every average, return and
indicator toward zero across more than a third of its inputs, with no assertion
failing. After this ticket, a non-traded Instrument has no Open, High, Low or
Close Price at all, carries an explicit flag, and keeps its Previous Close.

The rows are kept rather than filtered: `raw` must mirror the source, and
"listed, still priced, nobody traded it" is information.

**Blocked by:** 02 — Landed fixture to a queryable price fact

**Status:** ready-for-agent

- [ ] The fixture gains at least one Instrument that Did Not Trade
- [ ] An Instrument counts as having Did Not Trade when both its Volume and its
      Trade Count are zero — not on either field alone
- [ ] Zeroed Open, High, Low, Close, Volume, Turnover and Trade Count become
      null at the `staging` boundary, per
      [ADR 0006](../../adr/0006-did-not-trade-is-modelled.md)
- [ ] Previous Close survives that substitution
- [ ] A row exists in `fact_daily_price` whether or not the Instrument traded
- [ ] `fact_daily_price` carries an explicit flag marking the condition
- [ ] A test asserts a non-traded Instrument has null prices, the flag set, and
      its Previous Close intact
- [ ] Grain uniqueness still holds with non-traded rows present
