# Price return, not total return

Series are adjusted for Bonus Issues, splits and Rights Issues, and never for
Cash Dividends. Models describing a price series say so explicitly.

## Consequences

A Total Return series is the more complete measure and a reader may expect it.
We do not produce one, for three reasons.

Cash Dividends on this exchange are quoted as a percentage of face value rather
than of price, so a 5% dividend on a Tk 10 face value is Tk 0.50 — roughly 2% of
a Tk 25 share, far below the Circuit Limit and therefore undetectable in price
data. The declaration gives a year, not an Ex-Date, so there is nothing reliable
to adjust against.

Every technical indicator this project will build conventionally assumes a
price-return series. A Total Return series would make our RSI disagree with every
chart a reader compares it to, and the disagreement would look like a bug.

Total Return remains a legitimate later product once Corporate Action Ex-Dates
are reliable. It is a different dataset, not a correction to this one.
