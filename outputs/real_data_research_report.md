# Phase 2A — Real Historical Data Validation

## Acceptance decision

**No strategy run passed every acceptance gate. Live integration is not recommended.**

The acceptance decision uses out-of-sample results only. Positive-looking synthetic results are not considered evidence.

## Data and separation from synthetic validation

- Synthetic validation remains in `outputs/research_report.md` and was not overwritten.
- Real adjusted daily OHLCV: 2023-09-01 00:00:00 through 2026-09-04 00:00:00, Yahoo Finance via yfinance, cached under `data/real/raw/yahoo/`.
- Limited 15-minute adjusted OHLCV check: 2026-06-11 09:30:00-04:00 through 2026-09-04 15:45:00-04:00; this short slice is not the main acceptance evidence.
- Historical event rows applied: 806, from `data/real/events/historical_events.csv`.
- Signals use closed candles and execute at the next candle open with commission, spread, slippage, and short-borrow placeholders.
- Fill prices are clamped to the candle high/low. Ambiguous stop/target candles resolve adverse-first.

## Pair-discovery diagnostics

| Relationship | Corr 60 | Half-life | Crossings/yr | Kill failure | Verdict |
| --- | --- | --- | --- | --- | --- |
| CSCO/XLK | 0.45 | 7.6 | 18.3 | 9.09% | REVIEW: mixed evidence; continue only with conservative validation |
| CSCO/QQQ | 0.41 | 7.9 | 17.1 | 7.32% | REVIEW: mixed evidence; continue only with conservative validation |
| VZ/XLC | 0.31 | 14.4 | 13.3 | 15.62% | REVIEW: mixed evidence; continue only with conservative validation |
| MO/XLP | 0.67 | 13.3 | 14.6 | 20.00% | GO: relationship shows testable mean-reversion structure |
| XOM/XLE | 0.88 | 13.2 | 16.2 | 28.21% | GO: relationship shows testable mean-reversion structure |
| JPM/XLF | 0.71 | 5.9 | 17.5 | 16.67% | GO: relationship shows testable mean-reversion structure |
| PFE/XLV | 0.60 | 9.7 | 15.4 | 18.92% | GO: relationship shows testable mean-reversion structure |
| VZ/T | 0.91 | 7.3 | 13.3 | 12.50% | GO: relationship shows testable mean-reversion structure |
| KO/PEP | 0.64 | 11.8 | 15.4 | 21.62% | GO: relationship shows testable mean-reversion structure |
| XOM/CVX | 0.84 | 13.0 | 15.4 | 13.51% | GO: relationship shows testable mean-reversion structure |
| JPM/BAC | 0.85 | 7.4 | 11.2 | 18.52% | GO: relationship shows testable mean-reversion structure |
| MA/V | 0.88 | 9.2 | 12.1 | 13.79% | GO: relationship shows testable mean-reversion structure |

## In-sample/full-period descriptive results

These full-period figures are descriptive and are not the acceptance result.

| Run | Return | Ann. | Max DD | PF | Win | Expectancy | Avg hold h | Trades | Exposure | Max gross | Max |β| | Stock B&H | ETF/pair B&H |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| residual_grid:CSCO/XLK | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | 104.35% | 116.83% |
| residual_grid:CSCO/QQQ | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | 104.35% | 93.73% |
| residual_grid:VZ/XLC | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | 75.90% | 72.70% |
| residual_grid:MO/XLP | 0.26% | 0.08% | -0.26% | 3.11 | 50.00% | $127.64 | 96.0 | 2 | 0.79% | 0.46 | 0.06 | 96.26% | 27.20% |
| residual_grid:XOM/XLE | -2.54% | -0.85% | -3.78% | 0.30 | 23.81% | $-120.81 | 122.3 | 21 | 9.67% | 1.59 | 0.03 | 55.03% | 55.44% |
| residual_grid:JPM/XLF | 2.13% | 0.70% | -0.82% | 2.49 | 61.11% | $118.53 | 137.3 | 18 | 9.27% | 1.35 | 0.11 | 160.94% | 75.62% |
| residual_grid:PFE/XLV | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | -3.57% | 34.98% |
| stock_pair_grid:VZ/T | 0.14% | 0.05% | -0.13% | ∞ | 100.00% | $138.93 | 168.0 | 1 | 0.53% | 0.54 | 0.02 | 75.90% | 105.33% |
| stock_pair_grid:KO/PEP | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | 62.20% | -12.52% |
| stock_pair_grid:XOM/CVX | -0.52% | -0.17% | -0.68% | 0.48 | 55.56% | $-58.24 | 61.3 | 9 | 2.65% | 0.94 | 0.02 | 55.03% | 43.93% |
| stock_pair_grid:JPM/BAC | 0.44% | 0.15% | -0.99% | 1.30 | 62.50% | $55.34 | 120.0 | 8 | 3.71% | 1.20 | 0.04 | 160.94% | 132.41% |
| stock_pair_grid:MA/V | 0.55% | 0.18% | -0.54% | 2.46 | 44.44% | $61.41 | 93.3 | 9 | 2.78% | 0.97 | 0.03 | 41.89% | 54.66% |
| natural_long_grid:CSCO | 1.36% | 0.45% | -1.47% | 14.24 | 75.00% | $169.96 | 528.0 | 8 | 16.29% | 0.37 | 0.19 | 104.35% | n/a |
| natural_long_grid:VZ | 0.38% | 0.13% | -1.23% | 1.30 | 77.78% | $42.14 | 597.3 | 9 | 19.60% | 0.35 | 0.08 | 75.90% | n/a |
| natural_long_grid:T | -0.71% | -0.24% | -0.81% | 0.18 | 33.33% | $-238.27 | 240.0 | 3 | 2.65% | 0.27 | 0.28 | 105.33% | n/a |
| natural_long_grid:MO | 1.97% | 0.65% | -0.40% | 9.85 | 66.67% | $655.41 | 336.0 | 3 | 4.11% | 0.19 | 0.34 | 96.26% | n/a |
| natural_long_grid:KO | 0.71% | 0.24% | -1.46% | 1.74 | 66.67% | $118.34 | 408.0 | 6 | 9.40% | 0.38 | 0.26 | 62.20% | n/a |
| natural_long_grid:PEP | -4.20% | -1.42% | -5.51% | 0.13 | 22.22% | $-466.70 | 466.7 | 9 | 16.16% | 0.46 | 0.30 | -12.52% | n/a |
| natural_long_grid:XOM | 1.49% | 0.49% | -1.42% | 2.47 | 80.00% | $148.50 | 556.8 | 10 | 20.40% | 0.37 | 0.33 | 55.03% | n/a |
| natural_long_grid:CVX | 1.65% | 0.55% | -1.50% | 2.11 | 75.00% | $206.37 | 495.0 | 8 | 14.70% | 0.24 | 0.12 | 43.93% | n/a |
| natural_long_grid:JPM | 1.37% | 0.45% | -0.80% | ∞ | 100.00% | $455.91 | 672.0 | 3 | 7.68% | 0.38 | 0.87 | 160.94% | n/a |
| natural_long_grid:BAC | -2.54% | -0.85% | -2.89% | 0.00 | 0.00% | $-845.27 | 320.0 | 3 | 3.97% | 0.24 | 0.31 | 132.41% | n/a |
| natural_long_grid:MA | -0.85% | -0.28% | -2.51% | 0.65 | 45.45% | $-77.16 | 412.4 | 11 | 17.35% | 0.25 | 0.31 | 41.89% | n/a |
| natural_long_grid:V | 0.80% | 0.26% | -1.28% | 1.35 | 60.00% | $79.73 | 487.2 | 10 | 18.28% | 0.31 | 0.15 | 54.66% | n/a |
| natural_long_grid:PFE | -5.13% | -1.73% | -5.81% | 0.32 | 58.33% | $-427.47 | 474.0 | 12 | 21.59% | 0.48 | 0.11 | -3.57% | n/a |

## Out-of-sample 6-month / 1-month walk-forward results — main result

The first OOS month begins 2024-03-01. Parameters were fixed before this run. Each one-month bucket uses only information available at that time; the preceding six months serve as calibration/warm-up. Campaigns are not optimized on the combined period.

| Run | Return | Ann. | Max DD | PF | Win | Expectancy | Avg hold h | Trades | Exposure | Max gross | Max |β| | Stock B&H | ETF/pair B&H |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| residual_grid:CSCO/XLK | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | 140.58% | 80.49% |
| residual_grid:CSCO/QQQ | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | 140.58% | 63.51% |
| residual_grid:VZ/XLC | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | 46.87% | 44.10% |
| residual_grid:MO/XLP | 0.26% | 0.10% | -0.26% | 3.11 | 50.00% | $127.64 | 96.0 | 2 | 0.95% | 0.46 | 0.06 | 102.45% | 21.49% |
| residual_grid:XOM/XLE | -2.54% | -1.02% | -3.78% | 0.30 | 23.81% | $-120.81 | 122.3 | 21 | 11.57% | 1.59 | 0.03 | 63.25% | 59.14% |
| residual_grid:JPM/XLF | 2.13% | 0.84% | -0.82% | 2.49 | 61.11% | $118.53 | 137.3 | 18 | 11.09% | 1.35 | 0.11 | 103.99% | 49.79% |
| residual_grid:PFE/XLV | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | 26.14% | 22.15% |
| stock_pair_grid:VZ/T | 0.14% | 0.06% | -0.13% | ∞ | 100.00% | $138.93 | 168.0 | 1 | 0.63% | 0.54 | 0.02 | 46.87% | 71.05% |
| stock_pair_grid:KO/PEP | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | 59.06% | -8.22% |
| stock_pair_grid:XOM/CVX | -0.52% | -0.21% | -0.68% | 0.48 | 55.56% | $-58.24 | 61.3 | 9 | 3.17% | 0.94 | 0.02 | 63.25% | 51.50% |
| stock_pair_grid:JPM/BAC | 0.44% | 0.18% | -0.99% | 1.30 | 62.50% | $55.34 | 120.0 | 8 | 4.44% | 1.20 | 0.04 | 103.99% | 93.16% |
| stock_pair_grid:MA/V | 0.55% | 0.22% | -0.54% | 2.46 | 44.44% | $61.41 | 93.3 | 9 | 3.33% | 0.97 | 0.03 | 23.34% | 34.97% |
| natural_long_grid:CSCO | 1.36% | 0.54% | -1.47% | 14.24 | 75.00% | $169.96 | 528.0 | 8 | 19.49% | 0.37 | 0.19 | 140.58% | n/a |
| natural_long_grid:VZ | 0.38% | 0.15% | -1.23% | 1.30 | 77.78% | $42.14 | 597.3 | 9 | 23.45% | 0.35 | 0.08 | 46.87% | n/a |
| natural_long_grid:T | -0.71% | -0.29% | -0.81% | 0.18 | 33.33% | $-238.27 | 240.0 | 3 | 3.17% | 0.27 | 0.28 | 71.05% | n/a |
| natural_long_grid:MO | 1.06% | 0.42% | -0.40% | 5.76 | 66.67% | $352.39 | 216.0 | 3 | 3.17% | 0.19 | 0.34 | 102.45% | n/a |
| natural_long_grid:KO | 0.71% | 0.28% | -1.46% | 1.74 | 66.67% | $118.34 | 408.0 | 6 | 11.25% | 0.38 | 0.26 | 59.06% | n/a |
| natural_long_grid:PEP | -1.77% | -0.71% | -5.44% | 0.64 | 22.22% | $-196.25 | 464.0 | 9 | 19.02% | 0.45 | 0.29 | -8.22% | n/a |
| natural_long_grid:XOM | 0.56% | 0.22% | -0.99% | 1.55 | 75.00% | $70.12 | 552.0 | 8 | 19.33% | 0.21 | 0.16 | 63.25% | n/a |
| natural_long_grid:CVX | 1.35% | 0.54% | -1.50% | 1.91 | 71.43% | $193.37 | 545.1 | 7 | 16.96% | 0.24 | 0.12 | 51.50% | n/a |
| natural_long_grid:JPM | 1.37% | 0.54% | -0.80% | ∞ | 100.00% | $455.91 | 672.0 | 3 | 9.19% | 0.38 | 0.87 | 103.99% | n/a |
| natural_long_grid:BAC | -2.54% | -1.02% | -2.89% | 0.00 | 0.00% | $-845.27 | 320.0 | 3 | 4.75% | 0.24 | 0.31 | 93.16% | n/a |
| natural_long_grid:MA | -0.85% | -0.34% | -2.51% | 0.65 | 45.45% | $-77.16 | 412.4 | 11 | 20.76% | 0.25 | 0.31 | 23.34% | n/a |
| natural_long_grid:V | 0.80% | 0.32% | -1.28% | 1.35 | 60.00% | $79.73 | 487.2 | 10 | 21.87% | 0.31 | 0.15 | 34.97% | n/a |
| natural_long_grid:PFE | -4.72% | -1.91% | -5.80% | 0.32 | 63.64% | $-428.85 | 497.5 | 11 | 24.72% | 0.48 | 0.11 | 26.14% | n/a |

Monthly bucket details are in `outputs/real_data_walk_forward_monthly.csv`.

## MAE/MFE and regime attribution

| Run | Avg MAE | Avg MFE | Worst MAE R | Best MFE R | Regime trades / P&L |
| --- | --- | --- | --- | --- | --- |
| residual_grid:CSCO/XLK | $0.00 | $0.00 | n/a | n/a |  |
| residual_grid:CSCO/QQQ | $0.00 | $0.00 | n/a | n/a |  |
| residual_grid:VZ/XLC | $0.00 | $0.00 | n/a | n/a |  |
| residual_grid:MO/XLP | $-131.31 | $164.39 | -0.14 | 0.44 | range: 1 / $376; warning: 1 / $-121; breakout: 0 / $0; failed_breakout: 0 / $0 |
| residual_grid:XOM/XLE | $-185.38 | $46.25 | -1.09 | 0.46 | range: 12 / $-272; warning: 5 / $-2,074; breakout: 4 / $-191; failed_breakout: 0 / $0 |
| residual_grid:JPM/XLF | $-119.49 | $259.34 | -0.49 | 0.83 | range: 12 / $2,383; warning: 4 / $262; breakout: 2 / $-511; failed_breakout: 0 / $0 |
| residual_grid:PFE/XLV | $0.00 | $0.00 | n/a | n/a |  |
| stock_pair_grid:VZ/T | $-129.02 | $264.15 | -0.13 | 0.26 | range: 1 / $139; warning: 0 / $0; breakout: 0 / $0; failed_breakout: 0 / $0 |
| stock_pair_grid:KO/PEP | $0.00 | $0.00 | n/a | n/a |  |
| stock_pair_grid:XOM/CVX | $-92.28 | $50.40 | -0.61 | 0.25 | range: 2 / $-882; warning: 3 / $-79; breakout: 4 / $436; failed_breakout: 0 / $0 |
| stock_pair_grid:JPM/BAC | $-185.98 | $266.74 | -0.91 | 1.16 | range: 1 / $1,137; warning: 1 / $-5; breakout: 6 / $-689; failed_breakout: 0 / $0 |
| stock_pair_grid:MA/V | $-99.55 | $97.05 | -0.26 | 0.42 | range: 2 / $754; warning: 7 / $-201; breakout: 0 / $0; failed_breakout: 0 / $0 |
| natural_long_grid:CSCO | $-147.77 | $314.23 | -0.75 | 0.74 | range: 5 / $752; warning: 3 / $608; breakout: 0 / $0; failed_breakout: 0 / $0 |
| natural_long_grid:VZ | $-201.24 | $293.05 | -1.02 | 0.76 | range: 6 / $1,173; warning: 3 / $-794; breakout: 0 / $0; failed_breakout: 0 / $0 |
| natural_long_grid:T | $-283.23 | $45.45 | -0.76 | 0.17 | range: 0 / $0; warning: 3 / $-715; breakout: 0 / $0; failed_breakout: 0 / $0 |
| natural_long_grid:MO | $-26.46 | $530.29 | -0.22 | 1.29 | range: 2 / $1,279; warning: 1 / $-222; breakout: 0 / $0; failed_breakout: 0 / $0 |
| natural_long_grid:KO | $-256.43 | $399.99 | -0.94 | 1.05 | range: 3 / $-410; warning: 3 / $1,120; breakout: 0 / $0; failed_breakout: 0 / $0 |
| natural_long_grid:PEP | $-598.68 | $477.54 | -2.02 | 2.86 | range: 2 / $3,110; warning: 7 / $-4,876; breakout: 0 / $0; failed_breakout: 0 / $0 |
| natural_long_grid:XOM | $-202.76 | $317.36 | -0.71 | 0.84 | range: 6 / $1,040; warning: 2 / $-479; breakout: 0 / $0; failed_breakout: 0 / $0 |
| natural_long_grid:CVX | $-273.29 | $510.16 | -1.37 | 1.46 | range: 5 / $2,609; warning: 2 / $-1,255; breakout: 0 / $0; failed_breakout: 0 / $0 |
| natural_long_grid:JPM | $-205.71 | $564.17 | -0.49 | 0.88 | range: 3 / $1,368; warning: 0 / $0; breakout: 0 / $0; failed_breakout: 0 / $0 |
| natural_long_grid:BAC | $-888.41 | $173.12 | -1.21 | 0.25 | range: 0 / $0; warning: 3 / $-2,536; breakout: 0 / $0; failed_breakout: 0 / $0 |
| natural_long_grid:MA | $-309.70 | $181.85 | -0.92 | 0.86 | range: 5 / $887; warning: 6 / $-1,736; breakout: 0 / $0; failed_breakout: 0 / $0 |
| natural_long_grid:V | $-258.87 | $424.49 | -1.05 | 1.21 | range: 4 / $2,311; warning: 5 / $-1,748; breakout: 1 / $235; failed_breakout: 0 / $0 |
| natural_long_grid:PFE | $-722.74 | $279.24 | -4.80 | 1.11 | range: 5 / $1,600; warning: 6 / $-6,317; breakout: 0 / $0; failed_breakout: 0 / $0 |

## Limited 15-minute execution check

Yahoo-backed intraday history is limited to roughly 60 days. These results test candle-level mechanics and filters but cannot satisfy the requested 6m/1m walk-forward design.

| Run | Return | Ann. | Max DD | PF | Win | Expectancy | Avg hold h | Trades | Exposure | Max gross | Max |β| | Stock B&H | ETF/pair B&H |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| residual_grid:CSCO/XLK | -0.19% | -0.80% | -0.22% | 0.00 | 0.00% | $-187.81 | 1.2 | 1 | 1.67% | 0.56 | 0.17 | n/a | n/a |
| residual_grid:CSCO/QQQ | -1.08% | -4.55% | -1.19% | 0.00 | 0.00% | $-1,076.87 | 23.0 | 1 | 3.33% | 0.99 | 0.34 | n/a | n/a |
| residual_grid:VZ/XLC | 0.09% | 0.39% | -0.01% | ∞ | 100.00% | $90.76 | 0.2 | 1 | 1.67% | 0.21 | 0.01 | n/a | n/a |
| residual_grid:MO/XLP | -0.34% | -1.44% | -0.69% | 0.55 | 33.33% | $-56.01 | 17.0 | 6 | 10.00% | 2.44 | 0.64 | n/a | n/a |
| residual_grid:XOM/XLE | -4.50% | -17.97% | -4.58% | 0.11 | 20.83% | $-187.68 | 14.2 | 24 | 33.33% | 3.37 | 0.41 | n/a | n/a |
| residual_grid:JPM/XLF | -2.64% | -10.86% | -2.90% | 0.17 | 27.27% | $-239.88 | 25.3 | 11 | 16.67% | 4.49 | 0.72 | n/a | n/a |
| residual_grid:PFE/XLV | -1.54% | -6.44% | -1.94% | 0.34 | 33.33% | $-170.67 | 11.3 | 9 | 18.33% | 2.94 | 1.04 | n/a | n/a |
| stock_pair_grid:VZ/T | 0.43% | 1.84% | -0.40% | 2.05 | 40.00% | $85.12 | 4.3 | 5 | 3.33% | 2.20 | 0.03 | n/a | n/a |
| stock_pair_grid:KO/PEP | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | n/a | n/a |
| stock_pair_grid:XOM/CVX | -0.13% | -0.58% | -0.28% | 0.11 | 50.00% | $-67.48 | 10.9 | 2 | 3.33% | 0.85 | 0.02 | n/a | n/a |
| stock_pair_grid:JPM/BAC | -0.76% | -3.21% | -1.80% | 0.33 | 50.00% | $-94.54 | 18.3 | 8 | 10.00% | 4.29 | 0.51 | n/a | n/a |
| stock_pair_grid:MA/V | -0.92% | -3.91% | -1.39% | 0.47 | 33.33% | $-102.61 | 7.7 | 9 | 11.67% | 4.69 | 0.50 | n/a | n/a |
| natural_long_grid:CSCO | 0.08% | 0.33% | -0.15% | ∞ | 100.00% | $76.43 | 1.0 | 1 | 1.67% | 0.16 | 0.17 | n/a | n/a |
| natural_long_grid:VZ | 0.37% | 1.60% | -0.14% | ∞ | 100.00% | $368.99 | 192.8 | 1 | 10.00% | 0.10 | 0.23 | n/a | n/a |
| natural_long_grid:T | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | n/a | n/a |
| natural_long_grid:MO | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | n/a | n/a |
| natural_long_grid:KO | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | n/a | n/a |
| natural_long_grid:PEP | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | n/a | n/a |
| natural_long_grid:XOM | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | n/a | n/a |
| natural_long_grid:CVX | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | n/a | n/a |
| natural_long_grid:JPM | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | n/a | n/a |
| natural_long_grid:BAC | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | n/a | n/a |
| natural_long_grid:MA | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | n/a | n/a |
| natural_long_grid:V | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | n/a | n/a |
| natural_long_grid:PFE | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | $0.00 | 0.0 | 0 | 0.00% | 0.00 | 0.00 | n/a | n/a |

## Sensitivity analysis

One-at-a-time sweeps were run on the strongest default OOS member of each family: residual_grid:JPM/XLF, stock_pair_grid:MA/V, natural_long_grid:CSCO. This covers every requested parameter value without selecting a full-period optimum. The full table is `outputs/real_data_sensitivity.csv`.

| Run | Dimension | Variants | Viable | Worst return | Best return |
| --- | --- | --- | --- | --- | --- |
| natural_long_grid:CSCO | atr_stop_multiplier | 3 | 100.00% | 1.22% | 1.53% |
| natural_long_grid:CSCO | breakout_confirmation | 3 | 100.00% | 1.36% | 1.36% |
| natural_long_grid:CSCO | grid_levels | 3 | 100.00% | 1.34% | 1.36% |
| residual_grid:JPM/XLF | beta_window | 3 | 100.00% | 1.28% | 2.13% |
| residual_grid:JPM/XLF | breakout_confirmation | 3 | 100.00% | 0.93% | 2.13% |
| residual_grid:JPM/XLF | correlation_threshold | 3 | 100.00% | 0.25% | 2.13% |
| residual_grid:JPM/XLF | grid_levels | 3 | 100.00% | 2.97% | 4.53% |
| residual_grid:JPM/XLF | z_entry | 4 | 75.00% | -0.13% | 2.13% |
| residual_grid:JPM/XLF | z_exit | 4 | 100.00% | 2.11% | 2.17% |
| residual_grid:JPM/XLF | z_kill | 3 | 100.00% | 1.40% | 2.34% |
| stock_pair_grid:MA/V | beta_window | 3 | 100.00% | 0.19% | 0.88% |
| stock_pair_grid:MA/V | breakout_confirmation | 3 | 66.67% | -0.25% | 0.55% |
| stock_pair_grid:MA/V | correlation_threshold | 3 | 100.00% | 0.15% | 0.91% |
| stock_pair_grid:MA/V | grid_levels | 3 | 66.67% | -0.12% | 0.49% |
| stock_pair_grid:MA/V | z_entry | 4 | 50.00% | -0.25% | 0.55% |
| stock_pair_grid:MA/V | z_exit | 4 | 100.00% | 0.55% | 0.55% |
| stock_pair_grid:MA/V | z_kill | 3 | 66.67% | -0.39% | 0.55% |

## Acceptance gates by strategy

| Run | Decision | Failed conditions |
| --- | --- | --- |
| residual_grid:CSCO/XLK | FAIL | positive OOS expectancy; profit factor > 1.15; drawdown acceptable relative to return; at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| residual_grid:CSCO/QQQ | FAIL | positive OOS expectancy; profit factor > 1.15; drawdown acceptable relative to return; at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| residual_grid:VZ/XLC | FAIL | positive OOS expectancy; profit factor > 1.15; drawdown acceptable relative to return; at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| residual_grid:MO/XLP | FAIL | at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| residual_grid:XOM/XLE | FAIL | positive OOS expectancy; profit factor > 1.15; drawdown acceptable relative to return; nearby-parameter robustness |
| residual_grid:JPM/XLF | FAIL | at least 20 OOS trades |
| residual_grid:PFE/XLV | FAIL | positive OOS expectancy; profit factor > 1.15; drawdown acceptable relative to return; at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| stock_pair_grid:VZ/T | FAIL | at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| stock_pair_grid:KO/PEP | FAIL | positive OOS expectancy; profit factor > 1.15; drawdown acceptable relative to return; at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| stock_pair_grid:XOM/CVX | FAIL | positive OOS expectancy; profit factor > 1.15; drawdown acceptable relative to return; at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| stock_pair_grid:JPM/BAC | FAIL | drawdown acceptable relative to return; at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| stock_pair_grid:MA/V | FAIL | at least 20 OOS trades |
| natural_long_grid:CSCO | FAIL | at least 20 OOS trades |
| natural_long_grid:VZ | FAIL | drawdown acceptable relative to return; at least 20 OOS trades; nearby-parameter robustness |
| natural_long_grid:T | FAIL | positive OOS expectancy; profit factor > 1.15; drawdown acceptable relative to return; at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| natural_long_grid:MO | FAIL | at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| natural_long_grid:KO | FAIL | drawdown acceptable relative to return; at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| natural_long_grid:PEP | FAIL | positive OOS expectancy; profit factor > 1.15; drawdown acceptable relative to return; at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| natural_long_grid:XOM | FAIL | at least 20 OOS trades; nearby-parameter robustness |
| natural_long_grid:CVX | FAIL | at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| natural_long_grid:JPM | FAIL | at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| natural_long_grid:BAC | FAIL | positive OOS expectancy; profit factor > 1.15; drawdown acceptable relative to return; at least 20 OOS trades; no single trade dominates gross profit; no single week dominates gross profit; nearby-parameter robustness |
| natural_long_grid:MA | FAIL | positive OOS expectancy; profit factor > 1.15; drawdown acceptable relative to return; at least 20 OOS trades; nearby-parameter robustness |
| natural_long_grid:V | FAIL | at least 20 OOS trades; nearby-parameter robustness |
| natural_long_grid:PFE | FAIL | positive OOS expectancy; profit factor > 1.15; drawdown acceptable relative to return; at least 20 OOS trades; nearby-parameter robustness |

## Strategies that appear promising but did not necessarily pass

- residual_grid:MO/XLP
- residual_grid:JPM/XLF
- stock_pair_grid:VZ/T
- stock_pair_grid:JPM/BAC
- stock_pair_grid:MA/V
- natural_long_grid:CSCO
- natural_long_grid:VZ
- natural_long_grid:MO
- natural_long_grid:KO
- natural_long_grid:XOM
- natural_long_grid:CVX
- natural_long_grid:JPM
- natural_long_grid:V

## Strategies that failed the preliminary profitability screen

- residual_grid:CSCO/XLK
- residual_grid:CSCO/QQQ
- residual_grid:VZ/XLC
- residual_grid:XOM/XLE
- residual_grid:PFE/XLV
- stock_pair_grid:KO/PEP
- stock_pair_grid:XOM/CVX
- natural_long_grid:T
- natural_long_grid:PEP
- natural_long_grid:BAC
- natural_long_grid:MA
- natural_long_grid:PFE

## Known limitations

- Yahoo Finance/yfinance is a convenient research fallback, not an exchange-grade licensed backtest feed. Corporate-action corrections can be revised after the fact.
- The earnings dataset is retrieved retrospectively and is not a point-in-time announcement archive; dates are usable for exclusion windows, but revision history is unavailable.
- Only about 60 days of 15-minute history was available. Main OOS conclusions therefore use daily candles, which cannot reproduce intraday grid sequencing.
- Historical borrow availability and actual borrow fees are unavailable; short legs use the configured flat placeholder.
- Bid/ask quotes and queue position are unavailable. Spread and slippage are modeled conservatively, and fills are bounded by candle ranges.
- The controlled universe is curated and contains current survivors; results remain exposed to selection and survivorship bias.
- One-at-a-time sensitivity detects local fragility but does not exhaust the full parameter interaction product.
- A single three-year market sample is not enough to establish production readiness.

## Final recommendation

Do not add Bybit, MEXC, broker routing, or any live-trading integration. The Phase 2A acceptance gate was not met.
