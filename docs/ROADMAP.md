# Product roadmap

## Purpose and boundaries

Build a local daily Korean stock market research archive that reproduces what the
system believed on each historical trading date. Identify improving sectors and
stocks with early momentum, supporting evidence, and overheating risks. This is a
research watchlist, not a system for blindly recommending trades.

Quantitative facts and score formulas are deterministic Python. AI interprets
market conditions, related news, meaningful catalysts, earnings, risks, sector
alignment, and early/mature/overheated momentum using already calculated facts.
Use structured outputs; retain analysis date, model, prompt version, and practical
input references. All scoring weights remain TBD until explicitly authorized.

## Implementation order

These implementation steps are distinct from stages within a daily run.
STEP 1 is complete. STEP 2 adapter and persistence are implemented with synthetic
tests; authenticated live verification awaits an approved KRX key. STEP 3 onward
remains planned, not authorized by this document. Implement only the requested step, verify it, then stop.

| Step | Scope |
| --- | --- |
| 1 | Project foundation and database setup - completed |
| 2 | KRX OPEN API stock master, daily OHLCV, KOSPI/KOSDAQ - implemented; live verification pending |
| 3 | Historical collection and backfill |
| 4 | Deterministic technical features |
| 5 | Foreign and institutional investor flow |
| 6 | Sector/industry classification and dated sector aggregation |
| 7 | Financial statements |
| 8 | Disclosures |
| 9 | News collection and deduplication |
| 10 | Market regime logic |
| 11 | Sector ranking and sector stage detection |
| 12 | Stock candidate filtering |
| 13 | Explainable Early Momentum scoring; weights require explicit instruction |
| 14 | OpenAI structured qualitative analysis |
| 15 | Daily batch orchestration |
| 16 | Candidate future performance |
| 17 | Streamlit research dashboard |
| 18 | Historical evaluation and backtesting improvements |

Technical dependencies may justify an adjustment; document the reason without
using it to implement unrequested phases. Optional PDF/static exports follow a
stable historical pipeline and are not a current priority.

## Planned collection and analysis coverage

- Market context: KOSPI/KOSDAQ, breadth, trading value, foreign/institutional flow,
  USD/KRW, major US indices, US semiconductor markets, rates, useful macro indicators.
- Stocks: OHLCV, trading value, market capitalization, listing information, market,
  and sector/industry when available. STEP 2 starts with the narrower scope above.
- Flows: foreign/institutional daily net buying; program trading only with reliable data.
- Financials: revenue, operating/net profit, quarterly/annual results, Python-derived
  YoY growth; surprises, consensus, and estimate revisions when reliable sources exist.
- Disclosures: earnings, contracts, capex, new business, buybacks, ownership changes,
  M&A, and financing.
- News: market/sector/stock articles; title, source, publication time, URL, related
  stock, and sector when known. Deduplicate articles.
- Features: 1/3/5/20/60-session returns; MA5/20/60/120 and distances; RSI14;
  volume/trading-value expansion; 52-week high distance; 1/5/20-session investor
  flow sums; sector relative strength and stock strength versus sector.
- Market state: risk-on/neutral/risk-off concepts, liquidity, investor flows,
  breadth, dominant themes, and risks. Definitions remain future work.
- Sector state: strength across short/medium horizons, activity, rising-stock counts,
  flows, earnings, news quantity/quality, macro/policy catalysts. Possible stages:
  emerging, early uptrend, strengthening, mature, overheated, weakening. Detect
  improving conditions, not merely today's strongest sector.
- Candidate filtering: liquidity, capitalization, price/activity, flows, earnings,
  sector alignment, technical position, and excessive gains/MA extension. Reduce
  the universe before AI analysis.
- Daily watchlist: market summary, emerging/leading sectors, scores, selected stocks,
  Early Momentum scores, supporting reasons/news, and risks. Roughly 3-5 sectors
  and 5-15 stocks are illustrative, not acceptance requirements.
- Performance: 1/3/5/10/20-session returns; consider maximum return and maximum
  drawdown within 20 sessions. Define calculation conventions before implementation.
- Dashboard: Today, Calendar, Sectors, Stocks, Historical Performance. Calendar must
  expose a selected historical date's market state, sectors, stocks, scores, news,
  reasons, and subsequent performance. Primarily read-only.

## Phase workflow

Before each implementation phase: read AGENTS.md and relevant docs, inspect existing
code, preserve working code, keep scope within the requested phase, add relevant
tests, run pytest and Ruff, update affected architecture/schema documentation,
then stop. Documentation-only changes need no new implementation tests.

## Decisions before STEP 2

KRX OPEN API selected; see [DATA_SOURCES.md](DATA_SOURCES.md) for comparison,
conditions, and verification limits. Confirm approved live access and contract compatibility. Keep source-specific
collection and normalization separate from database transactions.

Define symbol/index identifiers, universe coverage (including delisted stocks for
later backtests), units/currency, adjusted versus unadjusted prices, and corporate
action handling. Preserve source provenance, retrieval time, and availability time
where applicable. Distinguish missing values, suspension, holidays, and genuine zeros.

Use explicit Asia/Seoul trading dates and exchange sessions. Define behavior for
incomplete same-day data and source failures. Validate normalized external records
with Pydantic and test with fixtures rather than live network dependencies.

Existing stock tables cannot store KOSPI/KOSDAQ index snapshots as stock records.
STEP 2 adds dated market/index and collection snapshots. Identical normalized
reruns skip writes; conflicts roll back without overwriting history. `create_all` does not
migrate existing tables. Mutable stock master alone cannot reconstruct historical
membership/classifications: later historical work needs point-in-time handling.
