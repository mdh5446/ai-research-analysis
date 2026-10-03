# Data model

STEP 1 implements `stock_master` and `stock_daily`. STEP 2 adds `market_daily`
and `collection_snapshot`; existing table definitions remain unchanged.

`StockMaster`: integer primary key `id`; unique string `symbol` (preserves leading
zeros); `name`, `market`; UTC naive `created_at` and auto-updated `updated_at`.

`StockDaily`: integer primary key `id`; explicit `trade_date`; string `symbol`;
`open`, `high`, `low`, `close` as Numeric(20,4); BigInteger `volume`;
nullable Numeric(24,4) `trading_value`; UTC naive `created_at`.
Unique `(trade_date, symbol)` rejects duplicate inserts. No daily update/upsert helper.
Symbols do not require a master foreign key in STEP 1, allowing independent daily
persistence. Currency/units, adjustment policy, and source provenance need definition
before collection begins. Master data is mutable reference data, not a daily snapshot.

| Entity | Purpose | Status |
| --- | --- | --- |
| market_daily | Dated KOSPI/KOSDAQ OHLCV and trading value | Implemented |
| collection_snapshot | Dated original response rows and normalized collection | Implemented |
| stock_master | Symbol, name, market reference | Implemented |
| stock_daily | Dated stock OHLCV and trading value | Implemented |
| stock_investor_daily | Dated foreign/institutional/other investor flows | Planned |
| stock_financial | Period financial statements with publication/availability dates | Planned |
| stock_feature_daily | Deterministic stock metrics by trading date | Planned |
| sector_master | Sector reference and classification | Planned |
| sector_daily | Dated sector aggregates | Planned |
| news | Source, publication time, content reference, related entities | Planned |
| market_analysis_daily | Dated market regime and interpretation | Planned |
| sector_analysis_daily | Dated sector analysis and ranking | Planned |
| stock_analysis_daily | Dated stock facts and qualitative analysis | Planned |
| daily_candidate | Dated selected candidates and score/strategy version | Planned |
| candidate_performance | Candidate outcomes at 1/3/5/10/20 trading-day horizons | Planned |

Daily snapshots are append-oriented and identified by explicit date plus entity.
Historical snapshots must never be overwritten. Repository insert helpers enforce
this write convention; SQLAlchemy itself is not an immutable-record security layer.
Future corrections need an explicit revision/provenance policy before implementation.
Future idempotent runs should recognize existing identical snapshots and report conflicts.
Performance records should identify candidate, horizon, and observed trading date.
Financial/news availability dates must prevent future-data leakage in backtests.
`create_all` creates missing tables only; future schema changes require migrations.

## Additional planned persistence requirements

- Market/index observations need distinct identifiers for KOSPI and KOSDAQ in
  `market_daily`; STEP 2 implements this table.
- Disclosures need source identifiers, company links, publication/availability times,
  and content references; a future disclosure entity is planned, not implemented.
- News needs title, source, `published_at`, URL, related stocks/sectors, and a
  deduplication rule.
- AI-backed analyses need analysis date, model, prompt version, and practical input
  references. Snapshots retain evidence, reasons, risks, and scoring versions.
- Source/retrieval/availability provenance and price adjustment conventions require
  definition before ingestion. Historical membership/classifications must eventually
  support point-in-time review instead of relying only on mutable master data.
- Performance may include 20-session maximum return and maximum drawdown; definitions
  and observation completeness must be specified before implementation.

See [ROADMAP.md](ROADMAP.md) for scope and decisions before STEP 2. These requirements
do not change STEP 1's implemented schema.


## STEP 2 additive schema

`MarketDaily`: integer primary key, explicit `trade_date`, `index_code` (KOSPI/KOSDAQ),
Numeric(20,4) OHLC, BigInteger volume, nullable Numeric(24,4) trading value, UTC naive
creation time. Unique `(trade_date, index_code)`. No index records in stock tables.

`CollectionSnapshot`: integer primary key; unique `(trade_date, source)`;
UTC naive `retrieved_at`; JSON `raw` containing the six API row arrays; JSON
`normalized` containing validated stocks/daily/indices and normalization version.
Credentials and request headers are never persisted. Original source rows retain
identifiers and source details omitted from minimum normalized tables. Historical
master names/classifications remain available through dated normalized snapshots.
Retrieval time is known; actual source availability/publication time is not asserted.

Caller-owned transaction stores all four datasets and snapshot together. Identical
normalized reruns skip writes and retain the first raw response/retrieval time.
Changed normalized data or conflicting preexisting daily values raises a conflict;
transaction rolls back. Snapshot convention is append-oriented, not a database
immutability trigger. No records are deleted when absent from a new master response.
Older collections do not overwrite existing latest-master names/markets; they still
store dated master snapshots. Backfill range execution remains STEP 3.

Schema change adds tables only: `init_db.py` creates missing tables without altering
or replacing existing stock tables. No existing data migration is needed.
