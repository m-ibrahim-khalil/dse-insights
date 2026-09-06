# 07 — Value assertions on traded rows

**What to build:** The data assertions that depend on knowing whether an
Instrument traded. These are contracts on the data rather than tests of code —
they run in operation as well as in development, and their job is to fail when
the exchange publishes something wrong.

Every one of these must be scoped to rows that traded. Applied to all rows they
would fail permanently on roughly 39% of the data: a non-traded Instrument has a
High of null and a Close Price carrying its last known price, so an unscoped
"High is not below Close" rule fails on every one of them. That mistake is what
makes teams disable their own tests.

**Blocked by:** 03 — Instruments that Did Not Trade

**Status:** ready-for-agent

- [ ] High Price is not below Low, Open or Close Price, on traded rows only
- [ ] Low Price is not above Open or Close Price, on traded rows only
- [ ] Volume, Turnover and Trade Count are never negative
- [ ] Prices are never negative
- [ ] Assertions run against real loaded data, not only against the fixture
- [ ] A failing assertion names the Instrument and Trading Day that broke it
- [ ] A deliberately corrupted fixture row proves each assertion actually fires
