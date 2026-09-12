# 04 — Backfill and catch-up from the UI

**What to build:** The ability to say "re-run the last three weeks" and have it
happen correctly, because each run is scoped to its own Trading Day rather than
to whatever "today" is when the task executes.

The loader is already idempotent per Trading Day and that is asserted, so this
ticket is about making the orchestrator hand each run the right date rather than
about changing the pipeline's safety.

**Blocked by:** 02 — The market DAG runs the pipeline end to end

**Status:** ready-for-agent

- [ ] Each run is parameterised by the Trading Day it is for, not by wall-clock today
- [ ] A backfill over a date range can be launched and produces one run per date
- [ ] Backfilled runs are limited in parallelism, so a backfill cannot hammer the source
- [ ] Re-running a date that already loaded leaves the warehouse byte-identical
- [ ] A date the exchange held no session on completes without writing anything
- [ ] The README documents how to recover after the platform has been off for a week
