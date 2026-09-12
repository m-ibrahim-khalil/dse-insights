# 08 — Runbooks for when it is red

**What to build:** Documentation for operating the thing, written for the person
who finds it broken — which will usually be its author, months later, having
forgotten everything.

**Blocked by:** 03 — Each dbt model is its own task; 04 — Backfill and catch-up
from the UI; 05 — A failure reaches a human; 07 — Two dashboards

**Status:** ready-for-agent

- [ ] A runbook per failure mode: capture failed, load refused a day, an
      assertion failed, data is stale, the platform was off for a week
- [ ] Each one states how to confirm the diagnosis before acting
- [ ] Each one states what to check afterwards to confirm the fix
- [ ] The README shows the platform coming up and the first run, with screenshots
- [ ] Architecture documentation reflects the orchestrated shape, not the manual one
