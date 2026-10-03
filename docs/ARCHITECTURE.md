# Architecture

This is a deterministic batch pipeline, not initially a fully autonomous AI agent.
AI is used only in selected interpretation stages.

Planned flow:

Data Collection -> Normalization -> Persistence -> Feature Calculation ->
Market Analysis -> Sector Analysis -> Stock Candidate Filtering ->
AI Qualitative Analysis -> Scoring -> Daily Snapshot -> Performance Tracking ->
Streamlit Dashboard

| Module | Responsibility |
| --- | --- |
| config | Environment settings |
| collectors | Collect and normalize external data; Pydantic boundary validation |
| features | Deterministic quantitative calculations |
| scoring | Explicit versioned scoring rules, weights TBD |
| ai | Interpret facts, metrics, news, context; validate responses with Pydantic |
| analysis | Market, then sector, then stock research decisions |
| db | SQLAlchemy persistence and caller-owned transactions |
| pipeline | Explicit-date batch orchestration, eventually idempotent |
| utils | Shared utilities only when needed |
| dashboard | Local read-oriented Streamlit views |

STEP 1 implements only settings, two database tables, session/repository helpers,
initialization, persistence tests, and dashboard placeholder. No external calls.
Korean trading-date logic must use Asia/Seoul. Database audit timestamps use UTC;
trade dates are supplied explicitly and never inferred from audit timestamps.

## Product direction

The output is a reproducible research archive and watchlist, not blind trade
recommendations. Full scope and sequential implementation order live in
[ROADMAP.md](ROADMAP.md). STEP 2 adapter/persistence implemented; approved live verification pending.

Expanded research flow:

Raw Data -> Normalized Data -> Deterministic Features -> Market State -> Sector State
-> Stock Candidate Filtering -> News / Financial / Flow Context -> AI Interpretation
-> Scoring -> Daily Research Snapshot -> Future Performance Tracking
-> Historical Review / Backtesting

Persistence retains inputs and daily results across this flow. Streamlit provides
read-only historical review, including a date-based Calendar. AI outputs retain
analysis date, model, prompt version, and practical input references.


STEP 2 adds a source-specific KRX collector and Pydantic normalized records.
Collectors perform no persistence or quantitative feature calculation.
`scripts/collect_market.py` is a manual single-date entry point: fetch/validate all
six responses, then persist via repository in one transaction. `market_daily` stores
headline indices; `collection_snapshot` retains source rows and dated master facts.
No scheduled/daily orchestration or backfill loops are implemented.
See [DATA_SOURCES.md](DATA_SOURCES.md) for source choice and live-verification limits.
