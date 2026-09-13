"""Watch for the failures that do not announce themselves.

Nothing here runs the pipeline. It exists because the pipeline can be entirely
green and the data still wrong: the machine was off for a week, the exchange
served an error page every night, or capture kept working while the load quietly
stopped. None of those raise a task failure, and all of them end with a warehouse
nobody should be trusting.

Two signals, deliberately separate, because they point at different broken things:

  landing behind today      -> capture is not running, or the machine was off
  warehouse behind landing  -> capture works, but load or dbt stopped

The second is the one that started this orchestration work. Capture had been
automated for days while load stayed manual, and the warehouse fell behind with
nothing to say so.
"""

from __future__ import annotations

import datetime as dt
import os
import pathlib

import psycopg
from airflow.sdk import dag, task
from dse_alerting import send_alert

LANDING = pathlib.Path("/opt/project/landing/dse/day_end")

# The exchange trades Sunday to Thursday, so a Thursday capture is three days old
# by Sunday and that is perfectly healthy. Anything beyond that is either a
# holiday week or something broken, and both are worth a look.
MAX_LANDING_AGE_DAYS = int(os.environ.get("DSE_FRESHNESS_MAX_AGE_DAYS", "4"))


def newest_landed_trading_day() -> dt.date | None:
    """The most recent date the exchange actually served data for.

    Sidecars without a response are dates with no session, so they are not
    evidence of freshness and are ignored here.
    """
    days = [
        dt.date.fromisoformat(path.name.split(".")[0])
        for path in LANDING.glob("*.html.gz")
    ]
    return max(days) if days else None


def newest_modelled_trading_day() -> dt.date | None:
    with psycopg.connect(
        host=os.environ["DSE_PG_HOST"], port=os.environ["DSE_PG_PORT"],
        dbname=os.environ["DSE_PG_DATABASE"], user=os.environ["DSE_PG_USER"],
        password=os.environ["DSE_PG_PASSWORD"],
    ) as connection, connection.cursor() as cursor:
        cursor.execute("select max(trade_date) from marts.fact_daily_price")
        return cursor.fetchone()[0]


@dag(
    dag_id="dse_freshness_check",
    description="Alerts when the data is stale even though nothing failed",
    # Hourly rather than daily: the point is to notice quickly, and the check is
    # two cheap reads. The alert itself is rate-limited, so this cannot become
    # an hourly stream of the same message.
    schedule="15 * * * *",
    start_date=dt.datetime(2026, 9, 1),
    catchup=False,
    max_active_runs=1,
    tags=["monitoring"],
)
def dse_freshness_check():

    @task
    def landing_is_current() -> str:
        """Is capture still happening at all?"""
        newest = newest_landed_trading_day()
        if newest is None:
            send_alert(
                key="landing_empty",
                subject="STALE  nothing has ever been captured",
                body=f"No landed responses found in {LANDING}.",
            )
            return "landing is empty"

        age = (dt.date.today() - newest).days
        if age > MAX_LANDING_AGE_DAYS:
            send_alert(
                key="landing_stale",
                subject=f"STALE  capture is {age} days behind",
                body=(
                    f"The newest captured trading day is {newest}, {age} days old.\n"
                    f"Expected no more than {MAX_LANDING_AGE_DAYS} days, which allows "
                    f"for the Friday and Saturday the exchange is closed.\n\n"
                    f"The archive is a rolling two-year window: a trading day that is "
                    f"never captured becomes unrecoverable, so this is worth acting on."
                ),
            )
            return f"stale: newest landed day {newest} is {age} days old"
        return f"current: newest landed day {newest}, {age} days old"

    @task
    def warehouse_matches_landing() -> str:
        """Capture can be perfectly healthy while nothing loads it."""
        landed = newest_landed_trading_day()
        modelled = newest_modelled_trading_day()

        if landed is None:
            return "nothing landed, nothing to compare"
        if modelled is None:
            send_alert(
                key="warehouse_empty",
                subject="STALE  the warehouse holds no prices",
                body=f"Landing has data up to {landed} but marts.fact_daily_price is empty.",
            )
            return "warehouse is empty"

        behind = (landed - modelled).days
        if behind > 0:
            send_alert(
                key="warehouse_behind_landing",
                subject=f"STALE  warehouse is {behind} days behind landing",
                body=(
                    f"Landing holds {landed}; the warehouse holds {modelled}.\n"
                    f"Capture is working and the load is not. Nothing will have "
                    f"failed — this is the silent one."
                ),
            )
            return f"behind: landing {landed}, warehouse {modelled}"
        return f"in step: landing {landed}, warehouse {modelled}"

    landing_is_current()
    warehouse_matches_landing()


dse_freshness_check()
