# The modelled entity is an Instrument, not a Company

The dimension is `dim_instrument`, keyed by a surrogate `instrument_key` with
`trading_code` as the natural key and an `instrument_type` attribute. An Issuer
dimension will be added only when something needs it.

## Consequences

The archive returns 636 rows per trading day, and they are not all companies —
`ABBLPBOND` is a corporate bond. A `dim_company` would have been named after
something that is not what the data contains, and the grain would have been
wrong from the first model.

Identity needs care: the archive appears to serve history under an instrument's
*current* trading code, so a rename silently rewrites the past. Landed responses
are then the only evidence a rename occurred. We keep an alias table and diff the
listing page daily. We have not yet observed a rename directly — `BSC` and
`BSCPLC` are two live instruments, not one renamed — so this is a precaution
based on how the endpoint behaves, not on a confirmed incident.
