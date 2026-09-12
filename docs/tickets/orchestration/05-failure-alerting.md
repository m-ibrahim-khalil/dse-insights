# 05 — A failure reaches a human

**What to build:** When the pipeline breaks, or when data goes stale without
breaking, somebody finds out without opening the UI.

Both halves matter. A crashed task is loud. The failure this project actually
fears is quiet: the DAG succeeds every night while the exchange serves an error
page, or the machine is off for a week and nothing says so.

**Blocked by:** 02 — The market DAG runs the pipeline end to end

**Status:** done

- [x] A failed task raises an alert that names the DAG, the task and the date
- [x] An alert carries a link straight to the failed run's logs
- [x] Data older than an expected freshness threshold alerts even when no task failed
- [x] Alerts are rate-limited, so a week-long outage does not produce a week of noise
- [x] Alerting is configured from the environment, with no endpoint committed
