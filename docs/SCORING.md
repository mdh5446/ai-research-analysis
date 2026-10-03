# Preliminary scoring concept

Concept only: no final strategy or scoring calculations implemented.
All weights, thresholds, normalization rules, and penalties are TBD.

| Scope | Possible category | Weight |
| --- | --- | --- |
| Sector | Relative strength | TBD |
| Sector | Trading value trend | TBD |
| Sector | Investor flow | TBD |
| Sector | Earnings trend | TBD |
| Sector | News/catalyst strength | TBD |
| Sector | Overheating penalty | TBD |
| Stock | Sector alignment | TBD |
| Stock | Price momentum | TBD |
| Stock | Volume/trading value expansion | TBD |
| Stock | Foreign investor flow | TBD |
| Stock | Institutional flow | TBD |
| Stock | Earnings momentum | TBD |
| Stock | News catalyst | TBD |
| Stock | Overheating penalty | TBD |

Early Momentum Score aims to prefer stocks beginning to strengthen, especially
within strengthening sectors, rather than stocks with extreme short-term gains.
Its inputs, weights, thresholds, and overheating definition are TBD; evaluate them
against historical data before adoption. Quantitative inputs must be deterministic
Python calculations. AI may interpret catalysts but must not calculate metrics.
Future stored scores should retain strategy versions and input dates for reproducibility.

## Early Momentum signals under consideration

Positive concepts: recovery above important moving averages, increasing trading value,
improving foreign/institutional buying, improving sector strength and earnings
expectations, emerging catalysts, and developing breakout structure.

Penalty concepts: extreme recent gains, high RSI, excessive MA20/MA60 distance,
parabolic moves, and deteriorating investor flow. Definitions and weights remain TBD;
do not finalize them without explicit instruction. Keep formulas explainable and
implemented in Python. AI interprets context and momentum stage, not score arithmetic.

Sector stage detection (STEP 11), candidate filtering (STEP 12), Early Momentum
scoring (STEP 13), and AI interpretation (STEP 14) are separate implementation steps.
See [ROADMAP.md](ROADMAP.md).
