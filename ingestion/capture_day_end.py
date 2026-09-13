"""Capture the exchange's day-end archive into landing, one file per date.

Deliberately crude. No schema, no parsing, no database. It exists only because
the exchange serves a rolling two-year window: a trading day we fail to capture
is unrecoverable once it ages out, and no amount of later engineering gets it
back. Everything downstream can be rebuilt from these files at any time.

Stdlib plus certifi. The certifi dependency is not incidental: the exchange's
server sends an incomplete TLS chain, omitting its Sectigo intermediate, so we
pin that intermediate in certs/ and trust it explicitly. curl papers over this
by chasing the certificate's AIA URL; Python does not.
"""

import argparse
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import ssl
import time
import urllib.parse
import urllib.request

ARCHIVE_URL = "https://www.dsebd.org/day_end_archive.php"
USER_AGENT = "dse-market-intelligence/0.1 (personal, non-commercial; contact: ibrahim@sensa.no)"

# The exchange returns this instead of an error when a date has no session, or
# when it falls outside the rolling archive window.
NO_DATA_MARKER = b"No Day End Data"

# A recent date with no data may simply not be published yet, so we retry it on
# later runs. Past this age, no data means it was never a trading day.
FINAL_AFTER_DAYS = 3

# The exchange serves its leaf certificate and then a root, omitting the
# intermediate that links them. Verification therefore fails against a normal
# trust store. We keep verification on and supply the missing link ourselves.
PINNED_INTERMEDIATE = pathlib.Path(__file__).parent / "certs" / "sectigo-dv-r36.pem"


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    context.load_verify_locations(cafile=str(PINNED_INTERMEDIATE))
    return context


def source_url(date: dt.date) -> str:
    query = urllib.parse.urlencode(
        {
            "startDate": date.isoformat(),
            "endDate": date.isoformat(),
            "inst": "All Instrument",
            "archive": "data",
        }
    )
    return f"{ARCHIVE_URL}?{query}"


def fetch(date: dt.date) -> bytes:
    request = urllib.request.Request(
        source_url(date), headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=120, context=ssl_context()) as response:
        return response.read()


def capture(date: dt.date, landing: pathlib.Path, today: dt.date) -> str:
    body = landing / f"{date.isoformat()}.html.gz"
    sidecar = landing / f"{date.isoformat()}.json"

    if sidecar.exists():
        return "skipped"

    payload = fetch(date)

    if NO_DATA_MARKER in payload:
        if (today - date).days < FINAL_AFTER_DAYS:
            return "no data yet, will retry"
        sidecar.write_text(
            json.dumps(
                {
                    "trade_date": date.isoformat(),
                    "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "trading_day": False,
                },
                indent=2,
            )
        )
        return "not a trading day"

    body.write_bytes(gzip.compress(payload))
    sidecar.write_text(
        json.dumps(
            {
                "trade_date": date.isoformat(),
                "source_url": source_url(date),
                "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "trading_day": True,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "file": body.name,
            },
            indent=2,
        )
    )
    return f"captured {len(payload):,} bytes"


def capture_range(landing: pathlib.Path, start: dt.date, end: dt.date, today=None) -> dict:
    """Capture every date from `start` to `end` inclusive.

    Oldest first, so an interrupted run loses the newest date -- which is also
    the one most likely to still be refetchable tomorrow.
    """
    landing.mkdir(parents=True, exist_ok=True)
    today = today or dt.date.today()

    outcomes: dict[str, str] = {}
    date = start
    while date <= end:
        try:
            outcomes[date.isoformat()] = capture(date, landing, today)
        except Exception as error:
            # One bad date must not cost us the rest of the window.
            outcomes[date.isoformat()] = f"FAILED {error!r}"
        print(f"{date}: {outcomes[date.isoformat()]}", flush=True)
        date += dt.timedelta(days=1)
        if date <= end:
            time.sleep(2)
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7,
                        help="Capture this many days back from today. Ignored if --start-date is given.")
    parser.add_argument("--start-date", type=dt.date.fromisoformat)
    parser.add_argument("--end-date", type=dt.date.fromisoformat,
                        help="Defaults to yesterday when --start-date is given.")
    parser.add_argument("--landing", type=pathlib.Path, default=pathlib.Path("landing/dse/day_end"))
    args = parser.parse_args()

    today = dt.date.today()
    if args.start_date:
        start, end = args.start_date, args.end_date or today - dt.timedelta(days=1)
    else:
        start, end = today - dt.timedelta(days=args.days), today - dt.timedelta(days=1)

    outcomes = capture_range(args.landing, start, end, today)
    if any(o.startswith("FAILED") for o in outcomes.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
