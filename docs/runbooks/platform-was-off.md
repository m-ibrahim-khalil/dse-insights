# Catching up after an outage

The machine was off, or the platform was down, for more than a day or two.

## Why this one is urgent

Everything else in this project is recoverable whenever you get to it. This is
not. The exchange serves a **rolling two-year window**, so a trading day that
ages out before it is captured is gone — not from this warehouse, from anywhere.
Catch up promptly, then worry about the rest.

## Do this

```bash
make up
```

A short outage needs nothing more: every run re-covers a three-day trailing
window, so the next scheduled run heals a gap of a day or two by itself.

For anything longer, capture first — it is the irreplaceable half:

```bash
uv run python ingestion/capture_day_end.py --days 30 --landing landing/dse/day_end
```

Then bring the warehouse up to date, either with a backfill:

```bash
docker compose exec airflow-scheduler \
  airflow backfill create --dag-id dse_market_daily \
  --from-date 2026-09-01 --to-date 2026-09-20 \
  --max-active-runs 1 --run-backwards
```

or, if you only need the warehouse to match landing, directly:

```bash
make reload
```

**Mind the dates.** `--from-date` and `--to-date` are *logical* dates, and a
run's trading day is the day its interval **ends** — one day later. A backfill
from `2026-09-01` to `2026-09-03` processes trading days **09-02 and 09-03**.
Ask for the day before the one you want.

`--max-active-runs 1` keeps the backfill from putting a burst of load on a public
exchange site. `--run-backwards` does the newest dates first, which gets the
warehouse current soonest.

Re-running dates you already have is safe: loading replaces a trading day
atomically, so a backfill over existing dates leaves the warehouse
byte-identical.

## Check afterwards

```bash
ls landing/dse/day_end/*.html.gz | wc -l
```

Compare against **Days captured** and **Trading days held** on the dashboards —
they should agree. Then confirm **Freshness** is back to a couple of days.
