"""Load landed Day End Archive responses into `raw`.

This is the only Python that touches the warehouse, and it does as little as
possible: it reads landed bytes, pulls the published columns out as text, and
writes them down beside the provenance needed to trace any row back to the file
it came from. It applies no business rule -- no unit conversion, no
did-not-trade determination, no zero handling. Those live in `staging`, per
ADR 0004, and doing any of them here would mean doing them twice.

`raw` mirrors the source: the exchange's own column names, all text. Coercing to
numeric here would turn a malformed value into a load failure instead of a
visible bad row, and would move "what does zero mean" above the layer boundary.
"""

import argparse
import dataclasses
import datetime as dt
import gzip
import hashlib
import json
import os
import pathlib

import psycopg
from bs4 import BeautifulSoup

# The exchange publishes these in this order. It is not OHLC -- see ADR 0002 and
# the fixture. The names are the exchange's, deliberately, because this is `raw`.
SOURCE_COLUMNS = (
    "row_num", "trade_date", "trading_code", "ltp", "high", "low",
    "openp", "closep", "ycp", "trade", "value_mn", "volume",
)

CREATE_RAW = """
create schema if not exists raw;
create table if not exists raw.day_end (
    row_num        text,
    trade_date     text,
    trading_code   text,
    ltp            text,
    high           text,
    low            text,
    openp          text,
    closep         text,
    ycp            text,
    trade          text,
    value_mn       text,
    volume         text,
    _source_file   text        not null,
    _source_sha256 text        not null,
    _loaded_at     timestamptz not null default now()
);
create index if not exists day_end_trade_date_idx on raw.day_end (trade_date);
"""


def parse(payload: bytes) -> list[dict]:
    """Pull the published columns out of a Day End Archive response, as text."""
    soup = BeautifulSoup(payload, "html.parser")
    rows = []
    for tr in soup.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) < len(SOURCE_COLUMNS):
            continue
        values = [c.get_text(strip=True) for c in cells[: len(SOURCE_COLUMNS)]]
        row = dict(zip(SOURCE_COLUMNS, values))
        # The header and any layout rows do not carry a date in this position.
        if len(row["trade_date"]) == 10 and row["trade_date"][4] == "-":
            rows.append(row)
    return rows


@dataclasses.dataclass
class LoadReport:
    """What a load actually did. A gap the operator never hears about is the
    failure mode; the gap itself is recoverable while the day is still served."""

    loaded: dict[str, int] = dataclasses.field(default_factory=dict)
    missing: list[str] = dataclasses.field(default_factory=list)
    non_trading: list[str] = dataclasses.field(default_factory=list)

    def summary(self) -> str:
        parts = [f"loaded {len(self.loaded)} trading days, {sum(self.loaded.values())} rows"]
        if self.non_trading:
            parts.append(f"{len(self.non_trading)} non-trading days")
        if self.missing:
            parts.append(f"MISSING from landing: {', '.join(self.missing)}")
        return "; ".join(parts)


def _as_date(value) -> dt.date | None:
    if value is None or isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(value)


def dates_to_consider(landing: pathlib.Path, start: dt.date | None, end: dt.date | None):
    """Every date worth an opinion.

    Given a range, walk it day by day so a date with no landed file can be
    reported rather than silently passed over. Without a range, only what is
    actually on disk is considered -- there is no calendar to compare against.
    """
    if start and end:
        step = start
        while step <= end:
            yield step
            step += dt.timedelta(days=1)
        return
    # Sidecars count as landed too: one marks a date the exchange held no
    # session on, which is an answer rather than an absence.
    seen = {
        dt.date.fromisoformat(path.name.split(".")[0])
        for pattern in ("*.html.gz", "*.json")
        for path in landing.glob(pattern)
    }
    yield from sorted(seen)


def load(connection, landing: pathlib.Path, start=None, end=None) -> LoadReport:
    start, end = _as_date(start), _as_date(end)
    with connection.cursor() as cursor:
        cursor.execute(CREATE_RAW)
    connection.commit()

    report = LoadReport()
    for date in dates_to_consider(landing, start, end):
        iso = date.isoformat()
        path = landing / f"{iso}.html.gz"

        if not path.exists():
            sidecar = landing / f"{iso}.json"
            # The capture script leaves a marker for a date the exchange held no
            # session on. Absent that, the day is genuinely unaccounted for.
            if sidecar.exists() and not json.loads(sidecar.read_text()).get("trading_day", True):
                report.non_trading.append(iso)
            else:
                report.missing.append(iso)
            continue

        payload = gzip.decompress(path.read_bytes())
        rows = parse(payload)
        digest = hashlib.sha256(payload).hexdigest()

        # A Trading Day is the unit of loading, because the source publishes a
        # complete day at a time. Replacing the day rather than merging row by
        # row means a day that shrinks leaves no orphans behind.
        with connection.cursor() as cursor:
            cursor.execute("delete from raw.day_end where trade_date = %s", (iso,))
            cursor.executemany(
                f"""insert into raw.day_end ({", ".join(SOURCE_COLUMNS)}, _source_file, _source_sha256)
                    values ({", ".join(["%s"] * len(SOURCE_COLUMNS))}, %s, %s)""",
                [[row[c] for c in SOURCE_COLUMNS] + [path.name, digest] for row in rows],
            )
        connection.commit()
        report.loaded[iso] = len(rows)

    return report


def connect():
    return psycopg.connect(
        host=os.environ["DSE_PG_HOST"], port=os.environ["DSE_PG_PORT"],
        dbname=os.environ["DSE_PG_DATABASE"], user=os.environ["DSE_PG_USER"],
        password=os.environ["DSE_PG_PASSWORD"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--landing", type=pathlib.Path, required=True)
    parser.add_argument("--start-date", type=dt.date.fromisoformat)
    parser.add_argument("--end-date", type=dt.date.fromisoformat)
    args = parser.parse_args()

    with connect() as connection:
        report = load(connection, args.landing, args.start_date, args.end_date)
    print(report.summary())


if __name__ == "__main__":
    main()
