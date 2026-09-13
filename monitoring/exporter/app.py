"""Metrics about the data, not about the machinery.

Airflow already reports whether tasks ran. This reports whether the result is
worth trusting, which is a different question and the one this project cares
about: the pipeline can be entirely green while the exchange serves an error
page, a day goes unloaded, or the instrument universe shifts under the models.

Deliberately stdlib plus psycopg. An exporter that needs its own dependency tree
is one more thing that can be broken when you most need to see what is broken.

Absence is not zero. When the warehouse cannot be reached, the data gauges are
not emitted at all rather than reported as 0 -- a freshness of zero would read as
"perfectly current" on every dashboard, which is the exact opposite of the truth.
Only `dse_warehouse_up` is always present.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg

PORT = int(os.environ.get("DSE_EXPORTER_PORT", "9108"))
LANDING = pathlib.Path(os.environ.get("DSE_LANDING_DIR", "/opt/project/landing/dse/day_end"))
DBT_RESULTS = pathlib.Path(os.environ.get("DBT_RESULTS", "/opt/project/dbt/target/run_results.json"))

WAREHOUSE_QUERY = """
select
    (select count(*)                         from marts.fact_daily_price) as price_rows,
    (select count(distinct trade_date)       from marts.fact_daily_price) as trading_days,
    (select max(trade_date)                  from marts.fact_daily_price) as newest_day,
    (select count(*)                         from marts.dim_instrument)   as instruments_ever,
    (select avg(case when did_not_trade then 1.0 else 0.0 end)
       from marts.fact_daily_price)                                       as did_not_trade_ratio
"""

LATEST_DAY_QUERY = """
select count(*) as instruments,
       sum(case when did_not_trade then 1 else 0 end) as did_not_trade,
       sum(coalesce(turnover, 0)) as turnover
from marts.fact_daily_price
where trade_date = (select max(trade_date) from marts.fact_daily_price)
"""


class Metric:
    """One Prometheus gauge, rendered with its help text and type."""

    def __init__(self, name: str, help_text: str):
        self.name, self.help_text = name, help_text

    def render(self, value) -> str:
        if value is None:
            return ""
        return (
            f"# HELP {self.name} {self.help_text}\n"
            f"# TYPE {self.name} gauge\n"
            f"{self.name} {value}\n"
        )


METRICS = {
    "up": Metric("dse_warehouse_up", "1 when the warehouse answered, 0 when it did not."),
    "price_rows": Metric("dse_price_rows_total", "Rows in fact_daily_price."),
    "trading_days": Metric("dse_trading_days_total", "Distinct trading days held."),
    "freshness": Metric(
        "dse_data_freshness_days",
        "Age in days of the newest trading day held. Rises on weekends; the exchange trades Sunday to Thursday.",
    ),
    "newest_ts": Metric("dse_newest_trading_day_timestamp_seconds", "Newest trading day held, as a unix timestamp."),
    "instruments_ever": Metric("dse_instruments_ever_seen", "Instruments that have appeared at any point."),
    "instruments_latest": Metric(
        "dse_instruments_latest_day",
        "Instruments present on the newest trading day. Drifts as listings arrive and bonds mature.",
    ),
    "dnt_latest": Metric("dse_did_not_trade_latest_day", "Instruments that did not trade on the newest day."),
    "dnt_ratio": Metric("dse_did_not_trade_ratio", "Share of all rows that did not trade. Historically about 0.39."),
    "turnover_latest": Metric("dse_turnover_latest_day_taka", "Total turnover on the newest trading day, in taka."),
    "landing_days": Metric("dse_landing_trading_days_total", "Trading days captured into landing."),
    "behind": Metric(
        "dse_warehouse_days_behind_landing",
        "Trading days landed but not yet in the warehouse. Above zero means capture works and the load does not.",
    ),
    "assertions_failed": Metric("dse_assertions_failed", "Failing dbt assertions in the last build."),
    "assertions_passed": Metric("dse_assertions_passed", "Passing dbt assertions in the last build."),
}


def landing_newest_and_count() -> tuple[dt.date | None, int]:
    days = [
        dt.date.fromisoformat(p.name.split(".")[0])
        for p in LANDING.glob("*.html.gz")
    ]
    return (max(days) if days else None), len(days)


def dbt_assertion_counts() -> tuple[int | None, int | None]:
    """Read the last dbt build's results, if one has been written."""
    if not DBT_RESULTS.exists():
        return None, None
    try:
        results = json.loads(DBT_RESULTS.read_text())["results"]
    except Exception:
        return None, None
    tests = [r for r in results if r.get("unique_id", "").startswith("test.")]
    failed = sum(1 for r in tests if r["status"] not in ("pass", "success"))
    return failed, len(tests) - failed


def collect() -> str:
    out: list[str] = []

    try:
        with psycopg.connect(
            host=os.environ["DSE_PG_HOST"], port=os.environ["DSE_PG_PORT"],
            dbname=os.environ["DSE_PG_DATABASE"], user=os.environ["DSE_PG_USER"],
            password=os.environ["DSE_PG_PASSWORD"], connect_timeout=5,
        ) as connection, connection.cursor() as cursor:
            cursor.execute(WAREHOUSE_QUERY)
            rows, days, newest, instruments_ever, dnt_ratio = cursor.fetchone()
            cursor.execute(LATEST_DAY_QUERY)
            latest_instruments, latest_dnt, latest_turnover = cursor.fetchone()
    except Exception as error:
        # Say the warehouse is down, and emit nothing else. A dashboard showing
        # a freshness of 0 because the database was unreachable is worse than a
        # dashboard showing a gap.
        print(f"warehouse unreachable: {type(error).__name__}: {error}", flush=True)
        return METRICS["up"].render(0)

    out.append(METRICS["up"].render(1))
    out.append(METRICS["price_rows"].render(rows))
    out.append(METRICS["trading_days"].render(days))
    out.append(METRICS["instruments_ever"].render(instruments_ever))
    out.append(METRICS["dnt_ratio"].render(round(float(dnt_ratio or 0), 4)))
    out.append(METRICS["instruments_latest"].render(latest_instruments))
    out.append(METRICS["dnt_latest"].render(latest_dnt))
    out.append(METRICS["turnover_latest"].render(int(latest_turnover or 0)))

    if newest:
        age = (dt.date.today() - newest).days
        out.append(METRICS["freshness"].render(age))
        out.append(METRICS["newest_ts"].render(
            int(dt.datetime.combine(newest, dt.time()).replace(tzinfo=dt.timezone.utc).timestamp())
        ))

    landed_newest, landed_count = landing_newest_and_count()
    out.append(METRICS["landing_days"].render(landed_count))
    if landed_newest and newest:
        out.append(METRICS["behind"].render((landed_newest - newest).days))

    failed, passed = dbt_assertion_counts()
    out.append(METRICS["assertions_failed"].render(failed))
    out.append(METRICS["assertions_passed"].render(passed))

    return "".join(out)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/metrics", "/"):
            self.send_error(404)
            return
        body = collect().encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # Prometheus scrapes constantly; its access log is noise.


if __name__ == "__main__":
    print(f"dse metrics exporter listening on :{PORT}", flush=True)
    ThreadingHTTPServer(("", PORT), Handler).serve_forever()
