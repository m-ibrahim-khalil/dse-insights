# Data is stale, and nothing failed

The alert said the data is behind, but every task is green. This is the failure
the project actually fears — the loud ones look after themselves.

## Confirm it, and tell the two cases apart

The alert already distinguishes them, and they need opposite responses:

| Alert | Meaning |
|---|---|
| `landing is N days behind` | **Capture** stopped, or the machine was off |
| `warehouse is N days behind landing` | Capture works; the **load** does not |

Check directly:

```bash
ls -t landing/dse/day_end/*.html.gz | head -1     # newest captured
make db-shell -- -c "select max(trade_date) from marts.fact_daily_price;"
```

## Before acting: is the exchange even open?

Freshness climbs every weekend. The exchange trades **Sunday to Thursday**, so
three days old on a Saturday is perfectly healthy, and the alert threshold
allows for it. There are also Saturday sessions — three occurred in the two years
to September 2026 — so never infer the calendar from the weekday.

## Do this

**Landing behind:** see [capture failed](capture-failed.md), then
[catching up](platform-was-off.md) if it has been days.

**Warehouse behind landing:** the load or the dbt build stopped. Check the DAG,
then catch up directly:

```bash
make reload
```

## Check afterwards

**Days behind landing** returns to zero and **Freshness** drops back to its
sawtooth — climbing over the weekend, dropping on Sunday. A flat, high freshness
line means it is still broken.
