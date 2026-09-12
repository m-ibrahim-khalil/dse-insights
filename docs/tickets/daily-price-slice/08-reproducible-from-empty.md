# 08 — Reproducible from an empty machine

**What to build:** A path from a fresh clone to a queried price series using only
documented commands, on a machine that has never run this project and has no
cloud account. This is the ticket that turns a working pipeline into something
another person — or the author in six months — can actually operate.

**Blocked by:** 04 — Price series over HTTP; 06 — Load failure handling and a
row-count guard; 07 — Value assertions on traded rows

**Status:** ready-for-agent

- [ ] A README takes a reader from clone to a queried price series in order,
      with no undocumented step
- [ ] Every command in it is run on a clean checkout and verified to work
- [ ] Dependency versions are pinned, so a rebuild months later behaves the same
- [ ] Configuration is environment-driven and an example file lists every
      variable, with no real credentials
- [ ] The whole path runs with no cloud account and no external service beyond
      the exchange itself
- [ ] The layer names, grain and Did Not Trade treatment are explained where a
      reader meets them, with links to the ADRs that decided them
- [ ] The README states that prices are unadjusted and links to
      [ADR 0008](../../adr/0008-adjusted-prices-are-derived.md)
