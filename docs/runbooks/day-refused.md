# A day was refused

The load reported `REFUSED` and wrote nothing for that trading day.

## Confirm it

This is the row-count guard, not a crash. It fires when a day holds fewer rows
than half the median of recent days. The message says both numbers:

```
REFUSED 2026-09-14: 2026-09-14.html.gz: 41 rows against a recent median of 636
```

## What it usually is

**A truncated response.** This is the failure the guard exists for, and it is
nasty precisely because it does not look like one: a truncated response is still
valid HTML, still parses, and produces a plausible day with too few instruments.
No schema assertion would reject it.

**A genuinely short session.** Rare, but half-days exist.

## Do this

Look at what landed before deciding:

```bash
gunzip -c landing/dse/day_end/2026-09-14.html.gz | grep -c "<tr"
```

If it is truncated, delete the landed file and re-capture that date. The file is
the evidence; replacing it is the fix.

```bash
rm landing/dse/day_end/2026-09-14.*
uv run python ingestion/capture_day_end.py --start-date 2026-09-14 --end-date 2026-09-14 \
  --landing landing/dse/day_end
```

If the day is genuinely short, wave it through explicitly:

```bash
uv run python -m ingestion.load_day_end --landing landing/dse/day_end \
  --start-date 2026-09-14 --end-date 2026-09-14 --allow-short-day 2026-09-14
```

## Check afterwards

The day is present with a plausible instrument count, and **Instruments, newest
day** on the data-health dashboard is back near its usual value. That number
drifts legitimately — 655 in May 2025, 636 in September 2026 — so compare to
neighbouring days rather than to a remembered constant.
