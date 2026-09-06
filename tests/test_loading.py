"""Loading behaviour: ranges, idempotency, and what happens when a day is absent.

These build their own landing directories on dates the shared fixture does not
use, and clean up after themselves, so they cannot disturb the pipeline tests.
"""

import pathlib

import pytest

from ingestion.load_day_end import load
from tests.landing_builder import write_day, write_non_trading_day

pytestmark = pytest.mark.pipeline

DATES = ["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13"]


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


def raw_digest(connection, date):
    """A content fingerprint, so 'nothing changed' means the rows, not just the count."""
    with connection.cursor() as cursor:
        cursor.execute(
            """select md5(string_agg(trading_code || closep || volume, '|' order by trading_code))
               from raw.day_end where trade_date = %s""",
            (date,),
        )
        return cursor.fetchone()[0]


def test_a_range_loads_every_landed_day(connection, tmp_path):
    for date in DATES[:3]:
        write_day(tmp_path, date)
    report = load(connection, tmp_path)
    assert sorted(report.loaded) == DATES[:3]
    assert all(raw_rows(connection, d) == 6 for d in DATES[:3])


def test_loading_the_same_day_twice_changes_nothing(connection, tmp_path):
    write_day(tmp_path, DATES[0])
    load(connection, tmp_path)
    before_count, before_digest = raw_rows(connection, DATES[0]), raw_digest(connection, DATES[0])

    load(connection, tmp_path)
    assert raw_rows(connection, DATES[0]) == before_count
    assert raw_digest(connection, DATES[0]) == before_digest


def test_a_day_that_shrinks_leaves_no_orphans(connection, tmp_path):
    """Replacing the day, rather than merging row by row, is what makes this true.

    The shrink is one instrument, which is what a delisting looks like. A larger
    drop is indistinguishable from a truncated response and the row-count guard
    refuses it -- deliberately, and covered separately in test_load_robustness.
    """
    write_day(tmp_path, DATES[0])
    load(connection, tmp_path)
    assert raw_rows(connection, DATES[0]) == 6

    payload = (pathlib.Path(__file__).parent / "fixtures" / "day_end_2026-09-03.html").read_text()
    head, _, _ = payload.partition('<tr>\n<td width="4%">6</td>')
    delisted = head + "</tbody>\n</table>\n</div>\n</body></html>\n"
    write_day(tmp_path, DATES[0], payload=delisted.encode())

    load(connection, tmp_path)
    assert raw_rows(connection, DATES[0]) == 5, "the delisted instrument must leave no orphan"


def test_a_range_spanning_a_non_session_date_succeeds(connection, tmp_path):
    write_day(tmp_path, DATES[0])
    write_non_trading_day(tmp_path, DATES[1])
    write_day(tmp_path, DATES[2])

    report = load(connection, tmp_path)
    assert sorted(report.loaded) == [DATES[0], DATES[2]]
    assert DATES[1] in report.non_trading
    assert raw_rows(connection, DATES[1]) == 0


def test_a_day_missing_from_landing_is_reported_not_skipped(connection, tmp_path):
    """Silence about a gap is the failure mode; the gap itself is recoverable."""
    write_day(tmp_path, DATES[0])
    write_day(tmp_path, DATES[3])

    report = load(connection, tmp_path, start=DATES[0], end=DATES[3])
    assert DATES[1] in report.missing
    assert DATES[2] in report.missing
    assert sorted(report.loaded) == [DATES[0], DATES[3]]
