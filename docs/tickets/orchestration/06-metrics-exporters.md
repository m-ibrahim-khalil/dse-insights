# 06 — The platform exposes metrics worth watching

**What to build:** Prometheus scraping two different kinds of metric.

Airflow's own — task duration, success and failure counts, scheduler health —
which say whether the machinery is working.

And metrics about the *data*, read from the warehouse: rows ingested per run,
rows that did not trade, data freshness in hours, instrument count per Trading
Day, and failing assertion counts. These are the ones specific to this project,
and the ones that catch a source serving valid-but-wrong data while every task
stays green.

**Blocked by:** 01 — The platform comes up with one command

**Status:** ready-for-agent

- [ ] Prometheus runs under Compose and scrapes on a documented interval
- [ ] Airflow's own metrics are collected
- [ ] A small exporter publishes data metrics read from the warehouse
- [ ] Freshness is expressed as the age of the newest Trading Day held
- [ ] Instrument count per Trading Day is exported, so universe drift is visible
- [ ] The exporter degrades to an explicit "unavailable" when the warehouse is down,
      rather than reporting zero — zero is a value, absence is not
