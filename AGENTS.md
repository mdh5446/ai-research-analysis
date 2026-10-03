# Response Style

Terse like caveman. Technical substance exact. Only fluff die.

- Drop articles, filler, pleasantries, hedging.
- Fragments OK.
- Short synonyms.
- Code unchanged.
- Prefer tables/bullets over prose.
- No repeated explanations.
- No restating user request.
- Code/commits/PRs: normal.
- ACTIVE EVERY RESPONSE.

# Token Efficiency

- Do not summarize work unless asked.
- Do not explain obvious code.
- Do not repeat unchanged code.
- Show only changed sections unless full file requested.
- Avoid preambles and conclusions.
- Do not describe tool calls.
- Prefer direct edits over explanations.
- When error found: cause -> fix -> code.
- Keep progress updates minimal.
- Read only files needed for the current task; use targeted searches before broad reads.
- Do not re-read unchanged files unless needed to resolve uncertainty.
- Do not reproduce entire files unless explicitly requested; show only relevant changes.

# Development Rules

1. Collectors only collect and normalize external data.
2. Feature calculations must be deterministic Python code.
3. Never ask an LLM to calculate RSI, moving averages, returns, trading volume ratios,
   investor flow totals, or relative strength.
4. AI only interprets already collected facts, metrics, news, and context.
5. Separate collectors, features, scoring, ai, analysis, db, pipeline, and dashboard.
6. All daily data must use an explicit analysis/trading date.
7. Historical daily snapshots must never be overwritten.
8. Pipeline execution must eventually be idempotent.
9. Prefer simple code over complex architecture.
10. Use Python type hints.
11. Use Pydantic models for external/AI data boundaries.
12. Use SQLAlchemy for persistence.
13. Use Asia/Seoul for Korean market date logic.
14. Add tests for deterministic calculations and persistence.
15. Read relevant docs/ files before changing architecture, DB schema, pipeline, or scoring.
