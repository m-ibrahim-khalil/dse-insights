"""Seam 1, completed: a landed response goes in, an HTTP response comes out.

These read back the same expectations ticket 02 asserted against the warehouse.
One set of truths, two readers.
"""

from decimal import Decimal

import pytest

from tests.expectations import EXPECTED, TRADE_DATE

pytestmark = pytest.mark.pipeline

PATH = "/v1/instruments/{code}/prices"


def as_decimal(value):
    return None if value is None else Decimal(str(value))


@pytest.mark.parametrize("trading_code", sorted(EXPECTED))
def test_series_matches_the_warehouse_exactly(client, trading_code):
    response = client.get(PATH.format(code=trading_code))
    assert response.status_code == 200

    prices = response.json()["prices"]
    assert len(prices) == 1
    row = prices[0]
    expected = EXPECTED[trading_code]

    assert row["trade_date"] == TRADE_DATE
    assert row["did_not_trade"] == expected["did_not_trade"]
    assert row["volume"] == expected["volume"]
    assert row["trade_count"] == expected["trade_count"]
    for field in ("open_price", "high_price", "low_price", "close_price",
                  "last_traded_price", "previous_close", "turnover"):
        assert as_decimal(row[field]) == expected[field], field


def test_response_declares_prices_unadjusted(client):
    """ADR 0008 and 0010: a consumer must not mistake this for a continuous series."""
    body = client.get(PATH.format(code="GP")).json()
    assert body["price_basis"] == "unadjusted"


def test_non_traded_day_is_identifiable_in_the_response(client):
    row = client.get(PATH.format(code="TB10Y0127")).json()["prices"][0]
    assert row["did_not_trade"] is True
    assert row["open_price"] is None
    assert as_decimal(row["close_price"]) == EXPECTED["TB10Y0127"]["close_price"]


def test_unknown_trading_code_is_not_found(client):
    response = client.get(PATH.format(code="NOSUCHCODE"))
    assert response.status_code == 404
    assert "NOSUCHCODE" in response.json()["detail"]


def test_known_instrument_with_no_rows_in_range_is_not_a_404(client):
    """An empty range is a different answer from an unknown Instrument."""
    response = client.get(PATH.format(code="GP"),
                          params={"start_date": "2020-01-01", "end_date": "2020-01-31"})
    assert response.status_code == 200
    assert response.json()["prices"] == []


def test_date_bounds_narrow_the_series(client):
    inside = client.get(PATH.format(code="GP"),
                        params={"start_date": TRADE_DATE, "end_date": TRADE_DATE})
    assert len(inside.json()["prices"]) == 1
    outside = client.get(PATH.format(code="GP"),
                         params={"start_date": "2026-09-04", "end_date": "2026-09-30"})
    assert outside.json()["prices"] == []


def test_inverted_date_range_is_rejected_by_name(client):
    response = client.get(PATH.format(code="GP"),
                          params={"start_date": "2026-09-30", "end_date": "2026-09-01"})
    assert response.status_code == 422
    assert "start_date" in response.text


def test_malformed_date_is_rejected(client):
    response = client.get(PATH.format(code="GP"), params={"start_date": "not-a-date"})
    assert response.status_code == 422


def test_series_is_ordered_oldest_first(client):
    dates = [r["trade_date"] for r in client.get(PATH.format(code="GP")).json()["prices"]]
    assert dates == sorted(dates)


def test_path_is_versioned_and_schema_is_published(client):
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert any(p.startswith("/v1/") for p in schema.json()["paths"])


def test_trading_days_present_are_discoverable(client):
    response = client.get("/v1/trading-days")
    assert response.status_code == 200
    assert TRADE_DATE in response.json()["trade_dates"]
