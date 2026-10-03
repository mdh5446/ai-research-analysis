# Stock Research

Local AI-assisted Korean stock market research, with historical snapshots and future
1/3/5/10/20 trading-day candidate performance tracking. Deterministic Python metrics;
AI interprets collected facts only. STEP 1 provides configuration, SQLite persistence,
documentation, tests, and a Streamlit placeholder.

## Setup and commands

Install Python 3.14 and uv. Run commands from the repository root:

```powershell
uv sync
Copy-Item .env.example .env
uv run python scripts/init_db.py
uv run pytest
uv run ruff check .
uv run streamlit run dashboard/app.py
```

`.env` is optional. Environment variables override `.env`.
`DATABASE_URL` defaults to `sqlite:///./data/stock_research.db`; relative paths resolve
from the working directory. Initialization creates parent directories and missing
tables and is safe to repeat. It is not a schema migration command.
Never commit secrets or local databases.

See [architecture](docs/ARCHITECTURE.md), [data model](docs/DATA_MODEL.md),
[pipeline](docs/PIPELINE.md), and [scoring](docs/SCORING.md).
KRX collection is implemented; authenticated live verification remains pending.
OpenAI calls, crawling, feature calculations, scoring, and daily orchestration are future work. Existing `ai_research_analysis` scaffold remains for compatibility.


## Roadmap and current boundary

[Product roadmap](docs/ROADMAP.md) records the full direction and 18-step sequence.
STEP 1 is complete. STEP 2 uses KRX OPEN API for stock master, daily OHLCV, KOSPI,
and KOSDAQ; approved live verification is pending. STEP 3 is historical backfill. Implement one explicitly requested phase, verify it, then stop.
The goal is reproducible daily research and later historical evaluation, with a
read-only Streamlit Calendar for past snapshots. Optional reports come later.


## KRX single-date collection (STEP 2)

Read [source comparison and access requirements](docs/DATA_SOURCES.md). Register
with KRX Data Marketplace, obtain an approved key, and obtain separate approval for
both stock basic APIs, both daily stock APIs, and both index series APIs.
Set `KRX_API_KEY` in local `.env`; never commit or share the key.

```powershell
uv run python scripts/init_db.py
uv run python scripts/collect_market.py --date 2026-09-30
```

Use a published historical trading date (2010-01-04 onward). Same-day/future dates
are disabled to avoid treating partial data as final. Empty responses are failures,
not automatic holiday detection. There is no exchange-calendar inference yet.
The command stores validated data plus original response rows in SQLite atomically.
Identical reruns retain originals; conflicts fail without overwriting history.
All API tests are offline synthetic fixtures. No production key/live collection has
been verified yet. STEP 2 adds tables without modifying existing stock tables.
