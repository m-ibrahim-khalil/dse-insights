# DSE Market Intelligence

Bangladesh equity market data from the Dhaka Stock Exchange — collected, cleaned,
modelled, and served. This glossary fixes the language used across the ingestion,
warehouse, dbt and API layers.

## Market

**Instrument**:
A tradable listing with its own trading code. The thing prices attach to.
_Avoid_: company, stock, share, security, ticker

**Trading Code**:
The exchange's short identifier for an instrument, e.g. `BATBC`, `ABBLPBOND`.
_Avoid_: symbol, ticker, code

**Issuer**:
The organisation that issued an instrument. One issuer may have several instruments.
_Avoid_: company, firm

**Instrument Type**:
What kind of thing an instrument is — equity, corporate bond, mutual fund, treasury.
_Avoid_: asset class, security type

**Instrument Category**:
The exchange's own A/B/N/Z quality marking of an instrument.
_Avoid_: grade, class, tier

**Sector**:
The exchange's industry classification of an instrument.
_Avoid_: industry, segment

## Time

**Trading Day**:
A calendar date on which the exchange held a session. Sunday to Thursday, less holidays.
_Avoid_: business day, weekday, market day

**Trading Calendar**:
The set of trading days, derived from which dates actually return data.
_Avoid_: holiday calendar, schedule

## Prices

**Close Price**:
The exchange's official closing price for an instrument on a trading day.
_Avoid_: close, closing price, CLOSEP, final price

**Last Traded Price**:
The price of the final execution of the day. Differs from the close price.
_Avoid_: LTP, last price, final trade

**Previous Close**:
The close price of the instrument's preceding trading day, as published by the exchange.
_Avoid_: YCP, yesterday close, prior close

**Open Price**, **High Price**, **Low Price**:
First, highest and lowest execution prices of the trading day.
_Avoid_: OPENP, O/H/L

**Unadjusted Price**:
A price exactly as traded. The only kind of price the exchange publishes.
_Avoid_: raw price, nominal price

**Adjusted Price**:
A price restated so a series is continuous across corporate actions. Always
derived, never stored, and only meaningful alongside the date it was derived on.
_Avoid_: normalised price, split-adjusted

**Circuit Limit**:
The exchange's cap on how far an instrument may move from its Previous Close in
one Trading Day, currently 10% in each direction.
_Avoid_: price band, limit up, limit down, halt

## Corporate Actions

**Corporate Action**:
An issuer event that changes the share count or the value of a share.
_Avoid_: event, action, announcement

**Bonus Issue**:
Additional shares distributed to holders, quoted as a percentage. The exchange
also calls this a stock dividend.
_Avoid_: stock dividend, scrip issue, bonus share

**Rights Issue**:
An offer to existing holders to buy new shares, usually below market price.
_Avoid_: rights offering

**Cash Dividend**:
A cash payment to holders, quoted as a percentage of face value rather than of
price. Not adjusted for.
_Avoid_: dividend, payout

**Record Date**:
The date determining who receives a Corporate Action. The instrument Did Not
Trade on this day.
_Avoid_: book closure, cutoff

**Ex-Date**:
The first Trading Day on which an instrument trades without entitlement to a
Corporate Action. The day its price visibly steps.
_Avoid_: ex-dividend date, effective date

**Adjustment Factor**:
The multiplier relating an instrument's price before an Ex-Date to its price
after. A 25% Bonus Issue gives a factor of 1.25.
_Avoid_: ratio, multiplier, split factor

**Price Return**:
A series adjusted for Bonus Issues, splits and Rights Issues, but not for Cash
Dividends. The only series this project produces.
_Avoid_: return series, adjusted series

**Total Return**:
A series additionally adjusted for Cash Dividends. Not produced.
_Avoid_: TR, gross return

**Adjustment Coverage**:
Whether an instrument's declared Corporate Actions have each been matched to an
observed Ex-Date. Where one has not, the series before it is untrustworthy.
_Avoid_: adjustment quality, confidence

## Activity

**Volume**:
Number of shares that changed hands in a trading day.
_Avoid_: quantity, shares, size

**Turnover**:
Monetary value of trading in a trading day, in Bangladeshi taka.
_Avoid_: value, amount, notional

**Trade Count**:
Number of individual executions in a trading day.
_Avoid_: trades, transactions, deals

**Did Not Trade**:
An instrument that was listed on a trading day but had no executions. It has a
previous close but no open, high, low, close, volume or turnover.
_Avoid_: inactive, suspended, halted, missing, zero-volume

## Sourcing

**Day End Archive**:
The exchange's published end-of-day record for a date range.
_Avoid_: EOD feed, daily dump

**Archive Window**:
The rolling two-year period the exchange serves. Data older than the window is
unavailable from the exchange at any price.
_Avoid_: retention, lookback

**Historical Seed**:
The separately-licensed dataset supplying prices older than the archive window.
_Avoid_: backfill data, history dump

## Pipeline Layers

**Landing**:
Source responses kept exactly as received and never modified.
_Avoid_: bronze, raw files, ingest

**Raw**:
Warehouse tables mirroring a source feed one-to-one, without interpretation.
_Avoid_: bronze, source, ingest, staging

**Staging**:
One typed, deduplicated model per raw table. The first layer where the project's
language replaces the source's.
_Avoid_: silver, cleaned, normalised

**Intermediate**:
Reusable derivations that are not themselves products.
_Avoid_: silver, transform, business logic

**Marts**:
The facts and dimensions other people are meant to consume.
_Avoid_: gold, analytics, warehouse, final
