"""Build throwaway landing directories from the committed fixture.

Ticket 05 and 06 need landing directories of their own -- different dates,
deliberately broken files -- without disturbing the shared fixture set the
pipeline tests rely on.
"""

import gzip
import hashlib
import json
import pathlib

FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "day_end_2026-09-03.html"


FIXTURE_DATE = "2026-09-03"


def write_day(directory: pathlib.Path, date: str, *, payload: bytes | None = None) -> pathlib.Path:
    """Land one trading day as the fixture, restamped to `date`.

    Restamping applies to a supplied payload too. Without that, a file named for
    one date carries rows dated another, and an assertion that "no rows exist for
    this date" passes for entirely the wrong reason.
    """
    if payload is None:
        payload = FIXTURE.read_text().encode()
    payload = payload.replace(FIXTURE_DATE.encode(), date.encode())
    path = directory / f"{date}.html.gz"
    path.write_bytes(gzip.compress(payload))
    (directory / f"{date}.json").write_text(json.dumps({
        "trade_date": date, "trading_day": True,
        "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
        "file": path.name,
    }))
    return path


def write_non_trading_day(directory: pathlib.Path, date: str) -> None:
    """Land the marker the capture script leaves for a date with no session."""
    (directory / f"{date}.json").write_text(json.dumps({
        "trade_date": date, "trading_day": False,
    }))


# code, ltp, high, low, openp, closep, ycp, trade, value_mn, volume
HEALTHY_ROW = ("GP", "285.40", "288.00", "283.10", "284.00", "285.90", "283.50",
               "1,205", "45.678", "159,842")
NON_TRADED_ROW = ("TB10Y0127", "0", "0", "0", "0", "97.63", "97.61", "0", "0", "0")


def render_day(date: str, rows) -> bytes:
    """Build a Day End Archive response with exactly the rows given.

    Used to construct data that is deliberately wrong, so an assertion can be
    watched to fail. An assertion nobody has seen fail is indistinguishable from
    one that cannot.
    """
    head = (
        "<html><body><table class='fixedHeader'><thead><tr>"
        "<th>#</th><th>DATE</th><th>TRADING CODE</th><th>LTP*</th><th>HIGH</th>"
        "<th>LOW</th><th>OPENP*</th><th>CLOSEP*</th><th>YCP</th><th>TRADE</th>"
        "<th>VALUE (mn)</th><th>VOLUME</th></tr></thead><tbody>"
    )
    body = ""
    for index, row in enumerate(rows, start=1):
        code, *values = row
        cells = "".join(f"<td>{v}</td>" for v in values)
        body += (
            f"<tr><td>{index}</td><td>{date}</td>"
            f"<td><a href='displayCompany.php?name={code}'> {code} </a></td>{cells}</tr>"
        )
    return (head + body + "</tbody></table></body></html>").encode()


def write_rows(directory: pathlib.Path, date: str, rows) -> pathlib.Path:
    return write_day(directory, date, payload=render_day(date, rows))
