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
import datetime as dt
import gzip
import hashlib
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


def landed_files(landing: pathlib.Path, start: dt.date | None, end: dt.date | None):
    for path in sorted(landing.glob("*.html.gz")):
        date = dt.date.fromisoformat(path.name.split(".")[0])
        if start and date < start:
            continue
        if end and date > end:
            continue
        yield date, path


def load(connection, landing: pathlib.Path, start=None, end=None) -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute(CREATE_RAW)
    connection.commit()

    written = {}
    for date, path in landed_files(landing, start, end):
        payload = gzip.decompress(path.read_bytes())
        rows = parse(payload)
        digest = hashlib.sha256(payload).hexdigest()

        # A Trading Day is the unit of loading, because the source publishes a
        # complete day at a time. Replacing the day rather than merging row by
        # row means a day that shrinks leaves no orphans behind.
        with connection.cursor() as cursor:
            cursor.execute("delete from raw.day_end where trade_date = %s", (date.isoformat(),))
            cursor.executemany(
                f"""insert into raw.day_end ({", ".join(SOURCE_COLUMNS)}, _source_file, _source_sha256)
                    values ({", ".join(["%s"] * len(SOURCE_COLUMNS))}, %s, %s)""",
                [[row[c] for c in SOURCE_COLUMNS] + [path.name, digest] for row in rows],
            )
        connection.commit()
        written[date.isoformat()] = len(rows)
        print(f"{date}: {len(rows)} rows")
    return written


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
        load(connection, args.landing, args.start_date, args.end_date)


if __name__ == "__main__":
    main()
