"""The daily market pipeline: capture a trading day, load it, rebuild the marts.

This DAG exists because of a gap that was visible in the data. Capture had been
automated since the project's first week, but loading and the dbt build stayed
manual, so the warehouse quietly fell behind landing — two days after capture was
wired up, landing held 2026-09-10 and the warehouse held 2026-09-09, with nothing
to say so.

Each task is deliberately small and independent: a failure in one stops what
depends on it and nothing else.
"""

from __future__ import annotations

import datetime as dt
import os
import pathlib

from airflow.sdk import dag, get_current_context, task
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import InvocationMode, TestBehavior
from dse_alerting import on_task_failure

LANDING = pathlib.Path("/opt/project/landing/dse/day_end")
DBT_PROJECT = pathlib.Path("/opt/project/dbt")
DBT_EXECUTABLE = os.environ.get("DBT_EXECUTABLE", "/opt/dbt-venv/bin/dbt")

# dbt is rendered into the graph model by model rather than run as one command.
# A single `dbt build` task is one green box that says nothing: when an
# assertion on fact_daily_price fails, the graph should name the model and the
# rule without anyone opening a log.
#
# TestBehavior.AFTER_EACH puts each assertion immediately after the model it
# tests, so a failing assertion stops that model's dependents and nothing else.
DBT_PROFILE = ProfileConfig(
    profile_name="dse",
    target_name="dev",
    profiles_yml_filepath=DBT_PROJECT / "profiles.yml",
)

# Each run re-covers a short trailing window rather than a single date. The
# exchange's archive is a rolling two-year window, so a day missed because the
# machine was asleep is only recoverable while it is still served. Re-covering a
# few days means an interrupted schedule heals itself on the next run instead of
# leaving a hole nobody notices until it is permanent. Loading is idempotent per
# trading day, so the overlap costs nothing.
LOOKBACK_DAYS = 3


def trading_day() -> dt.date:
    """The trading day this run is responsible for.

    Taken from `data_interval_end`, not `logical_date`, and that is deliberate.
    A daily schedule at 13:00 UTC produces a run whose interval *ends* at 13:00
    on the day being processed and whose `logical_date` is the day before. The
    exchange publishes end-of-day data a few hours after its 14:30 local close,
    so the day worth fetching is the one the interval ends on. Using
    `logical_date` here would quietly process yesterday, for ever.

    Read off the DagRun rather than the context. Airflow 3 does not put
    `data_interval_end` in the task context, only on the run -- and
    `airflow dags test` does, which is how a DAG that could never run under the
    scheduler passed its first round of checks.
    """
    run = get_current_context()["dag_run"]
    end = getattr(run, "data_interval_end", None) or getattr(run, "logical_date", None)
    # A run triggered by hand may carry neither; the day it was asked for is today.
    return (end or dt.datetime.now(dt.timezone.utc)).date()


def window() -> tuple[dt.date, dt.date]:
    end = trading_day()
    return end - dt.timedelta(days=LOOKBACK_DAYS - 1), end


@dag(
    dag_id="dse_market_daily",
    description="Capture, load and model one trading day of DSE prices",
    # 13:00 UTC is 19:00 in Dhaka, several hours after the 14:30 close.
    schedule="0 13 * * *",
    start_date=dt.datetime(2026, 9, 1),
    # Turned on deliberately in the backfill ticket, not by accident here.
    catchup=False,
    # One run at a time: overlapping runs would fetch the same days twice and
    # put avoidable load on a public exchange site.
    max_active_runs=1,
    default_args={
        # Fires after the retries are exhausted, not on each attempt.
        "on_failure_callback": on_task_failure,
        "retries": 3,
        "retry_delay": dt.timedelta(minutes=3),
        "retry_exponential_backoff": True,
        "max_retry_delay": dt.timedelta(minutes=30),
    },
    tags=["market", "daily"],
)
def dse_market_daily():

    @task
    def capture() -> dict:
        """Fetch the window from the exchange into landing, byte for byte."""
        from ingestion.capture_day_end import capture_range

        start, end = window()
        outcomes = capture_range(LANDING, start, end)

        failed = {d: o for d, o in outcomes.items() if o.startswith("FAILED")}
        if failed:
            raise RuntimeError(f"capture failed for {', '.join(sorted(failed))}")

        captured = sum(1 for o in outcomes.values() if o.startswith("captured"))
        print(f"window {start} to {end}: {captured} newly captured, {len(outcomes)} dates considered")
        return {"start": start.isoformat(), "end": end.isoformat()}

    @task
    def load(bounds: dict) -> dict:
        """Load landed responses into `raw`, replacing each day atomically."""
        import psycopg

        from ingestion.load_day_end import load as load_landing

        with psycopg.connect(
            host=os.environ["DSE_PG_HOST"], port=os.environ["DSE_PG_PORT"],
            dbname=os.environ["DSE_PG_DATABASE"], user=os.environ["DSE_PG_USER"],
            password=os.environ["DSE_PG_PASSWORD"],
        ) as connection:
            report = load_landing(connection, LANDING, bounds["start"], bounds["end"])

        print(report.summary())
        for date in sorted(report.rows_read):
            print(f"  {date}: read {report.rows_read[date]}, wrote {report.loaded.get(date, 0)}")

        # A refusal is the row-count guard doing its job and needs a human, so it
        # fails the task. A day with no session is an answer, not a failure.
        if not report.ok:
            raise RuntimeError(report.summary())

        return {
            "days_loaded": len(report.loaded),
            "rows": sum(report.loaded.values()),
            "non_trading": len(report.non_trading),
        }

    # Every model and every assertion is its own task. Runs even when nothing new
    # was loaded: the models are cheap to rebuild and the assertions are worth
    # re-running against what is already there. A quiet day is not a reason to
    # stop checking.
    transform = DbtTaskGroup(
        group_id="transform",
        project_config=ProjectConfig(dbt_project_path=DBT_PROJECT),
        profile_config=DBT_PROFILE,
        # SUBPROCESS, not the default DBT_RUNNER: dbt lives in its own
        # virtualenv and is deliberately not importable from Airflow's
        # environment, so cosmos has to shell out to it rather than import it.
        execution_config=ExecutionConfig(
            dbt_executable_path=DBT_EXECUTABLE,
            invocation_mode=InvocationMode.SUBPROCESS,
        ),
        render_config=RenderConfig(
            dbt_executable_path=DBT_EXECUTABLE,
            invocation_mode=InvocationMode.SUBPROCESS,
            test_behavior=TestBehavior.AFTER_EACH,
        ),
        default_args={"retries": 1},
    )

    load(capture()) >> transform


dse_market_daily()
