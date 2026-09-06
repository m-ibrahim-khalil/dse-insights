# 05 — Idempotent loading over a range of Trading Days

**What to build:** Loading many Trading Days in one command, and loading any of
them repeatedly without consequence. Recovering from a failed or partial load
should never require reasoning about duplicates — it should just mean running the
same command again.

The unit of loading is a Trading Day, because the source publishes a complete day
at a time. Loading a day replaces that day's rows atomically rather than merging
row by row, so a day that shrinks — an Instrument delisted between loads — leaves
no orphans behind.

**Blocked by:** 02 — Landed fixture to a queryable price fact

**Status:** ready-for-agent

- [ ] One command loads every landed Trading Day within a given range
- [ ] Loading a Trading Day already present replaces it rather than appending
- [ ] The replacement is atomic — an interrupted load leaves the previous state,
      never a partial one
- [ ] A test loads the same Trading Day twice and asserts the fact row count and
      contents are byte-identical afterwards
- [ ] A test loads a range spanning a date with no session and succeeds, with no
      rows for that date
- [ ] A Trading Day present in the range but absent from landing is reported, not
      silently skipped
