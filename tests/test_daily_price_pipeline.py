"""Seam 1: a landed response goes in, the modelled price fact comes out.

Everything between -- parsing, the raw load, the dbt build -- is implementation
this test knows nothing about. Renaming a model or restructuring the parser must
not change a line here.
"""

import pytest

from tests.expectations import EXPECTED, TRADE_DATE

pytestmark = pytest.mark.pipeline

FACT_COLUMNS = (
    "open_price", "high_price", "low_price", "close_price",
    "last_traded_price", "previous_close", "trade_count", "turnover",
    "volume", "did_not_trade",
)


def fact_row(connection, trading_code, trade_date=TRADE_DATE):
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            select {", ".join("f." + c for c in FACT_COLUMNS)}
            from marts.fact_daily_price f
            join marts.dim_instrument i using (instrument_key)
            where i.trading_code = %s and f.trade_date = %s
            """,
            (trading_code, trade_date),
        )
        row = cursor.fetchone()
    assert row is not None, f"no fact row for {trading_code} on {trade_date}"
    return dict(zip(FACT_COLUMNS, row))


@pytest.mark.parametrize("trading_code", sorted(EXPECTED))
def test_every_price_field_matches_exactly(warehouse, trading_code):
    """The transposition guard. Source column order is LTP, HIGH, LOW, OPENP, CLOSEP."""
    assert fact_row(warehouse, trading_code) == EXPECTED[trading_code]


def test_turnover_is_taka_not_millions(warehouse):
    """Converted exactly once. Converting twice, or not at all, is a factor of a million."""
    assert fact_row(warehouse, "GP")["turnover"] == EXPECTED["GP"]["turnover"]


def test_thousands_separated_price_keeps_its_magnitude(warehouse):
    """A price above a thousand must not be truncated at the comma."""
    assert fact_row(warehouse, "ABBLPBOND")["close_price"] > 1000


def test_every_fixture_instrument_reaches_the_fact(warehouse):
    with warehouse.cursor() as cursor:
        cursor.execute("select count(*) from marts.fact_daily_price")
        assert cursor.fetchone()[0] == len(EXPECTED)


def test_dimension_describes_instruments_not_companies(warehouse):
    """A bond is an Instrument. ADR 0005."""
    with warehouse.cursor() as cursor:
        cursor.execute("select count(*) from marts.dim_instrument where trading_code = 'ABBLPBOND'")
        assert cursor.fetchone()[0] == 1
