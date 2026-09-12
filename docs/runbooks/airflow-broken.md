# Airflow will not start

Services restart-loop, or the UI never comes up.

## Confirm it

```bash
docker compose ps
docker compose logs airflow-init --tail 30
```

`airflow-init` runs once and everything waits for it to succeed. If it failed,
nothing else will start, and its log holds the reason.

## What it usually is

**The disk filled.** The most likely cause, and it has happened here. Docker's
VM image grows without bound, and when the host runs out of space Postgres can
be left with a zeroed page:

```
PANIC: replication checkpoint has wrong magic 0 instead of 307747550
```

Check first:

```bash
df -h /System/Volumes/Data
docker system df
```

Reclaim build cache, which is regenerable and holds no state:

```bash
docker builder prune -af
```

That alone freed 42 GB here. Prune images or volumes only deliberately — other
projects share that daemon.

**Corrupt Airflow metadata.** If `airflow-db` is unhealthy after a disk event,
rebuild *only* it. Airflow's metadata is a separate database from the warehouse
precisely so this is survivable:

```bash
docker compose rm -sf airflow-db
docker volume rm dse_airflow-db-data
docker compose up -d
```

You lose Airflow's run history. **You do not lose the warehouse.**

## Check afterwards

```bash
docker compose ps        # all services healthy
make test                # 48 tests, against its own database
```

Then confirm the warehouse survived:

```bash
make db-shell -- -c "select count(*), max(trade_date) from raw.day_end;"
```
