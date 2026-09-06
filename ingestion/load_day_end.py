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
    rows_read: dict[str, int] = dataclasses.field(default_factory=dict)
    missing: list[str] = dataclasses.field(default_factory=list)
    non_trading: list[str] = dataclasses.field(default_factory=list)
    failed: dict[str, str] = dataclasses.field(default_factory=dict)
    refused: dict[str, str] = dataclasses.field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.failed and not self.refused

    def summary(self) -> str:
        parts = [f"loaded {len(self.loaded)} trading days, {sum(self.loaded.values())} rows"]
        if self.non_trading:
            parts.append(f"{len(self.non_trading)} non-trading days")
        if self.missing:
            parts.append(f"MISSING from landing: {', '.join(self.missing)}")
        for date, reason in sorted(self.refused.items()):
            parts.append(f"REFUSED {date}: {reason}")
        for date, reason in sorted(self.failed.items()):
            parts.append(f"FAILED {date}: {reason}")
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


# A truncated day is refused when it falls below this fraction of what recent
# days actually contained. The expectation comes from history; only the
# tolerance is stated here, and it is deliberately generous -- the instrument
# count is stable day to day, so a genuine truncation is dramatic, not marginal.
SHORT_DAY_TOLERANCE = 0.5

RECENT_ROW_COUNTS = """
select count(*) as rows
from raw.day_end
where trade_date < %s
group by trade_date
order by trade_date desc
limit %s
"""


def expected_rows(connection, before: str, sample: int = 10) -> float | None:
    """The median row count of recent trading days already loaded.

    Derived from what this warehouse has actually seen rather than from a
    constant: the original plan hardcoded an expectation of ~300 instruments and
    was wrong by half. There is no basis to judge a day until history exists.
    """
    with connection.cursor() as cursor:
        cursor.execute(RECENT_ROW_COUNTS, (before, sample))
        counts = sorted(row[0] for row in cursor.fetchall())
    if not counts:
        return None
    middle = len(counts) // 2
    if len(counts) % 2:
        return float(counts[middle])
    return (counts[middle - 1] + counts[middle]) / 2


def load(connection, landing: pathlib.Path, start=None, end=None, allow_short_days=None) -> LoadReport:
    start, end = _as_date(start), _as_date(end)
    allowed_short = set(allow_short_days or ())
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

        # One unreadable file must not cost the operator the rest of a recovery.
        try:
            payload = gzip.decompress(path.read_bytes())
            rows = parse(payload)
        except Exception as error:
            report.failed[iso] = f"{path.name}: {type(error).__name__}: {error}"
            continue

        report.rows_read[iso] = len(rows)

        expected = expected_rows(connection, iso)
        if expected and len(rows) < expected * SHORT_DAY_TOLERANCE and iso not in allowed_short:
            report.refused[iso] = (
                f"{path.name}: {len(rows)} rows against a recent median of {expected:.0f}; "
                f"pass --allow-short-day {iso} if the day is genuinely short"
            )
            continue

        digest = hashlib.sha256(payload).hexdigest()

        # A Trading Day is the unit of loading, because the source publishes a
        # complete day at a time. Replacing the day rather than merging row by
        # row means a day that shrinks leaves no orphans behind.
        try:
            with connection.cursor() as cursor:
                cursor.execute("delete from raw.day_end where trade_date = %s", (iso,))
                cursor.executemany(
                    f"""insert into raw.day_end ({", ".join(SOURCE_COLUMNS)}, _source_file, _source_sha256)
                        values ({", ".join(["%s"] * len(SOURCE_COLUMNS))}, %s, %s)""",
                    [[row[c] for c in SOURCE_COLUMNS] + [path.name, digest] for row in rows],
                )
            connection.commit()
        except Exception as error:
            connection.rollback()
            report.failed[iso] = f"{path.name}: {type(error).__name__}: {error}"
            continue

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
    parser.add_argument(
        "--allow-short-day", action="append", default=[], metavar="YYYY-MM-DD",
        help="Load this date even if its row count looks truncated.",
    )
    args = parser.parse_args()

    with connect() as connection:
        report = load(
            connection, args.landing, args.start_date, args.end_date,
            allow_short_days=args.allow_short_day,
        )
    for date in sorted(report.rows_read):
        print(f"{date}: read {report.rows_read[date]}, wrote {report.loaded.get(date, 0)}")
    print(report.summary())
    if not report.ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
