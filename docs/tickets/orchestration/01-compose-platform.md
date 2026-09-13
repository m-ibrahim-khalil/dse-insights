# 01 — The platform comes up with one command

**What to build:** `docker compose up` brings up the whole local platform —
warehouse, Airflow scheduler, Airflow webserver, Airflow's own metadata database
— and the Airflow UI is reachable in a browser with the DAG visible but not yet
doing anything useful.

The warehouse moves under Compose too, so there is one way to start the platform
rather than a Makefile target for the database and a different mechanism for
everything else. The existing `make` targets keep working as thin wrappers, so
the README's commands do not all change at once.

Airflow's metadata database is **separate from the warehouse**. Sharing one
would put scheduler churn in the same instance as analytical queries and make
"drop the warehouse and reload" destroy the orchestrator's history.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] One documented command starts warehouse, scheduler, webserver and metadata DB
- [x] The Airflow UI is reachable and authenticated with credentials from the environment
- [x] Airflow's metadata lives in its own database, not the warehouse
- [x] The warehouse keeps its data across a restart of the platform
- [x] The existing test suite still passes against the Compose warehouse
- [x] Teardown is documented, and distinguishes stopping from destroying data
- [x] No credential is committed; `.env.example` lists every new variable
