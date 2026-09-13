"""Expected values for the hand-built fixture, in one place.

Ticket 02 asserts these by querying the warehouse; ticket 04 asserts the same
values back over HTTP. One set of truths, two readers -- if these ever disagree
with the fixture, the fixture is what changed.

Every OHLC value below differs from every other on the same row, deliberately.
The source publishes its columns in the order LTP, HIGH, LOW, OPENP, CLOSEP, so
a parser that assumes OHLC yields plausible, correctly typed, wrong numbers.
Distinct values are what make that transposition visible.
"""

from decimal import Decimal as D

TRADE_DATE = "2026-09-03"

# trading_code -> expected fact_daily_price row, in project vocabulary
EXPECTED = {
    "RECKITTBEN": dict(
        open_price=D("4150.00"), high_price=D("4180.00"), low_price=D("4090.10"),
        close_price=D("4125.30"), last_traded_price=D("4120.50"),
        previous_close=D("4160.70"), trade_count=312,
        turnover=D("12456000.000"), volume=3021, did_not_trade=False,
    ),
    "GP": dict(
        open_price=D("284.00"), high_price=D("288.00"), low_price=D("283.10"),
        close_price=D("285.90"), last_traded_price=D("285.40"),
        previous_close=D("283.50"), trade_count=1205,
        turnover=D("45678000.000"), volume=159842, did_not_trade=False,
    ),
    "1STPRIMFMF": dict(
        open_price=D("21.90"), high_price=D("22.10"), low_price=D("21.60"),
        close_price=D("21.80"), last_traded_price=D("21.70"),
        previous_close=D("21.90"), trade_count=224,
        turnover=D("3313000.000"), volume=152200, did_not_trade=False,
    ),
    # A bond, not a company -- ADR 0005. Also the thousands-separator price test.
    "ABBLPBOND": dict(
        open_price=D("1059.00"), high_price=D("1062.50"), low_price=D("1058.00"),
        close_price=D("1061.20"), last_traded_price=D("1060.00"),
        previous_close=D("1060.00"), trade_count=12,
        turnover=D("1273000.000"), volume=1200, did_not_trade=False,
    ),
    # A treasury bond. It never trades, yet the exchange publishes a close for it
    # every day -- a valuation, not a trade. Zeroed OHLC means "no trades
    # happened"; the close is real information and the only price these
    # instruments ever have.
    "TB10Y0127": dict(
        open_price=None, high_price=None, low_price=None,
        close_price=D("97.63"), last_traded_price=None,
        previous_close=D("97.61"), trade_count=0,
        turnover=D("0.000"), volume=0, did_not_trade=True,
    ),
    # A treasury bond on its maturity day. The exchange zeroes everything
    # including the close, keeping only the previous close. A zero close is not a
    # price of zero, it is the absence of a valuation -- left as 0 it reads as a
    # -100% return on an instrument that matured at par.
    "TB15Y0925": dict(
        open_price=None, high_price=None, low_price=None,
        close_price=None, last_traded_price=None,
        previous_close=D("100.00"), trade_count=0,
        turnover=D("0.000"), volume=0, did_not_trade=True,
    ),
    "SQURPHARMA": dict(
        open_price=D("216.50"), high_price=D("217.90"), low_price=D("214.00"),
        close_price=D("215.80"), last_traded_price=D("215.30"),
        previous_close=D("214.60"), trade_count=890,
        turnover=D("28901000.000"), volume=133940, did_not_trade=False,
    ),
}
