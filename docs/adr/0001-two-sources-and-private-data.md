# Two data sources, and exchange data stays private

The exchange serves only a rolling two-year archive window, so it cannot supply
the deeper history this project wants; a separately-published CC BY 4.0 dataset
covers roughly 2012 to early 2026 and may be redistributed with attribution. We
therefore take history from the licensed dataset and daily freshness from the
exchange, and we keep exchange-derived data private.

## Considered Options

Scraping the exchange as the only source was the original plan. It fails on
history — full calendar years 2010 and 2015 return zero rows, verified against
the live endpoint, not inferred from the date picker.

Buying a licence through the exchange's data sale service remains open and is
worth an email regardless; pricing is unpublished.

## Consequences

The exchange's copyright notice permits download "for your personal and
non-commercial use only" and prohibits redistribution, commercial exploitation,
and transmitting or storing the content "in any other website or other form of
electronic retrieval system". Scraping as a technique is never mentioned, and no
robots.txt is published. Read strictly, the storage clause would describe any
warehouse; read practically, a private non-commercial platform sits inside the
carve-out and a public API re-serving exchange prices does not.

So: the repository holds code and small fixtures, never a data dump. Any public
demo serves only data we are licensed to serve, which in practice means the
CC BY 4.0 seed with attribution. This is a deliberate constraint on the shape of
the project, not an oversight — it is why there is no public price endpoint.

None of this is legal advice.
