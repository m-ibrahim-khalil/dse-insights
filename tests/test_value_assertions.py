"""Proof that the data assertions actually fire.

Every assertion here is watched failing against deliberately corrupt data. A
green test suite says nothing about an assertion that could never fail.
"""

import subprocess

import pytest

from ingestion.load_day_end import load
from tests.landing_builder import HEALTHY_ROW, NON_TRADED_ROW, write_rows

pytestmark = pytest.mark.pipeline

DATE = "2026-06-15"
REPO = __import__("pathlib").Path(__file__).resolve().parents[1]


def run_dbt(env, *args):
    return subprocess.run(["uv", "run", "dbt", *args],
                          cwd=REPO / "dbt", env=env, capture_output=True, text=True)


@pytest.fixture
def corrupt_day(env, tmp_path, warehouse):
    """Land a day, rebuild, and put the warehouse back afterwards.

    Depends on `warehouse` so the shared fixture is already loaded, and restores
    it on teardown so no other test can observe the corruption.
    """
    def land(rows):
        write_rows(tmp_path, DATE, rows)
        load(warehouse, tmp_path, allow_short_days=[DATE])
        return run_dbt(env, "build")

    yield land

    with warehouse.cursor() as cursor:
        cursor.execute("delete from raw.day_end where trade_date = %s", (DATE,))
    warehouse.commit()
    run_dbt(env, "build")


def bad_ohlc_row():
    """High below low. Every other field is ordinary, so only one rule can fire."""
    code, ltp, high, low, *rest = HEALTHY_ROW
    return (code, ltp, low, high, *rest)   # high and low swapped


def negative_volume_row():
    row = list(HEALTHY_ROW)
    row[9] = "-159,842"
    return tuple(row)


def test_ohlc_assertion_fires_when_high_is_below_low(corrupt_day):
    built = corrupt_day([bad_ohlc_row(), NON_TRADED_ROW])
    assert built.returncode != 0, "a high below the low must fail the build"
    assert "fact_daily_price_ohlc_is_sane" in built.stdout


def test_a_failing_assertion_names_the_instrument_and_the_day(corrupt_day, env, warehouse):
    corrupt_day([bad_ohlc_row(), NON_TRADED_ROW])
    with warehouse.cursor() as cursor:
        cursor.execute("""
            select i.trading_code, f.trade_date
            from marts.fact_daily_price f
            join marts.dim_instrument i using (instrument_key)
            where not f.did_not_trade and f.high_price < f.low_price
        """)
        offending = cursor.fetchall()
    assert offending, "the failing rows must be identifiable, not merely counted"
    assert offending[0][0] == "GP"
    assert offending[0][1].isoformat() == DATE


def test_negative_volume_fails_the_build(corrupt_day):
    built = corrupt_day([negative_volume_row(), NON_TRADED_ROW])
    assert built.returncode != 0
    assert "fact_daily_price_values_are_not_negative" in built.stdout


def test_a_non_traded_row_does_not_trip_the_ohlc_assertion(corrupt_day):
    """The 39% case. Zeroed OHLC beside a published close must not be a failure."""
    built = corrupt_day([HEALTHY_ROW, NON_TRADED_ROW])
    assert built.returncode == 0, built.stdout[-2000:]


def test_assertions_are_part_of_the_build_not_only_the_tests(env):
    """They run in operation, against loaded data, not only under pytest."""
    listed = run_dbt(env, "ls", "--resource-type", "test")
    assert "fact_daily_price_ohlc_is_sane" in listed.stdout
    assert "fact_daily_price_values_are_not_negative" in listed.stdout
