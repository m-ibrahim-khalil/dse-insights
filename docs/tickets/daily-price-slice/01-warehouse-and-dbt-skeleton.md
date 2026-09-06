# 01 — Warehouse and dbt skeleton

**What to build:** A developer with a fresh clone runs one documented command and
gets a local warehouse running, and a second command builds a trivial dbt model
against it. Nothing about the Day End Archive is involved yet — this exists so
that every later ticket can assume a working warehouse connection instead of
discovering a broken one halfway through modelling.

This is prefactoring. It delivers no data, but "the warehouse comes up" is the
thing that breaks first on a machine that has never run the project.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] A documented command starts a local PostgreSQL instance
- [ ] A dbt project exists and its connection check passes against that instance
- [ ] A trivial dbt model builds and is queryable
- [ ] Schemas exist for the `raw`, `staging`, `intermediate` and `marts` layers,
      named per [ADR 0003](../../adr/0003-layer-vocabulary.md)
- [ ] Database credentials come from the environment, never from a committed file
- [ ] Teardown is documented, so a developer can return to a clean state
