# Planned daily pipeline

1. Collect market data.
2. Collect stock OHLCV.
3. Collect investor flow.
4. Collect financial data.
5. Collect disclosures.
6. Collect macro data.
7. Collect news.
8. Calculate deterministic features.
9. Analyze overall market regime.
10. Rank and analyze sectors.
11. Filter candidate stocks.
12. Analyze candidate stocks, with selected AI qualitative interpretation.
13. Calculate final scores.
14. Store daily research snapshot.
15. Update previous candidate performance.

Future manual entry point (not implemented):

```powershell
uv run python scripts/run_daily.py --date YYYY-MM-DD
```

Every daily stage receives an explicit trading/analysis date. Use Asia/Seoul and
an eventual exchange trading calendar; weekends alone cannot identify trading days.
Persist normalized inputs before downstream calculations. Validate external/AI
boundaries with Pydantic. Never ask AI to calculate quantitative features.

Daily snapshots are append-oriented. Future reruns must skip identical persisted
results or explicitly report conflicts without overwriting history. STEP 1 rejects
duplicate stock daily records; full pipeline idempotence is future work.
Track candidates after 1/3/5/10/20 trading sessions using exchange sessions, not
calendar-day offsets. Previously completed horizons remain historical records.

## Implementation versus execution

The stages above describe a future daily run; they are not implementation order.
Follow the 18 steps in [ROADMAP.md](ROADMAP.md), one requested step at a time.
Within a run, reduce the candidate universe before AI, attach news/financial/flow
context, interpret it with structured outputs, then calculate explainable scores.
All score formulas are Python. Archive reasons, risks, evidence, and AI provenance.
Historical review/backtesting follows performance tracking. Consider 20-session
maximum return and maximum drawdown in addition to fixed-horizon returns.


## STEP 2 manual collection

```powershell
uv run python scripts/collect_market.py --date YYYY-MM-DD
```

Requires approved `KRX_API_KEY` and all six source APIs. Past dates only, with
Asia/Seoul cutoff; no automatic date fallback. Empty responses fail explicitly;
they do not prove a holiday. Required date, symbol, OHLC, and volume values are
validated before DB writes. Master/daily universes must match per market. A timeout,
HTTP failure, invalid JSON/schema, or missing headline index prevents persistence.
No automatic retries; investigate publication/access, then rerun manually.
Identical normalized reruns skip storage, conflicting historical values roll back.
This command is collection only; `run_daily.py` and later stages remain unimplemented.
