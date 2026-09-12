# Landing holds original response bytes, not Parquet

Landing stores each source response exactly as received — gzipped, with a JSON
sidecar recording URL, parameters, fetch time, HTTP status and content hash.
Parquet, if we want it, is derived downstream.

## Consequences

The obvious move is to parse on arrival and land columnar files. We reject it
because the exchange's day-end table publishes its columns in the order
`LTP, HIGH, LOW, OPENP, CLOSEP` — not OHLC. A parser that assumes OHLC produces
numbers that are plausible, correctly typed, and wrong.

Combined with the two-year archive window, that is unrecoverable: a parsing bug
discovered in month eighteen can be fixed by reparsing landed HTML, but cannot be
fixed by refetching data that has aged out. Immutable storage is only worth
anything if what was kept is the part that cannot be obtained again.

The cost is storage volume and a parse step on every read of landing.
