# DSE Market Intelligence Platform — Project Plan

> **Status:** Planning  
> **Primary goal:** Build a production-grade, end-to-end Data Engineering portfolio project around Dhaka Stock Exchange (DSE) market data.  
> **Primary career goal:** Demonstrate strong Data Engineering fundamentals, production engineering practices, cloud deployment, analytics, and eventually ML/AI readiness.

---

## 1. Project Vision

Build a **DSE Market Intelligence Platform** that collects, stores, transforms, validates, analyzes, and serves Bangladesh stock-market data.

The project should evolve from a simple ETL pipeline into a complete data platform:

```text
DSE / External Sources
        │
        ▼
   Data Ingestion
        │
        ▼
 Raw Object Storage
   S3 / MinIO
        │
        ▼
 Raw / Staging Database
      PostgreSQL
        │
        ▼
       dbt
        │
        ▼
 Analytical Data Models
        │
        ├── Stock Prices
        ├── Returns
        ├── Market Metrics
        ├── Technical Indicators
        ├── Company Data
        └── News
        │
        ▼
      FastAPI
        │
        ├── Analytics
        ├── Dashboard
        └── ML / AI
```

**Apache Airflow** will orchestrate the data workflows, while observability, testing, data quality, CI/CD, and cloud deployment will progressively make the platform production-grade.

---

# 2. Why This Project Exists

The project is designed around a specific career gap:

- Existing professional experience in software engineering.
- Around three years of practical Data Engineering exposure.
- Experience with ETL pipelines and related tooling.
- Need to become more confident with **end-to-end data platform design**.
- Need a substantial project that can be discussed deeply in interviews and included prominently on a CV.
- Need to strengthen understanding of modern Data Engineering practices rather than only individual tools.

The project therefore prioritizes **engineering depth over technology count**.

The objective is not to build something complicated for its own sake.

The objective is to demonstrate:

> **I can design, build, operate, monitor, test, and explain an end-to-end data platform.**

---

# 3. Core Principles

## 3.1 Build while learning

Do not spend months learning every technology before starting the project.

Use:

```text
Learn
  ↓
Implement
  ↓
Break
  ↓
Debug
  ↓
Improve
  ↓
Document
```

Every new Data Engineering concept should ideally become part of the project.

---

## 3.2 Start simple, then evolve

Do not introduce Spark, Kafka, Kubernetes, or other distributed technologies just because they appear in Data Engineering job descriptions.

First build a reliable batch platform.

Then introduce technologies when there is a real architectural reason.

---

## 3.3 Prefer production thinking

The project should eventually demonstrate:

- Incremental ingestion
- Idempotency
- Backfills
- Retry handling
- Data validation
- Schema evolution
- Data quality
- Data lineage
- Testing
- CI/CD
- Monitoring
- Alerting
- Logging
- Observability
- Security
- Cloud deployment
- Cost awareness

---

# 4. Project Scope

The project will be developed in stages.

## MVP

The first version should contain only:

```text
DSE company data
        +
Daily historical/current OHLCV data
        ↓
Raw storage
        ↓
PostgreSQL
        ↓
dbt
        ↓
Analytical models
        ↓
FastAPI
```

The MVP must work end-to-end before adding news, advanced analytics, ML, or AI.

---

# 5. Long-Term Architecture

The target architecture is:

```text
                        ┌──────────────────────┐
                        │   DSE / Data Sources │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │   Python Ingestion   │
                        │                      │
                        │ API / Scraper        │
                        │ Parser               │
                        │ Retry / Backoff      │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │    S3 / MinIO        │
                        │  Immutable Raw Data  │
                        │      Parquet         │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │     PostgreSQL       │
                        │   Raw / Staging      │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │        dbt           │
                        │                      │
                        │ Staging              │
                        │ Intermediate         │
                        │ Marts                │
                        └──────────┬───────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │     Analytical Layer         │
                    │                              │
                    │ Prices                       │
                    │ Returns                      │
                    │ Market Statistics            │
                    │ Technical Indicators         │
                    │ Company Analytics             │
                    │ News                          │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │       FastAPI       │
                        │                      │
                        │ /stocks             │
                        │ /prices             │
                        │ /indicators         │
                        │ /news               │
                        │ /market             │
                        └──────────┬───────────┘
                                   │
                       ┌───────────┼───────────┐
                       ▼           ▼           ▼
                   Dashboard      ML          AI
```

Airflow operates across the ingestion and transformation workflows:

```text
                         Apache Airflow
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
         Market DAG       Company DAG       News DAG
              │               │                │
              └───────────────┼────────────────┘
                              ▼
                             dbt
                              │
                              ▼
                         Data Products
```

---

# 6. Data Architecture

Use a **Bronze / Silver / Gold** conceptual architecture.

## 6.1 Bronze — Raw

Purpose:

> Preserve source data exactly as received.

Example:

```text
data/
└── bronze/
    └── dse/
        ├── market/
        │   ├── 2026-09-01.json
        │   ├── 2026-09-02.json
        │   └── 2026-09-03.json
        ├── company/
        │   └── 2026-09-03.json
        └── news/
            └── 2026-09-03.json
```

Rules:

- Do not overwrite raw data unnecessarily.
- Preserve extraction timestamps.
- Preserve source metadata.
- Keep enough information to reproduce downstream processing.
- Store large analytical/raw datasets in Parquet where appropriate.

---

## 6.2 Silver — Cleaned

Purpose:

> Standardize and validate source data.

Examples:

```text
silver.market_prices
silver.companies
silver.news
```

Typical transformations:

- Data type conversion
- Null handling
- Duplicate removal
- Date normalization
- Symbol normalization
- Schema validation
- Invalid-record detection

Example price schema:

```text
symbol
trade_date
open
high
low
close
volume
trade_count
turnover
```

---

## 6.3 Gold — Analytics

Purpose:

> Provide trustworthy, business-ready datasets.

Potential models:

```text
dim_company
fact_daily_price
fact_daily_returns
fact_technical_indicators
fact_market_statistics
fact_sector_statistics
fact_news
```

---

# 7. Data Sources

## Phase 1

Primary source:

- Dhaka Stock Exchange market/company data.

Initial data scope:

- Company/symbol list
- Historical daily market data
- Daily OHLCV
- Trading volume
- Turnover/value
- Trade counts where available

---

## Phase 2

Add:

- Financial news
- News metadata
- Company/news relationships
- Additional company information

---

## Phase 3+

Potential additions:

- Financial statements
- Corporate actions
- Dividend information
- Sector information
- Index data
- Other relevant market datasets

All external sources must be evaluated for:

- Availability
- Stability
- Terms of use
- Rate limits
- Data quality
- Historical coverage
- Licensing/redistribution restrictions

---

# 8. Ingestion System

The ingestion layer will primarily use Python.

Potential tools:

```text
Python
Requests / httpx
BeautifulSoup
Playwright
```

Use the simplest reliable method available for each source.

---

## 8.1 Historical ingestion

The system must support:

```bash
python ingest.py \
    --start-date 2010-01-01 \
    --end-date 2026-09-06
```

The historical loader should:

- Extract data in manageable chunks.
- Save raw responses.
- Track extraction metadata.
- Validate records.
- Load data incrementally.
- Support retries.
- Support restart after failure.
- Avoid duplicate data.

---

## 8.2 Incremental ingestion

After historical loading:

```text
Every day
   ↓
Identify missing/new data
   ↓
Extract only required period
   ↓
Validate
   ↓
Store raw
   ↓
Load warehouse
   ↓
Run dbt
```

The pipeline should not repeatedly download the entire history.

---

## 8.3 Backfill

The ingestion system must support:

```bash
python ingest.py \
    --start-date 2025-01-01 \
    --end-date 2025-01-31
```

This allows recovery from:

- Source outages
- Pipeline failures
- Missing historical periods
- Data corrections

---

## 8.4 Idempotency

Running the same ingestion twice should not create duplicates.

A natural uniqueness rule for daily stock prices:

```text
(symbol, trade_date)
```

The pipeline should use appropriate:

- Unique constraints
- Upserts
- MERGE operations
- Deduplication logic

---

# 9. Data Warehouse

Initial warehouse:

**PostgreSQL**

Reasons:

- Familiar technology
- Excellent SQL support
- Good for the initial project
- Easy local development
- Easy cloud deployment
- Strong ecosystem

Do not introduce multiple analytical databases until there is a meaningful reason.

---

# 10. Data Modeling

Use dimensional modeling principles.

Core dimensions:

```text
dim_company
dim_date
dim_sector
```

Core facts:

```text
fact_daily_price
fact_daily_returns
fact_market_statistics
fact_technical_indicators
fact_news
```

Example:

```text
dim_company
-----------
company_key
symbol
company_name
sector
industry
...

        │
        │
        ▼

fact_daily_price
----------------
company_key
trade_date
open
high
low
close
volume
turnover
...
```

Learn and apply:

- Fact tables
- Dimension tables
- Grain
- Primary keys
- Surrogate keys
- Slowly Changing Dimensions
- Star schemas

Do not implement advanced modeling patterns unless they have a real use case.

---

# 11. dbt Transformation Layer

dbt should own the analytical SQL transformation layer.

Suggested structure:

```text
models/
├── staging/
│   ├── stg_dse_prices.sql
│   ├── stg_dse_companies.sql
│   └── stg_dse_news.sql
│
├── intermediate/
│   ├── int_daily_returns.sql
│   ├── int_stock_moving_average.sql
│   └── int_market_statistics.sql
│
└── marts/
    ├── dim_company.sql
    ├── fact_daily_price.sql
    ├── fact_daily_returns.sql
    ├── fact_technical_indicators.sql
    ├── fact_market_statistics.sql
    └── fact_news.sql
```

Learn:

- Models
- Sources
- Seeds
- Tests
- Documentation
- Lineage
- Incremental models
- Macros
- Jinja
- Snapshots
- Materializations

---

# 12. Data Quality

Data quality is a major project feature.

## Price validation

Examples:

```text
high >= low

high >= open
high >= close

low <= open
low <= close

volume >= 0
```

---

## Uniqueness

```text
(symbol, trade_date)
```

must be unique.

---

## Null validation

Critical fields should not unexpectedly be null:

```text
symbol
trade_date
close
```

---

## Completeness

Example:

```text
Expected companies: ~300
Received: 120

=> Data quality failure
```

The exact expected count should come from reliable project metadata rather than a hardcoded assumption where possible.

---

## Freshness

Monitor:

```text
Latest available data
Expected latest data
```

If data is late:

```text
DATA FRESHNESS FAILURE
```

---

## Data-quality tooling

Start with:

```text
dbt tests
```

Then consider:

```text
Great Expectations
Elementary
```

only if they add meaningful value.

---

# 13. Airflow Orchestration

Create separate workflows.

## Market DAG

```text
extract_market_data
        ↓
validate_raw_data
        ↓
store_raw_data
        ↓
load_postgres
        ↓
dbt_staging
        ↓
dbt_marts
        ↓
quality_checks
        ↓
notify
```

---

## Company DAG

```text
extract_companies
        ↓
validate
        ↓
store_raw
        ↓
load_postgres
        ↓
dbt_company_models
```

---

## News DAG

```text
extract_news
        ↓
deduplicate
        ↓
store_raw
        ↓
load_database
        ↓
dbt_news
```

---

## Airflow concepts to learn

- DAGs
- Tasks
- Task dependencies
- Scheduling
- Retries
- Sensors
- Connections
- Variables
- Secrets
- Backfills
- Catchup
- Task groups
- Failure handling
- Logging
- Alerting

Later investigate modern Airflow concepts such as data-aware/event-driven scheduling where useful.

---

# 14. Analytics Layer

The analytical layer should provide reusable metrics.

## Price metrics

```text
Open
High
Low
Close
Volume
Turnover
```

## Returns

```text
Daily return
Weekly return
Monthly return
YTD return
Cumulative return
```

## Moving averages

```text
SMA 20
SMA 50
SMA 200

EMA 12
EMA 20
EMA 26
EMA 50
```

## Momentum

```text
RSI 14
ROC
Stochastic Oscillator
Williams %R
```

## MACD

```text
MACD
MACD Signal
MACD Histogram
```

## Volatility

```text
Rolling volatility
Historical volatility
ATR
Bollinger Bands
```

## Market statistics

```text
Advancing stocks
Declining stocks
Unchanged stocks

New highs
New lows

Market volume
Market turnover
Market return
Market volatility
```

## Sector analytics

```text
Sector return
Sector volume
Sector turnover
Sector volatility
```

---

# 15. Technical Indicator Design Principle

Do not make the project primarily about stock prediction.

The core project is:

> **Reliable financial data infrastructure.**

Technical indicators are analytical products built on top of that infrastructure.

The correct dependency is:

```text
Reliable raw data
       ↓
Clean data
       ↓
Trusted analytical models
       ↓
Technical indicators
       ↓
ML features
```

Not:

```text
Scrape
 ↓
Train model
```

---

# 16. News Layer

Add news after the market-data MVP is stable.

Potential schema:

```text
news_article
------------
id
title
content
source
published_at
url
category
```

Then associate news with companies:

```text
news_article
      │
      ├── company A
      ├── company B
      └── company C
```

Later:

```text
News
 ↓
NLP
 ↓
Sentiment
 ↓
Company
 ↓
Price movement
```

Potential future analytics:

- News volume per company
- News sentiment
- Sentiment vs price movement
- News around abnormal volatility
- News impact windows

---

# 17. FastAPI Data Product

Expose analytical data through REST APIs.

Potential endpoints:

```http
GET /companies
GET /companies/{symbol}

GET /stocks/{symbol}/prices
GET /stocks/{symbol}/indicators
GET /stocks/{symbol}/returns
GET /stocks/{symbol}/news

GET /market/overview
GET /market/sectors
GET /market/statistics
```

Potential response:

```json
{
  "symbol": "GP",
  "price": 285.40,
  "rsi_14": 62.3,
  "ema_20": 281.2,
  "ema_50": 274.8,
  "macd": 3.4,
  "volatility_20d": 0.018
}
```

FastAPI should eventually demonstrate:

- API versioning
- Pagination
- Validation
- Error handling
- Authentication where needed
- Caching
- OpenAPI documentation
- Performance considerations

---

# 18. Dashboard

Build a simple analytical UI after the API.

Possible choices:

```text
Streamlit
```

for speed, or:

```text
React
```

for a stronger full-stack demonstration.

The dashboard does not need to be visually sophisticated.

Example:

```text
DSE Market Intelligence

GP
৳285.40     +2.1%

[ Price Chart ]

RSI       62.3
EMA20     281.2
EMA50     274.8
MACD        3.4

Recent News
----------------------
...
```

Focus on demonstrating the data product.

---

# 19. Testing Strategy

## Python

Use:

```text
pytest
```

Test:

- Extractors
- Parsers
- Normalization
- Transformation helpers
- API behavior

---

## dbt

Test:

- not_null
- unique
- relationships
- accepted_values
- Custom business rules

Example business rules:

```text
close >= 0
volume >= 0
high >= low
```

---

## Integration tests

Eventually test:

```text
Ingestion
   ↓
PostgreSQL
   ↓
dbt
   ↓
FastAPI
```

---

# 20. Observability

Use observability as a first-class feature.

Track:

```text
pipeline_duration
records_ingested
records_processed
records_failed
data_freshness
data_quality_failures

API_requests
API_error_rate
API_latency
```

Potential stack:

```text
Prometheus
Grafana
```

Dashboard example:

```text
DSE Data Platform
----------------------------

Pipeline Status       OK
Last successful run   15:35

Rows ingested         182,431
Rows processed        181,982
Failed rows               449

Data freshness        OK
Data quality          OK

API requests          12,420
API p95 latency          142 ms
```

---

# 21. Logging

Every important pipeline stage should provide structured logs.

Example:

```text
INFO extraction_started
INFO source=dse
INFO date=2026-09-06

INFO extraction_completed
INFO rows=182431

INFO validation_completed
INFO invalid_rows=449

INFO load_completed
INFO inserted=181982
```

Avoid relying only on print statements.

---

# 22. CI/CD

Use GitHub Actions.

Every pull request should eventually run:

```text
lint
 ↓
unit tests
 ↓
dbt tests
 ↓
integration tests
 ↓
Docker build
```

Deployment pipeline:

```text
GitHub
   ↓
GitHub Actions
   ↓
Docker image
   ↓
Container registry
   ↓
AWS deployment
```

---

# 23. Docker

The local development environment should eventually contain services such as:

```text
postgres
minio
airflow
redis
fastapi
frontend
prometheus
grafana
```

Target developer experience:

```bash
docker compose up
```

The entire development platform should become reproducible.

---

# 24. Cloud Deployment

Primary cloud target:

**AWS**

Initial cloud architecture:

```text
                 AWS
                  │
       ┌──────────┼───────────┐
       ▼          ▼           ▼
      S3         RDS         EC2/ECS
   Raw data    PostgreSQL    Services
                              │
                     ┌────────┼────────┐
                     ▼        ▼        ▼
                  Airflow   FastAPI  Monitoring
```

Learn:

```text
IAM
S3
EC2
RDS
ECR
ECS
CloudWatch
VPC
Secrets
```

Later investigate:

```text
Athena
Glue
Redshift
EMR
```

Do not attempt to use every AWS service.

---

# 25. Security

Eventually implement:

- Environment variables for configuration
- Secret management
- IAM least privilege
- No credentials in Git
- Database access restrictions
- API authentication where appropriate
- HTTPS in production
- Secure Docker configuration

---

# 26. Performance

Performance should become a deliberate engineering concern.

Potential areas:

## Ingestion

- Chunking
- Parallel extraction where appropriate
- Connection reuse
- Retry/backoff
- Rate limiting

## Database

- Indexes
- Query optimization
- EXPLAIN
- Partitioning when justified

## Analytics

- Incremental dbt models
- Precomputed metrics
- Appropriate materializations

## API

- Pagination
- Caching
- Efficient queries
- Connection pooling

---

# 27. Advanced Technologies — Introduce Only with a Reason

## Spark

Introduce Spark when there is a meaningful large-scale processing problem.

Example:

```text
S3
 ↓
Large historical dataset
 ↓
Spark
 ↓
Parquet
 ↓
Analytical storage
```

The project should be able to explain:

> Why did we need Spark?

---

## Kafka

Introduce Kafka if the project evolves toward streaming/near-real-time market events.

Example:

```text
DSE
 ↓
Kafka
 ↓
Stream processing
 ↓
Real-time analytics
```

Again, there must be a genuine use case.

---

## Kubernetes

Only introduce Kubernetes if deployment complexity actually justifies it.

Do not add it simply to increase the technology list.

---

# 28. ML Extension

Only begin ML after the data platform is reliable.

Potential ML problems:

```text
Next-day return prediction
Volatility prediction
Market regime classification
Anomaly detection
```

Feature engineering:

```text
RSI
EMA
MACD
Returns
Volume
Volatility
Market statistics
News sentiment
```

Architecture:

```text
Analytical Warehouse
        ↓
Feature Engineering
        ↓
ML Dataset
        ↓
Training
        ↓
Model
        ↓
Prediction API
```

The ML component is an extension, not the foundation.

---

# 29. AI Extension

Long-term possibility:

## DSE AI Analyst

User:

> Why did GP's volatility increase during the last month?

System:

```text
User question
     ↓
LLM
     ↓
Data/API layer
     ↓
Price + volatility + news
     ↓
LLM reasoning/synthesis
     ↓
Human-readable explanation
```

Another example:

> Show me companies whose RSI crossed below 30 while 20-day volume is increasing.

The AI system can translate the request into structured analytical queries.

This turns the project into:

```text
Data Engineering
      ↓
Analytics
      ↓
ML
      ↓
AI
```

---

# 30. Recommended Repository Structure

Initial structure:

```text
dse-market-intelligence/
│
├── README.md
├── PLAN.md
├── LICENSE
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── ingestion/
│   ├── dse/
│   ├── common/
│   └── tests/
│
├── dbt/
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   ├── tests/
│   ├── macros/
│   └── seeds/
│
├── airflow/
│   ├── dags/
│   ├── plugins/
│   └── tests/
│
├── api/
│   ├── app/
│   └── tests/
│
├── dashboard/
│
├── infrastructure/
│   ├── docker/
│   └── terraform/
│
├── monitoring/
│   ├── prometheus/
│   └── grafana/
│
├── ml/
│
├── scripts/
│
└── docs/
    ├── architecture/
    ├── data-model/
    ├── decisions/
    └── runbooks/
```

This structure can evolve as the project grows.

---

# 31. Architecture Decision Records

Create ADRs for important decisions.

Examples:

```text
docs/decisions/
├── 001-postgresql-as-warehouse.md
├── 002-s3-for-raw-storage.md
├── 003-parquet-for-data-files.md
├── 004-dbt-for-transformations.md
└── 005-airflow-for-orchestration.md
```

Each ADR should explain:

```text
Context
Decision
Alternatives
Reasoning
Consequences
```

This will significantly improve the project's interview value.

---

# 32. Documentation Requirements

The final GitHub repository should contain:

## README

Include:

- Project overview
- Architecture diagram
- Features
- Tech stack
- Quick start
- Data flow
- Example API calls
- Dashboard screenshots
- Monitoring screenshots
- Deployment architecture

## Data documentation

Document:

- Sources
- Schemas
- Table grain
- Columns
- Relationships
- Data quality rules

## Operations documentation

Create runbooks for:

```text
Pipeline failure
Data freshness failure
Bad source data
Backfill
Database failure
API failure
```

---

# 33. Learning Roadmap

## Level 1 — Core Fundamentals

Priority: Very High

Learn deeply:

```text
Advanced SQL
Python
Linux
Git
Docker
PostgreSQL
```

SQL topics:

```text
JOIN
GROUP BY
CTE
Subqueries
Window functions
CASE
Date/time operations
Indexes
EXPLAIN
Query optimization
Partitioning
```

---

## Level 2 — Data Engineering Fundamentals

Learn and implement:

```text
ETL vs ELT
Batch processing
Incremental processing
Idempotency
Backfills
Data contracts
Schema evolution
Data quality
Data lineage
Fact/dimension modeling
Star schema
SCD
CDC
Partitioning
```

---

## Level 3 — Modern Data Stack

Focus on:

```text
Airflow
dbt
S3
Parquet
PostgreSQL
Docker
```

Understand:

```text
OLTP
OLAP
Data lake
Data warehouse
Lakehouse
```

---

## Level 4 — Cloud

Primary target:

```text
AWS
```

Learn:

```text
IAM
S3
EC2
RDS
ECR
ECS
CloudWatch
VPC
Secrets
```

---

## Level 5 — Production Data Engineering

Learn:

```text
Observability
Logging
Metrics
Alerting
Data quality
CI/CD
Security
Performance
Reliability
Cost optimization
```

---

## Level 6 — Distributed Systems

Later:

```text
Kafka
Spark
Flink
Kubernetes
Distributed storage
Distributed processing
```

---

# 34. Skill Priority for Career Development

Recommended priority:

| Skill | Priority |
|---|---:|
| Advanced SQL | ⭐⭐⭐⭐⭐ |
| Data Modeling | ⭐⭐⭐⭐⭐ |
| Python for Data Engineering | ⭐⭐⭐⭐⭐ |
| Airflow | ⭐⭐⭐⭐⭐ |
| dbt | ⭐⭐⭐⭐⭐ |
| AWS | ⭐⭐⭐⭐⭐ |
| Data Quality | ⭐⭐⭐⭐⭐ |
| Docker | ⭐⭐⭐⭐⭐ |
| CI/CD | ⭐⭐⭐⭐ |
| PostgreSQL | ⭐⭐⭐⭐ |
| S3 / Parquet | ⭐⭐⭐⭐ |
| Observability | ⭐⭐⭐⭐ |
| Spark | ⭐⭐⭐⭐ |
| Kafka | ⭐⭐⭐ |
| Kubernetes | ⭐⭐⭐ |
| ML | ⭐⭐⭐ |
| AI/LLM | ⭐⭐⭐ |

The project should prioritize **depth and engineering judgment** over collecting technologies.

---

# 35. Development Phases

## Phase 0 — Architecture & Fundamentals

**Goal:** Understand the system before building it.

Tasks:

- [ ] Define project scope
- [ ] Research DSE data sources
- [ ] Define initial data model
- [ ] Design raw storage structure
- [ ] Design PostgreSQL schema
- [ ] Define data quality rules
- [ ] Define ingestion strategy
- [ ] Set up Git repository
- [ ] Write initial architecture documentation

---

## Phase 1 — DSE Market Data MVP

**Goal:** Build the first complete end-to-end pipeline.

Tasks:

- [ ] Build DSE source client
- [ ] Implement historical extraction
- [ ] Implement raw storage
- [ ] Implement Parquet storage where appropriate
- [ ] Create PostgreSQL schema
- [ ] Load historical data
- [ ] Implement incremental ingestion
- [ ] Implement idempotency
- [ ] Implement basic validation
- [ ] Build first dbt models
- [ ] Create first analytical table
- [ ] Build initial FastAPI endpoint

Success criteria:

```text
DSE
 ↓
Python
 ↓
Raw storage
 ↓
PostgreSQL
 ↓
dbt
 ↓
FastAPI
```

works end-to-end.

---

## Phase 2 — Production Data Engineering

**Goal:** Make the pipeline reliable.

Tasks:

- [ ] Introduce Airflow
- [ ] Build DAGs
- [ ] Add retries
- [ ] Add backfills
- [ ] Add failure handling
- [ ] Add data-quality checks
- [ ] Add freshness checks
- [ ] Add structured logging
- [ ] Add unit tests
- [ ] Add dbt tests
- [ ] Add integration tests
- [ ] Dockerize services
- [ ] Create reproducible local environment

---

## Phase 3 — CI/CD & Observability

**Goal:** Operate the platform like a production system.

Tasks:

- [ ] GitHub Actions
- [ ] Linting
- [ ] Automated tests
- [ ] Docker builds
- [ ] Prometheus
- [ ] Grafana
- [ ] Pipeline metrics
- [ ] API metrics
- [ ] Alerts
- [ ] Runbooks

---

## Phase 4 — Financial Analytics

**Goal:** Turn raw market data into useful data products.

Tasks:

- [ ] Daily returns
- [ ] SMA
- [ ] EMA
- [ ] RSI
- [ ] MACD
- [ ] Bollinger Bands
- [ ] Volatility
- [ ] ATR
- [ ] Market statistics
- [ ] Sector statistics
- [ ] Market breadth
- [ ] Analytical API endpoints

---

## Phase 5 — News Intelligence

**Goal:** Combine market and textual data.

Tasks:

- [ ] News ingestion
- [ ] News deduplication
- [ ] News storage
- [ ] Company/news relationships
- [ ] News analytics
- [ ] Sentiment analysis
- [ ] News/price correlation experiments

---

## Phase 6 — Dashboard

**Goal:** Make the data platform demonstrable.

Tasks:

- [ ] Stock search
- [ ] Price charts
- [ ] Technical indicators
- [ ] Market overview
- [ ] Sector overview
- [ ] News section
- [ ] Basic filtering

---

## Phase 7 — AWS Deployment

**Goal:** Demonstrate cloud Data Engineering.

Tasks:

- [ ] Create AWS architecture
- [ ] S3 raw storage
- [ ] RDS PostgreSQL
- [ ] ECR
- [ ] EC2/ECS deployment
- [ ] IAM
- [ ] Secrets
- [ ] CloudWatch
- [ ] HTTPS
- [ ] Cost monitoring

---

## Phase 8 — ML

**Goal:** Build ML products on top of the trusted data platform.

Tasks:

- [ ] Feature engineering
- [ ] Dataset generation
- [ ] Baseline model
- [ ] Evaluation
- [ ] Experiment tracking
- [ ] Model serving
- [ ] Prediction API

Potential tasks:

```text
Return prediction
Volatility prediction
Regime classification
Anomaly detection
```

---

## Phase 9 — AI

**Goal:** Explore an AI-powered financial research product.

Potential product:

**DSE AI Analyst**

Features:

- Natural-language market questions
- Company analysis
- News + price analysis
- Analytical query generation
- Explanation of market movements
- Retrieval over financial/news data

---

# 36. Definition of Done

The project should eventually satisfy the following.

## Data

- [ ] Historical DSE data available
- [ ] Daily incremental ingestion
- [ ] Raw data preserved
- [ ] Backfill supported
- [ ] Idempotent ingestion
- [ ] Data quality checks

## Data Engineering

- [ ] Airflow orchestration
- [ ] dbt transformations
- [ ] Dimensional modeling
- [ ] Incremental models
- [ ] Data lineage
- [ ] Data documentation

## Production Engineering

- [ ] Docker
- [ ] Automated tests
- [ ] CI/CD
- [ ] Structured logging
- [ ] Metrics
- [ ] Monitoring
- [ ] Alerting
- [ ] Runbooks

## Data Products

- [ ] Analytical tables
- [ ] Technical indicators
- [ ] FastAPI
- [ ] Dashboard

## Cloud

- [ ] AWS deployment
- [ ] S3
- [ ] PostgreSQL/RDS
- [ ] IAM
- [ ] Container deployment
- [ ] Monitoring

## Advanced

- [ ] News intelligence
- [ ] ML
- [ ] AI analyst

---

# 37. Portfolio / CV Positioning

Do not describe the project simply as:

> DSE ETL Pipeline

Preferred project name:

> **DSE Market Intelligence Platform**

Potential final CV description:

> **DSE Market Intelligence Platform | Python, Airflow, dbt, PostgreSQL, S3, FastAPI, Docker, AWS**
>
> Designed and implemented an end-to-end financial data platform ingesting historical and daily Dhaka Stock Exchange market data and financial news. Built incremental and idempotent ingestion pipelines with automated retries, backfills, schema validation, and data-quality checks. Implemented a medallion-style architecture using S3/Parquet and PostgreSQL, developed dbt models for prices, returns, market statistics and technical indicators, and exposed analytical datasets through FastAPI for downstream analytics and ML applications. Added automated testing, CI/CD, observability, monitoring, and cloud deployment.

Only include technologies and metrics that are actually implemented.

---

# 38. Interview Preparation Through the Project

For every major technology, be able to answer:

### Architecture

- Why did you choose this architecture?
- Why S3?
- Why PostgreSQL?
- Why Parquet?
- Why dbt?
- Why Airflow?

### Reliability

- How do you handle duplicate data?
- How do you recover from a failed pipeline?
- How do you backfill two years?
- What happens when the source schema changes?
- How do you detect missing data?

### Data modeling

- What is the grain of your fact table?
- Why use a star schema?
- What belongs in a dimension?
- How would you handle historical company changes?

### Performance

- How would you optimize a slow query?
- What indexes do you use?
- When would you partition?
- What happens when the dataset becomes 500 GB?

### Distributed systems

- When would you introduce Spark?
- When would you introduce Kafka?
- Why not use them now?

### Production

- How do you monitor the pipeline?
- What metrics do you track?
- How do you alert on stale data?
- How do you deploy?
- How do you manage secrets?

The ability to answer these questions is one of the project's main outcomes.

---

# 39. Project Philosophy

The final system should demonstrate this progression:

```text
                 BEGINNER
                    │
                 Scraping
                    │
                    ▼
                  ETL
                    │
                    ▼
             Data Engineering
                    │
                    ▼
            Data Platform
                    │
                    ▼
          Production System
                    │
                    ▼
             Data Products
                    │
                    ▼
                 ML
                    │
                    ▼
                  AI
```

The project is successful if it demonstrates that progression clearly.

---

# 40. First Milestone

The immediate next objective is **not** ML, Kafka, Spark, Kubernetes, or AI.

The first milestone is:

```text
DSE historical market data
          ↓
Python ingestion
          ↓
Immutable raw storage
          ↓
PostgreSQL
          ↓
dbt
          ↓
Daily price analytical model
          ↓
FastAPI
```

Once this works reliably, we will incrementally add:

```text
Airflow
Data quality
Testing
Observability
CI/CD
Analytics
News
Dashboard
AWS
ML
AI
```

---

# 41. Working Rule Going Forward

When adding any new technology, ask:

1. What problem does it solve?
2. Why do we need it?
3. What alternatives exist?
4. What are the trade-offs?
5. Can we demonstrate it in the DSE project?
6. Can we explain the decision in an interview?

The goal is not:

> **"I used many technologies."**

The goal is:

> **"I can design and operate a reliable data platform, and I understand why every major architectural decision was made."**
