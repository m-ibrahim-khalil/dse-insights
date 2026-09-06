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
