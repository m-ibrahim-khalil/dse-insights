# Runbooks

Written for the person who finds this broken, which will usually be its author
some months later, having forgotten everything.

Each one starts with how to *confirm* the diagnosis, because the symptoms
overlap: a stale warehouse looks the same whether capture stopped, the load
stopped, or the exchange was closed. Acting on the wrong one wastes the only
thing that matters here — time inside the archive's rolling two-year window.

| The symptom | The runbook |
|---|---|
| A task went red in Airflow | [Capture failed](capture-failed.md) |
| A day was refused, nothing written | [A day was refused](day-refused.md) |
| A dbt assertion failed the build | [An assertion failed](assertion-failed.md) |
| Freshness is climbing, nothing failed | [Data is stale](data-stale.md) |
| The machine was off for days | [Catching up after an outage](platform-was-off.md) |
| Airflow will not start | [Airflow is broken](airflow-broken.md) |

## The one rule

**The archive is a rolling two-year window.** Everything else here is
recoverable at leisure; a trading day that ages out before it is captured is
gone permanently. When triaging, deal with capture first and the warehouse
second — the warehouse can always be rebuilt from landing, and landing cannot be
rebuilt from anything.
