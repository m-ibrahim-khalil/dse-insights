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


def write_day(directory: pathlib.Path, date: str, *, payload: bytes | None = None) -> pathlib.Path:
    """Land one trading day, by default the fixture restamped to `date`."""
    if payload is None:
        payload = FIXTURE.read_text().replace("2026-09-03", date).encode()
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
