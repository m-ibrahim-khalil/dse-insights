# 04 — Price series over HTTP

**What to build:** One read-only endpoint returning the price series for a single
Instrument by its Trading Code, optionally bounded by a date range, ordered
oldest first. This completes the end-to-end path and moves the project's test
seam to where it belongs: a landed fixture goes in, an HTTP response comes out,
and everything between is implementation.

The expected values asserted in ticket 02 are read back here over HTTP. They are
the same expectations, not new ones — only the access path differs.

The endpoint is not exposed publicly, per
[ADR 0001](../../adr/0001-two-sources-and-private-data.md).

**Blocked by:** 03 — Instruments that Did Not Trade

**Status:** ready-for-agent

- [ ] An endpoint returns the price series for one Trading Code
- [ ] The path carries a version, so the response shape can change later without
      breaking callers
- [ ] Optional start and end date bounds narrow the series
- [ ] Rows come back ordered by Trading Day, oldest first
- [ ] Prices are nullable and the Did Not Trade flag is present on every row
- [ ] Response fields use the vocabulary in [CONTEXT.md](../../../CONTEXT.md),
      never the source's column names
- [ ] Prices are documented in the response schema as unadjusted
- [ ] An unknown Trading Code returns a not-found response, distinguishable from
      a known Instrument with no rows in range
- [ ] An invalid or inverted date range is rejected with a message naming the
      offending parameter
- [ ] A machine-readable schema for the response is published
- [ ] A consumer can discover which Trading Days are present
- [ ] The seam-level test drives a landed fixture all the way to an HTTP response
