# 02 — The market DAG runs the pipeline end to end

**What to build:** One DAG that takes a Trading Day from the exchange to
asserted marts: capture → load → dbt build. Running it makes the warehouse
current; the four steps and their dependencies are visible in the UI, and a
failure stops what depends on it rather than the whole world.

This closes the gap that prompted the work: capture has been automated since day
one, but nothing loaded it, so the warehouse silently drifted behind landing.

**Blocked by:** 01 — The platform comes up with one command

**Status:** done

- [x] A DAG runs capture, then load, then the dbt build, in that order
- [x] Each task fails independently and stops only its downstream tasks
- [x] Tasks retry with backoff, because the exchange is occasionally slow
- [x] The DAG is scheduled daily, after the exchange's close plus a margin
- [x] A task that loads nothing new succeeds rather than failing — a quiet day
      is not an error
- [x] The run is visible in the UI with per-task logs and durations
- [x] Running the DAG twice for the same day changes nothing in the warehouse
