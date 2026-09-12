# Capture failed

## Confirm it

Open the failed task in Airflow, or:

```bash
docker compose logs airflow-scheduler | grep -i "capture"
```

The alert names the trading day. Check whether the exchange is reachable at all:

```bash
curl -sI https://www.dsebd.org/day_end_archive.php | head -1
```

## What it usually is

**The exchange was slow or briefly down.** The task retries three times with
exponential backoff before alerting, so by the time you see this it has already
been failing for a while. Usually resolves by itself on the next run, which
re-covers a three-day window.

**A TLS error.** The exchange serves an incomplete certificate chain, omitting
its Sectigo intermediate. That intermediate is pinned in `ingestion/certs/`. If
it has expired or the exchange has rotated its certificate, capture fails with a
verification error. Fetch the current one from the URL in the leaf's
authority-information-access extension. **Do not "fix" this by disabling
verification** — `curl` only appears to work because it chases that URL itself.

**The response parsed to zero rows.** That is treated as a failure on purpose:
an error page is valid HTML that parses to nothing. Look at the landed file.

## Do this

Nothing, if the next scheduled run succeeds — the trailing window heals it.

If it keeps failing, capture by hand to see the real error:

```bash
uv run python ingestion/capture_day_end.py --days 3 --landing landing/dse/day_end
```

## Check afterwards

```bash
ls -t landing/dse/day_end/*.html.gz | head -3
```

The newest landed day should be the most recent trading day. Then confirm
Grafana's **Days behind landing** returns to zero once the load catches up.
