# 07 — Two dashboards: is it running, is it right

**What to build:** Grafana, provisioned from files in the repository so the
dashboards exist on a fresh clone rather than being clicked together by hand.

Two dashboards, because they answer different questions. **Pipeline health**:
run outcomes, task durations over time, retries, last successful run. **Data
health**: freshness, rows per Trading Day, the did-not-trade share, instrument
count, assertion failures.

The second is the one worth showing someone. Anyone can screenshot a green DAG;
a chart of the did-not-trade share holding near 39% for two years is evidence
the data is understood.

**Blocked by:** 06 — The platform exposes metrics worth watching

**Status:** ready-for-agent

- [ ] Grafana runs under Compose with its datasource and dashboards provisioned from files
- [ ] A pipeline-health dashboard shows run outcomes, durations and last success
- [ ] A data-health dashboard shows freshness, volumes, did-not-trade share and assertions
- [ ] Every panel reads a metric that actually exists, with no placeholder panels
- [ ] Dashboards load with real data on a fresh clone after one pipeline run
- [ ] The default admin credential is not the committed one
