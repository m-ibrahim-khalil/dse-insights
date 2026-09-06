"""What the loader does with input it cannot trust.

The exchange fails in a particular way: a truncated response is still valid
HTML and still parses. It yields a trading day with too few instruments, which
no schema assertion rejects and which surfaces months later as a hole in a chart.
"""

import gzip
import subprocess

import pytest

from ingestion.load_day_end import load
from tests.landing_builder import write_day

pytestmark = pytest.mark.pipeline

DATES = ["2026-07-06", "2026-07-07", "2026-07-08", "2026-07-09", "2026-07-13"]


@pytest.fixture
def connection(env):
    import psycopg
    with psycopg.connect(
        host=env["DSE_PG_HOST"], port=env["DSE_PG_PORT"], dbname=env["DSE_PG_DATABASE"],
        user=env["DSE_PG_USER"], password=env["DSE_PG_PASSWORD"],
    ) as conn:
        yield conn
        with conn.cursor() as cursor:
            cursor.execute("delete from raw.day_end where trade_date = any(%s)", (DATES,))
        conn.commit()


def raw_rows(connection, date):
    with connection.cursor() as cursor:
        cursor.execute("select count(*) from raw.day_end where trade_date = %s", (date,))
        return cursor.fetchone()[0]


def truncated_payload(keep: int) -> bytes:
    """A response cut short mid-table: still valid HTML, still parses, wrong."""
    from tests.landing_builder import FIXTURE
    html = FIXTURE.read_text()
    head, _, _ = html.partition(f'<tr>\n<td width="4%">{keep + 1}</td>')
    return (head + "</tbody></table></div></body></html>").encode()


def test_a_corrupt_file_does_not_stop_its_neighbours(connection, tmp_path):
    write_day(tmp_path, DATES[0])
    (tmp_path / f"{DATES[1]}.html.gz").write_bytes(b"this is not gzip")
    write_day(tmp_path, DATES[2])

    report = load(connection, tmp_path)

    assert sorted(report.loaded) == [DATES[0], DATES[2]]
    assert DATES[1] in report.failed
    assert raw_rows(connection, DATES[0]) == 6
    assert raw_rows(connection, DATES[2]) == 6


def test_a_failure_names_the_file_and_the_reason(connection, tmp_path):
    (tmp_path / f"{DATES[1]}.html.gz").write_bytes(b"this is not gzip")
    report = load(connection, tmp_path)
    reason = report.failed[DATES[1]]
    assert f"{DATES[1]}.html.gz" in reason
    assert reason != ""


def test_a_truncated_day_is_refused_before_anything_is_written(connection, tmp_path):
    for date in DATES[:3]:
        write_day(tmp_path, date)
    load(connection, tmp_path)

    write_day(tmp_path, DATES[3], payload=truncated_payload(1))
    report = load(connection, tmp_path)

    assert DATES[3] in report.refused
    assert raw_rows(connection, DATES[3]) == 0, "nothing may be written for a refused day"


def test_the_expected_count_comes_from_history_not_a_constant(connection, tmp_path):
    """With no history to compare against there is no basis to refuse."""
    write_day(tmp_path, DATES[0], payload=truncated_payload(1))
    report = load(connection, tmp_path)
    assert report.refused == {}
    assert report.loaded[DATES[0]] == 1


def test_the_guard_can_be_overridden_for_a_genuinely_short_day(connection, tmp_path):
    for date in DATES[:3]:
        write_day(tmp_path, date)
    load(connection, tmp_path)

    write_day(tmp_path, DATES[3], payload=truncated_payload(1))
    report = load(connection, tmp_path, allow_short_days=[DATES[3]])

    assert report.refused == {}
    assert raw_rows(connection, DATES[3]) == 1


def test_rows_read_and_rows_written_are_both_reported(connection, tmp_path):
    for date in DATES[:3]:
        write_day(tmp_path, date)
    load(connection, tmp_path)
    write_day(tmp_path, DATES[3], payload=truncated_payload(1))

    report = load(connection, tmp_path)
    assert report.rows_read[DATES[3]] == 1
    assert report.loaded.get(DATES[3], 0) == 0, "read but not written -- visible, not silent"


def test_exit_status_reflects_a_failure(connection, env, tmp_path):
    write_day(tmp_path, DATES[0])
    (tmp_path / f"{DATES[1]}.html.gz").write_bytes(b"this is not gzip")

    finished = subprocess.run(
        ["uv", "run", "python", "-m", "ingestion.load_day_end", "--landing", str(tmp_path)],
        env=env, capture_output=True, text=True,
    )
    assert finished.returncode != 0
    assert DATES[1] in finished.stdout + finished.stderr


def test_a_response_that_parses_to_nothing_is_a_failure(connection, tmp_path):
    """The silent one. An error page is valid HTML that parses to zero rows.

    Caught before the row-count guard, which needs history to judge against and
    would otherwise wave the very first such day through as a successful load.
    """
    write_day(tmp_path, DATES[0],
              payload=b"<html><body><h1>Service unavailable</h1></body></html>")

    report = load(connection, tmp_path)

    assert DATES[0] in report.failed
    assert DATES[0] not in report.loaded
    assert "0 rows" in report.failed[DATES[0]]
    assert raw_rows(connection, DATES[0]) == 0
