"""Read-only access to the modelled price history.

Not exposed publicly: the exchange permits personal, non-commercial use and
prohibits redistribution, so this serves the operator, not the internet
(ADR 0001).
"""

import datetime as dt
import os
from decimal import Decimal

import psycopg
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

app = FastAPI(
    title="DSE Market Intelligence",
    version="0.1.0",
    description=(
        "Daily price history for Dhaka Stock Exchange instruments. Prices are "
        "UNADJUSTED: they are not restated across bonus issues, splits or rights "
        "issues, and never for cash dividends (ADR 0008, ADR 0010)."
    ),
)


def connect():
    return psycopg.connect(
        host=os.environ["DSE_PG_HOST"], port=os.environ["DSE_PG_PORT"],
        dbname=os.environ["DSE_PG_DATABASE"], user=os.environ["DSE_PG_USER"],
        password=os.environ["DSE_PG_PASSWORD"],
    )


class DailyPrice(BaseModel):
    trade_date: dt.date
    open_price: Decimal | None = Field(None, description="Null when the instrument did not trade.")
    high_price: Decimal | None = None
    low_price: Decimal | None = None
    close_price: Decimal | None = Field(
        None, description="The exchange's official weighted close, not the last trade."
    )
    last_traded_price: Decimal | None = Field(
        None, description="Final execution of the day. Null when the instrument did not trade."
    )
    previous_close: Decimal | None = None
    volume: int | None = Field(None, description="Shares traded. Zero, not null, on a non-traded day.")
    turnover: Decimal | None = Field(None, description="Taka, not millions.")
    trade_count: int | None = None
    did_not_trade: bool = Field(
        description="Listed, but no trades occurred. The close is still a published valuation."
    )


class PriceSeries(BaseModel):
    trading_code: str
    price_basis: str = Field(
        "unadjusted",
        description="Always 'unadjusted'. Adjusted series are derived elsewhere, never stored.",
    )
    count: int
    prices: list[DailyPrice]


class TradingDays(BaseModel):
    trade_dates: list[dt.date]


SERIES_SQL = """
select f.trade_date, f.open_price, f.high_price, f.low_price, f.close_price,
       f.last_traded_price, f.previous_close, f.volume, f.turnover,
       f.trade_count, f.did_not_trade
from marts.fact_daily_price f
join marts.dim_instrument i using (instrument_key)
where i.trading_code = %(trading_code)s
  and (%(start_date)s::date is null or f.trade_date >= %(start_date)s::date)
  and (%(end_date)s::date is null or f.trade_date <= %(end_date)s::date)
order by f.trade_date
"""


@app.get("/v1/instruments/{trading_code}/prices", response_model=PriceSeries)
def price_series(
    trading_code: str,
    start_date: dt.date | None = Query(None, description="Inclusive lower bound."),
    end_date: dt.date | None = Query(None, description="Inclusive upper bound."),
) -> PriceSeries:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail=f"start_date {start_date} is after end_date {end_date}",
        )

    with connect() as connection, connection.cursor() as cursor:
        # An unknown Trading Code and an Instrument with no rows in range are
        # different answers, so the dimension is checked before the range is applied.
        cursor.execute(
            "select 1 from marts.dim_instrument where trading_code = %s", (trading_code,)
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail=f"unknown trading code: {trading_code}")

        cursor.execute(
            SERIES_SQL,
            {"trading_code": trading_code, "start_date": start_date, "end_date": end_date},
        )
        columns = [c.name for c in cursor.description]
        prices = [DailyPrice(**dict(zip(columns, row))) for row in cursor.fetchall()]

    return PriceSeries(trading_code=trading_code, count=len(prices), prices=prices)


@app.get("/v1/trading-days", response_model=TradingDays)
def trading_days() -> TradingDays:
    """Which Trading Days the warehouse holds.

    Answered from the fact itself: a Trading Calendar does not exist yet, so this
    reports what was loaded, not what the exchange held a session on.
    """
    with connect() as connection, connection.cursor() as cursor:
        cursor.execute("select distinct trade_date from marts.fact_daily_price order by 1")
        return TradingDays(trade_dates=[row[0] for row in cursor.fetchall()])
