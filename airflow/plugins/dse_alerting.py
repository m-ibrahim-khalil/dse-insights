"""Getting a human's attention, and not getting it too often.

Two failures matter here and they look nothing alike. A crashed task is loud and
Airflow already records it. The failure this project actually fears is quiet: the
schedule succeeding every night while the warehouse silently falls further behind,
or the machine being off for a week with nothing to say so.

The channel is deliberately a plain webhook. It works with Slack, Discord, Teams
and ntfy without this project knowing which, and the endpoint stays in the
environment rather than in the repository.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.request

from airflow.sdk import Variable

# How long the same alert stays quiet after firing. A week-long outage should
# produce a handful of messages, not one per scheduled run -- an alert stream
# nobody can face is an alert stream nobody reads.
QUIET_HOURS = float(os.environ.get("DSE_ALERT_QUIET_HOURS", "6"))

BASE_URL = os.environ.get("AIRFLOW_BASE_URL", "http://localhost:8080")


def _recently_sent(key: str) -> bool:
    """True when this alert fired inside the quiet window."""
    last = Variable.get(f"alert_last_sent__{key}", default=None)
    if not last:
        return False
    try:
        sent_at = dt.datetime.fromisoformat(last)
    except ValueError:
        return False
    age = dt.datetime.now(dt.timezone.utc) - sent_at
    return age < dt.timedelta(hours=QUIET_HOURS)


def _remember(key: str) -> None:
    Variable.set(f"alert_last_sent__{key}", dt.datetime.now(dt.timezone.utc).isoformat())


def send_alert(key: str, subject: str, body: str, link: str | None = None) -> bool:
    """Raise an alert, unless the same one fired recently.

    `key` identifies the *kind* of alert, not the occurrence, so repeats of the
    same problem collapse. Returns whether anything was actually sent.
    """
    if _recently_sent(key):
        print(f"ALERT suppressed (fired within {QUIET_HOURS}h): {subject}")
        return False

    text = f"{subject}\n\n{body}"
    if link:
        text += f"\n\n{link}"

    # Always visible in the task log, whether or not a webhook is configured --
    # an alert that depends on configuration nobody did is not an alert.
    print(f"ALERT: {text}")

    webhook = os.environ.get("DSE_ALERT_WEBHOOK", "").strip()
    if webhook:
        request = urllib.request.Request(
            webhook,
            data=json.dumps({"text": text}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                print(f"alert delivered, HTTP {response.status}")
        except Exception as error:
            # A failing alert channel must never fail the thing it reports on.
            print(f"alert webhook failed: {type(error).__name__}: {error}")
    else:
        print("DSE_ALERT_WEBHOOK is not set — alert logged only")

    _remember(key)
    return True


def on_task_failure(context) -> None:
    """Airflow failure callback: name the DAG, the task, the date and the log."""
    ti = context["task_instance"]
    run = context["dag_run"]
    # Same trap as the market DAG: the interval lives on the run, not the context.
    end = getattr(run, "data_interval_end", None) or getattr(run, "logical_date", None)
    date = (end or dt.datetime.now(dt.timezone.utc)).date()

    link = (
        f"{BASE_URL}/dags/{ti.dag_id}/runs/{run.run_id}/tasks/{ti.task_id}"
    )
    send_alert(
        key=f"task_failed__{ti.dag_id}__{ti.task_id}",
        subject=f"FAILED  {ti.dag_id} · {ti.task_id}  (trading day {date})",
        body=(
            f"Attempt {ti.try_number} failed.\n"
            f"Run: {run.run_id}\n"
            f"Reason: {context.get('exception', 'see the task log')}"
        ),
        link=link,
    )
