# Python ingests, dbt transforms

Python may fetch bytes, write them to landing, and load landing into `raw` with
type coercion no more sophisticated than "make it text". Every join, derivation,
business rule and indicator after that point is dbt SQL. No pandas transformation
step, no Python-computed indicators, no SQL in Python beyond the load statement.

## Consequences

This is a deliberate constraint, and a reader will otherwise assume the opposite
— computing an RSI in pandas is easier than computing it in a window function.

We accept the difficulty because it is the rule that keeps the lineage graph true
and the tests visible. The common failure of this kind of project is that Python
quietly does the real work while dbt performs a `SELECT *` over the result, at
which point the lineage diagram is decorative. It also forces the SQL depth the
project is partly meant to build.
