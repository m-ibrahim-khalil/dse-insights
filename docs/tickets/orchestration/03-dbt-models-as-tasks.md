# 03 — Each dbt model is its own task

**What to build:** The dbt project is rendered into the Airflow graph as
individual model and test tasks rather than one opaque `dbt build`, so the
lineage visible in Airflow is the real lineage.

This is the difference between an orchestrator you can see the pipeline in and
one that shows a single green box labelled "dbt". When a test on
`fact_daily_price` fails, the graph should say so — naming the model and the
assertion — without anyone opening a log.

**Blocked by:** 02 — The market DAG runs the pipeline end to end

**Status:** ready-for-agent

- [ ] Each dbt model appears as its own task, with dbt's own dependencies as edges
- [ ] Each data assertion appears as its own task, downstream of what it tests
- [ ] A failing assertion identifies the model and the rule in the UI
- [ ] A model's failure stops its dependents, not unrelated branches
- [ ] Re-running a single failed model from the UI works without a full rebuild
