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


def test_non_traded_instrument_has_no_trade_prices(warehouse):
    """Zeroed OHLC means no trade happened, not a price of zero."""
    row = fact_row(warehouse, "TB10Y0127")
    assert row["open_price"] is None
    assert row["high_price"] is None
    assert row["low_price"] is None
    assert row["last_traded_price"] is None
    assert row["did_not_trade"] is True


def test_non_traded_instrument_keeps_its_published_close(warehouse):
    """The exchange publishes a close for instruments that never trade.

    A treasury bond's close moves daily on zero volume -- it is a valuation, and
    the only price such an instrument has. Nulling it would erase that.
    """
    row = fact_row(warehouse, "TB10Y0127")
    assert row["close_price"] == EXPECTED["TB10Y0127"]["close_price"]
    assert row["previous_close"] == EXPECTED["TB10Y0127"]["previous_close"]
    assert row["close_price"] != row["previous_close"]


def test_non_traded_instrument_reports_zero_activity_not_null(warehouse):
    """No shares changed hands is a fact, not missing data."""
    row = fact_row(warehouse, "TB10Y0127")
    assert row["volume"] == 0
    assert row["trade_count"] == 0
    assert row["turnover"] == 0


def test_non_traded_instrument_still_has_a_row(warehouse):
    """A gap in a series must mean missing data, never a quiet day."""
    with warehouse.cursor() as cursor:
        cursor.execute(
            "select count(*) from marts.fact_daily_price where did_not_trade")
        assert cursor.fetchone()[0] == 1
