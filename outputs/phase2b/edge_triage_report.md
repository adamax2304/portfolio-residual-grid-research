# Phase 2B — Edge Triage & Signal Density Expansion

## Decision

**The project remains NO-GO for live trading. Phase 2A's NO-GO is unchanged.**

Phase 2B is diagnostic research only. No exchange, broker, live-order, or API-trading integration was added.

## What Phase 2B tested

- Extended adjusted daily sample: 2020-09-01 00:00:00 through 2026-09-04 00:00:00.
- Expanded liquid large/mid-cap strategy runs across all three families: 169 total runs.
- Same-sector/economic pair candidates screened: 62; selected before backtesting: 26.
- One-at-a-time signal-density variants on the four deep-dive controls: 87.
- Phase 2C research-gate promotions: 1.

## Phase 2A candidate triage

The original OOS return and campaign accounting below come directly from the preserved Phase 2A sidecars. `Trade legs` counts realized closing legs; `Campaigns` counts complete entry-to-flat episodes.

| Run | Class | OOS | PF | Exp. | DD | Trade legs | Campaigns | Avg h | Exposure | Avg MAE | Avg MFE | Worst | Best | Top campaign/week/month |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| residual_grid:CSCO/XLK | TOO_FEW_TRADES | 0.00% | 0.00 | $0 | 0.00% | 0 | 0 | 0.0 | 0.00% | $0 | $0 | $0 | $0 | n/a/n/a/n/a |
| residual_grid:CSCO/QQQ | TOO_FEW_TRADES | 0.00% | 0.00 | $0 | 0.00% | 0 | 0 | 0.0 | 0.00% | $0 | $0 | $0 | $0 | n/a/n/a/n/a |
| residual_grid:VZ/XLC | TOO_FEW_TRADES | 0.00% | 0.00 | $0 | 0.00% | 0 | 0 | 0.0 | 0.00% | $0 | $0 | $0 | $0 | n/a/n/a/n/a |
| residual_grid:MO/XLP | TOO_FEW_TRADES | 0.26% | 3.11 | $128 | -0.26% | 4 | 2 | 96.0 | 0.95% | $-131 | $164 | $-121 | $376 | 100.00%/100.00%/100.00% |
| residual_grid:XOM/XLE | FAILED_EDGE | -2.54% | 0.30 | $-121 | -3.78% | 48 | 21 | 122.3 | 11.57% | $-185 | $46 | $-1,094 | $453 | 40.74%/40.74%/42.04% |
| residual_grid:JPM/XLF | PROMISING_BUT_UNDERPOWERED | 2.13% | 2.49 | $119 | -0.82% | 46 | 18 | 137.3 | 11.09% | $-119 | $259 | $-493 | $812 | 22.76%/22.76%/25.55% |
| residual_grid:PFE/XLV | TOO_FEW_TRADES | 0.00% | 0.00 | $0 | 0.00% | 0 | 0 | 0.0 | 0.00% | $0 | $0 | $0 | $0 | n/a/n/a/n/a |
| stock_pair_grid:VZ/T | TOO_FEW_TRADES | 0.14% | ∞ | $139 | -0.13% | 2 | 1 | 168.0 | 0.63% | $-129 | $264 | $139 | $139 | 100.00%/100.00%/100.00% |
| stock_pair_grid:KO/PEP | TOO_FEW_TRADES | 0.00% | 0.00 | $0 | 0.00% | 0 | 0 | 0.0 | 0.00% | $0 | $0 | $0 | $0 | n/a/n/a/n/a |
| stock_pair_grid:XOM/CVX | FAILED_EDGE | -0.52% | 0.48 | $-58 | -0.68% | 18 | 9 | 61.3 | 3.17% | $-92 | $50 | $-610 | $246 | 51.32%/51.32%/64.70% |
| stock_pair_grid:JPM/BAC | TOO_FEW_TRADES | 0.44% | 1.30 | $55 | -0.99% | 18 | 8 | 120.0 | 4.44% | $-186 | $267 | $-907 | $1,137 | 59.23%/59.23%/96.44% |
| stock_pair_grid:MA/V | TOO_FEW_TRADES | 0.55% | 2.46 | $61 | -0.54% | 18 | 9 | 93.3 | 3.33% | $-100 | $97 | $-163 | $401 | 43.08%/43.08%/52.21% |
| natural_long_grid:CSCO | TOO_FEW_TRADES | 1.36% | 14.24 | $170 | -1.47% | 12 | 8 | 528.0 | 19.49% | $-148 | $314 | $-64 | $559 | 38.20%/38.20%/38.20% |
| natural_long_grid:VZ | TOO_FEW_TRADES | 0.38% | 1.30 | $42 | -1.23% | 18 | 9 | 597.3 | 23.45% | $-201 | $293 | $-1,017 | $591 | 36.21%/36.21%/36.21% |
| natural_long_grid:T | TOO_FEW_TRADES | -0.71% | 0.18 | $-238 | -0.81% | 4 | 3 | 240.0 | 3.17% | $-283 | $45 | $-730 | $154 | 100.00%/100.00%/100.00% |
| natural_long_grid:MO | TOO_FEW_TRADES | 1.06% | 5.76 | $352 | -0.40% | 5 | 3 | 216.0 | 3.17% | $-26 | $530 | $-222 | $1,092 | 85.35%/85.35%/85.35% |
| natural_long_grid:KO | TOO_FEW_TRADES | 0.71% | 1.74 | $118 | -1.46% | 10 | 6 | 408.0 | 11.25% | $-256 | $400 | $-937 | $924 | 55.21%/55.21%/55.21% |
| natural_long_grid:PEP | FAILED_EDGE | -1.77% | 0.64 | $-196 | -5.44% | 12 | 9 | 464.0 | 19.02% | $-599 | $478 | $-1,816 | $2,865 | 92.12%/92.12%/92.12% |
| natural_long_grid:XOM | TOO_FEW_TRADES | 0.56% | 1.55 | $70 | -0.99% | 14 | 8 | 552.0 | 19.33% | $-203 | $317 | $-609 | $467 | 29.66%/29.66%/32.33% |
| natural_long_grid:CVX | TOO_FEW_TRADES | 1.35% | 1.91 | $193 | -1.50% | 10 | 7 | 545.1 | 16.96% | $-273 | $510 | $-1,368 | $1,461 | 51.53%/51.53%/51.53% |
| natural_long_grid:JPM | TOO_FEW_TRADES | 1.37% | ∞ | $456 | -0.80% | 6 | 3 | 672.0 | 9.19% | $-206 | $564 | $230 | $883 | 64.59%/64.59%/64.59% |
| natural_long_grid:BAC | TOO_FEW_TRADES | -2.54% | 0.00 | $-845 | -2.89% | 4 | 3 | 320.0 | 4.75% | $-888 | $173 | $-1,210 | $-377 | n/a/n/a/n/a |
| natural_long_grid:MA | FAILED_EDGE | -0.85% | 0.65 | $-77 | -2.51% | 16 | 11 | 412.4 | 20.76% | $-310 | $182 | $-923 | $536 | 34.72%/34.72%/34.72% |
| natural_long_grid:V | PROMISING_BUT_UNDERPOWERED | 0.80% | 1.35 | $80 | -1.28% | 18 | 10 | 487.2 | 21.87% | $-259 | $424 | $-1,031 | $1,021 | 33.37%/33.37%/36.42% |
| natural_long_grid:PFE | FAILED_EDGE | -4.72% | 0.32 | $-429 | -5.80% | 17 | 11 | 497.5 | 24.72% | $-723 | $279 | $-4,803 | $750 | 34.27%/34.27%/38.09% |

Classification counts: TOO_FEW_TRADES=18, FAILED_EDGE=5, PROMISING_BUT_UNDERPOWERED=2.

## Triage diagnosis

- Phase 2A had 5 zero-campaign runs, direct evidence that its filters/universe left some hypotheses untestable.
- 3 Phase 2A runs had at least 10 campaigns and still showed non-positive expectancy or PF ≤ 1, evidence of weak edge rather than density alone.
- In the expanded sample, natural grids reached a median 20 campaigns versus 7 for residual ETF runs. Expansion improved diagnosis, but did not produce a broad robust edge.
- The result is therefore mixed: Phase 2A was underpowered in many runs, but loosening density constraints does not rescue the residual or pair families after costs.

## Phase 2A regime and exit attribution

| Run | Range regime | Breakout regime | Failed breakout | Warning | Kill | Time stop | Grid mode | Hybrid | Long residual | Short residual |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| residual_grid:CSCO/XLK | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 |
| residual_grid:CSCO/QQQ | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 |
| residual_grid:VZ/XLC | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 |
| residual_grid:MO/XLP | $376 | $0 | $0 | $-121 | $-121 | $376 | $255 | $0 | $255 | $0 |
| residual_grid:XOM/XLE | $-272 | $-191 | $0 | $-2,074 | $-2,074 | $-642 | $-2,346 | $-143 | $-2,874 | $337 |
| residual_grid:JPM/XLF | $2,383 | $-511 | $0 | $262 | $262 | $1,975 | $2,645 | $-493 | $912 | $1,222 |
| residual_grid:PFE/XLV | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 |
| stock_pair_grid:VZ/T | $139 | $0 | $0 | $0 | $0 | $139 | $139 | $0 | $139 | $0 |
| stock_pair_grid:KO/PEP | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 | $0 |
| stock_pair_grid:XOM/CVX | $-882 | $436 | $0 | $-79 | $-79 | $-272 | $-961 | $365 | $-383 | $-141 |
| stock_pair_grid:JPM/BAC | $1,137 | $-689 | $0 | $-5 | $-5 | $1,137 | $1,132 | $-1,438 | $-174 | $617 |
| stock_pair_grid:MA/V | $754 | $0 | $0 | $-201 | $-201 | $754 | $553 | $0 | $191 | $362 |
| natural_long_grid:CSCO | $752 | $0 | $0 | $608 | $608 | $816 | $1,360 | $0 | $1,360 | $0 |
| natural_long_grid:VZ | $1,173 | $0 | $0 | $-794 | $-794 | $1,173 | $379 | $0 | $379 | $0 |
| natural_long_grid:T | $0 | $0 | $0 | $-715 | $-715 | $0 | $-715 | $0 | $-715 | $0 |
| natural_long_grid:MO | $1,279 | $0 | $0 | $-222 | $-222 | $0 | $1,057 | $0 | $1,057 | $0 |
| natural_long_grid:KO | $-410 | $0 | $0 | $1,120 | $1,120 | $-680 | $710 | $0 | $710 | $0 |
| natural_long_grid:PEP | $3,110 | $0 | $0 | $-4,876 | $-4,876 | $245 | $-1,766 | $0 | $-1,766 | $0 |
| natural_long_grid:XOM | $1,040 | $0 | $0 | $-479 | $-479 | $574 | $561 | $0 | $561 | $0 |
| natural_long_grid:CVX | $2,609 | $0 | $0 | $-1,255 | $-1,255 | $2,609 | $1,354 | $0 | $1,354 | $0 |
| natural_long_grid:JPM | $1,368 | $0 | $0 | $0 | $0 | $1,368 | $1,368 | $0 | $1,368 | $0 |
| natural_long_grid:BAC | $0 | $0 | $0 | $-2,536 | $-2,536 | $0 | $-2,536 | $0 | $-2,536 | $0 |
| natural_long_grid:MA | $887 | $0 | $0 | $-1,736 | $-1,736 | $583 | $-849 | $0 | $-849 | $0 |
| natural_long_grid:V | $2,311 | $235 | $0 | $-1,748 | $-1,748 | $2,311 | $562 | $235 | $797 | $0 |
| natural_long_grid:PFE | $1,600 | $0 | $0 | $-6,317 | $-6,317 | $1,600 | $-4,717 | $0 | $-4,717 | $0 |

## Expanded-universe results by family

| Family | Runs | Positive edge | Median return | Median PF | Median campaigns | Median robustness | Phase 2C |
| --- | --- | --- | --- | --- | --- | --- | --- |
| natural | 71 | 46.48% | 0.33% | 1.14 | 20.0 | 36.36% | 1 |
| pair | 26 | 34.62% | -0.19% | 0.53 | 8.0 | 18.18% | 0 |
| residual | 72 | 33.33% | -0.07% | 0.47 | 7.0 | 27.27% | 0 |

### Highest-ranked expanded runs

| Run | OOS | PF | Expectancy | DD | Legs | Campaigns | 2x-cost exp. | Local pass | Robustness | Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| natural_long_grid:XOM | 3.75% | 2.43 | $150 | -1.08% | 35 | 25 | $141 | 100.00% | 90.91% | PASS |
| stock_pair_grid:MA/V | 1.12% | 3.54 | $80 | -0.68% | 32 | 14 | $47 | 100.00% | 81.82% | FAIL |
| natural_long_grid:LOW | 1.76% | 1.54 | $59 | -1.44% | 36 | 30 | $51 | 100.00% | 81.82% | FAIL |
| natural_long_grid:GS | 6.74% | 5.88 | $375 | -1.45% | 22 | 18 | $363 | 100.00% | 72.73% | FAIL |
| natural_long_grid:SO | 5.01% | 3.78 | $251 | -1.00% | 25 | 20 | $236 | 100.00% | 72.73% | FAIL |
| natural_long_grid:GE | 4.47% | 3.18 | $248 | -1.02% | 26 | 18 | $239 | 100.00% | 72.73% | FAIL |
| natural_long_grid:AEP | 4.37% | 2.55 | $243 | -2.35% | 23 | 18 | $231 | 80.00% | 72.73% | FAIL |
| natural_long_grid:DE | 4.42% | 3.39 | $201 | -1.16% | 27 | 22 | $190 | 100.00% | 72.73% | FAIL |
| natural_long_grid:DUK | 3.95% | 2.51 | $188 | -1.56% | 33 | 21 | $176 | 100.00% | 72.73% | FAIL |
| natural_long_grid:WMT | 2.79% | 2.97 | $186 | -0.98% | 18 | 15 | $173 | 100.00% | 72.73% | FAIL |
| natural_long_grid:O | 2.65% | 4.87 | $177 | -1.06% | 21 | 15 | $167 | 100.00% | 72.73% | FAIL |
| natural_long_grid:MRK | 3.52% | 3.27 | $168 | -1.07% | 28 | 21 | $158 | 100.00% | 72.73% | FAIL |
| natural_long_grid:SHW | 3.43% | 1.85 | $143 | -1.78% | 31 | 24 | $130 | 100.00% | 72.73% | FAIL |
| natural_long_grid:RTX | 4.18% | 3.72 | $261 | -1.43% | 20 | 16 | $249 | 60.00% | 63.64% | FAIL |
| residual_grid:AMZN/XLY | 1.44% | ∞ | $180 | -0.23% | 20 | 8 | $154 | n/a | 63.64% | FAIL |
| stock_pair_grid:JPM/GS | 1.79% | 3.48 | $149 | -0.96% | 36 | 12 | $118 | n/a | 63.64% | FAIL |
| residual_grid:EQIX/XLRE | 0.97% | 4.76 | $121 | -0.52% | 20 | 8 | $95 | n/a | 63.64% | FAIL |
| stock_pair_grid:JPM/BAC | 1.03% | 6.27 | $103 | -0.62% | 22 | 10 | $71 | n/a | 63.64% | FAIL |
| residual_grid:LIN/XLB | 1.13% | 2.30 | $103 | -0.82% | 22 | 11 | $56 | n/a | 63.64% | FAIL |
| stock_pair_grid:JPM/MS | 0.66% | ∞ | $94 | -0.25% | 18 | 7 | $69 | n/a | 63.64% | FAIL |

## Pair screening

Pairs were formed only inside the named economic groups, then screened on overlap, liquidity, median rolling correlation, beta stability, half-life/crossing stationarity proxies, and event-blocked share.

| Pair | Group | Corr | Beta stability | Half-life | Crossings/yr | ADF p | Event-blocked | Min ADV |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| JPM/BAC | banks | 0.80 | 0.19 | 13.3 | 11.3 | 0.000 | 26.16% | $1,550,990,522 |
| JPM/WFC | banks | 0.75 | 0.23 | 13.0 | 12.2 | 0.000 | 25.83% | $1,056,516,810 |
| JPM/C | banks | 0.77 | 0.21 | 15.2 | 10.7 | 0.000 | 25.83% | $1,018,022,438 |
| JPM/GS | banks | 0.77 | 0.23 | 11.2 | 13.5 | 0.000 | 26.49% | $896,552,465 |
| JPM/MS | banks | 0.73 | 0.27 | 14.1 | 15.0 | 0.000 | 26.49% | $707,376,511 |
| BAC/WFC | banks | 0.81 | 0.19 | 12.0 | 11.9 | 0.000 | 29.47% | $1,056,516,810 |
| BAC/C | banks | 0.81 | 0.26 | 18.7 | 15.8 | 0.000 | 29.14% | $1,018,022,438 |
| BAC/GS | banks | 0.74 | 0.26 | 13.1 | 9.6 | 0.000 | 24.83% | $896,552,465 |
| BAC/MS | banks | 0.77 | 0.24 | 15.7 | 10.9 | 0.000 | 27.81% | $707,376,511 |
| WFC/C | banks | 0.75 | 0.27 | 12.6 | 12.8 | 0.000 | 24.83% | $1,018,022,438 |
| WFC/GS | banks | 0.70 | 0.26 | 8.5 | 13.9 | 0.000 | 29.80% | $896,552,465 |
| WFC/MS | banks | 0.66 | 0.28 | 11.3 | 14.5 | 0.000 | 29.47% | $707,376,511 |
| C/GS | banks | 0.75 | 0.24 | 13.0 | 11.1 | 0.000 | 29.47% | $896,552,465 |
| C/MS | banks | 0.73 | 0.25 | 14.4 | 11.9 | 0.000 | 25.50% | $707,376,511 |
| GS/MS | banks | 0.85 | 0.18 | 10.4 | 11.1 | 0.000 | 28.81% | $707,376,511 |
| MA/V | payments | 0.86 | 0.19 | 9.3 | 12.6 | 0.000 | 32.45% | $1,229,954,911 |
| VZ/T | telecom | 0.70 | 0.36 | 9.2 | 11.3 | 0.000 | 22.85% | $723,407,999 |
| KO/PEP | staples | 0.69 | 0.39 | 15.0 | 11.7 | 0.000 | 32.12% | $817,890,494 |
| KO/MDLZ | staples | 0.64 | 0.34 | 10.3 | 11.7 | 0.000 | 32.12% | $421,327,919 |
| KO/CL | staples | 0.62 | 0.28 | 12.4 | 14.3 | 0.000 | 29.47% | $360,518,265 |
| PEP/PG | staples | 0.64 | 0.41 | 13.4 | 15.0 | 0.000 | 30.79% | $817,890,494 |
| PG/CL | staples | 0.73 | 0.33 | 10.1 | 12.2 | 0.000 | 22.19% | $360,518,265 |
| XOM/CVX | energy | 0.85 | 0.27 | 15.3 | 12.2 | 0.000 | 27.15% | $1,134,656,699 |
| XOM/COP | energy | 0.83 | 0.26 | 13.3 | 12.8 | 0.000 | 30.13% | $609,964,283 |
| CVX/COP | energy | 0.82 | 0.33 | 13.4 | 12.2 | 0.000 | 32.78% | $609,964,283 |
| HPQ/HPE | tech_enterprise | 0.62 | 0.41 | 12.7 | 14.5 | 0.000 | 28.81% | $189,808,908 |

The full selected/rejected audit, including failure reasons, is in `pair_diagnostics.csv`.

## Signal-density diagnostics

Sweeps are one-at-a-time, not a Cartesian optimization. A valid signal is an ARMED transition; a generated trade is a completed campaign.

| Family | Dimension | Variants | Min trades | Median | Max | Positive/PF>1.15 | Survives 2x cost | Mean robust |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| natural | adx_filter | 2 | 19 | 24.0 | 29 | 0.00% | 0.00% | 57.14% |
| natural | event_exclusion_days | 3 | 19 | 19.0 | 19 | 0.00% | 0.00% | 57.14% |
| natural | grid_levels | 4 | 19 | 19.0 | 20 | 0.00% | 0.00% | 57.14% |
| natural | time_stop_days | 3 | 19 | 27.0 | 31 | 33.33% | 33.33% | 71.43% |
| pair | adx_filter | 2 | 14 | 18.0 | 22 | 100.00% | 100.00% | 100.00% |
| pair | beta_stability_threshold | 3 | 12 | 14.0 | 18 | 100.00% | 100.00% | 100.00% |
| pair | correlation_threshold | 5 | 14 | 15.0 | 15 | 100.00% | 100.00% | 100.00% |
| pair | event_exclusion_days | 3 | 13 | 14.0 | 14 | 100.00% | 100.00% | 100.00% |
| pair | grid_levels | 4 | 14 | 14.0 | 14 | 100.00% | 100.00% | 92.86% |
| pair | time_stop_days | 3 | 14 | 14.0 | 16 | 100.00% | 100.00% | 100.00% |
| pair | z_entry | 5 | 8 | 12.0 | 22 | 100.00% | 100.00% | 91.43% |
| residual | adx_filter | 4 | 20 | 34.5 | 48 | 50.00% | 0.00% | 71.43% |
| residual | beta_stability_threshold | 6 | 18 | 20.5 | 25 | 33.33% | 0.00% | 69.05% |
| residual | correlation_threshold | 10 | 11 | 22.5 | 25 | 40.00% | 0.00% | 68.57% |
| residual | event_exclusion_days | 6 | 19 | 21.0 | 26 | 50.00% | 0.00% | 71.43% |
| residual | grid_levels | 8 | 20 | 21.5 | 23 | 50.00% | 0.00% | 71.43% |
| residual | time_stop_days | 6 | 19 | 22.5 | 27 | 50.00% | 16.67% | 73.81% |
| residual | z_entry | 10 | 8 | 18.5 | 37 | 30.00% | 10.00% | 61.43% |

## Breakout continuation attribution

| Family | Runs | Mean incremental return | PF improved | DD improved | Dependent | Grid P&L | Breakout/hybrid P&L | Research setting |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| natural | 71 | 0.00% | 0.00% | 0.00% | 0 | $36,168 | $0 | NO EFFECT OBSERVED |
| pair | 26 | 0.08% | 42.31% | 50.00% | 1 | $3,156 | $-4,920 | DISABLE IN BASELINE: mixed counterfactual, negative campaign contribution |
| residual | 72 | -0.01% | 27.78% | 31.94% | 4 | $-1,401 | $-18,171 | DISABLE: negative aggregate and incremental contribution |

`breakout_attribution.csv` contains the enabled-versus-disabled comparison for every Phase 2A and expanded run, plus kill, failed-breakout, time-stop, grid, hybrid, and direction contributions.

## Liquidity sweep/reclaim prototype

The required variant enters only after a later reclaim candle, one to three bars after the sweep. The boost variant leaves eligibility unchanged and increases size only when that causal confirmation exists.

| Run | Mode | Campaigns | Δ trades | PF | ΔPF | Expectancy | Δ expectancy | DD | ΔDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| residual_grid:JPM/XLF | none | 20 | 0 | 1.22 | 0.00 | $20 | $0 | -1.07% | 0.00% |
| residual_grid:JPM/XLF | required | 1 | -19 | ∞ | ∞ | $10 | $-10 | -0.04% | 1.03% |
| residual_grid:JPM/XLF | boost | 20 | 0 | 1.22 | 0.00 | $21 | $0 | -1.07% | 0.00% |
| residual_grid:XOM/XLE | none | 25 | 0 | 0.36 | 0.00 | $-79 | $0 | -2.90% | 0.00% |
| residual_grid:XOM/XLE | required | 2 | -23 | 4.42 | 4.06 | $105 | $184 | -0.09% | 2.81% |
| residual_grid:XOM/XLE | boost | 25 | 0 | 0.36 | 0.00 | $-79 | $0 | -2.90% | 0.00% |
| natural_long_grid:CSCO | none | 19 | 0 | 0.93 | 0.00 | $-7 | $0 | -4.32% | 0.00% |
| natural_long_grid:CSCO | required | 2 | -17 | ∞ | ∞ | $162 | $169 | -0.07% | 4.25% |
| natural_long_grid:CSCO | boost | 19 | 0 | 0.93 | 0.00 | $-7 | $0 | -4.32% | 0.00% |

## Phase 2B research-only gate

Promoted to Phase 2C diagnostic candidates: natural_long_grid:XOM.

Positive but explicitly underpowered runs: residual_grid:HPQ/XLK, residual_grid:MSFT/XLK, residual_grid:GOOGL/XLC, residual_grid:MO/XLP, residual_grid:JPM/XLF, residual_grid:WFC/XLF, residual_grid:V/XLF, residual_grid:AXP/XLF, residual_grid:CVX/XLE, residual_grid:LLY/XLV, residual_grid:MDT/XLV, residual_grid:HON/XLI, residual_grid:DUK/XLU, residual_grid:AMZN/XLY, residual_grid:HD/XLY, residual_grid:NKE/XLY, residual_grid:LOW/XLY, residual_grid:SBUX/XLY, residual_grid:LIN/XLB, residual_grid:SHW/XLB….

Every check and failure reason is recorded in `phase2b_acceptance.json`.

## Answers to the Phase 2B questions

- **Live status:** NO-GO remains in force.
- **Deeper research:** The only research promotions are natural_long_grid:XOM.
- **Residual ETF versus natural long:** Natural long grid is stronger on the predeclared family comparison (promotion count, then median robustness). This is a research ranking, not evidence for deployment.
- **Stock-to-stock pairs:** The pair family is not yet viable under the research gate. MA/V is locally stable in the density sweep but remains underpowered and profit-concentrated.
- **Breakout continuation:** Across families, average incremental return was 0.02%. Disable it for residual and pair research baselines; natural grids recorded no continuation activity in this daily sample.
- **Liquidity sweeps:** No required-filter prototype retained 10 campaigns. The one- and two-campaign improvements are underpowered; the filter currently removes too many entries to claim benefit.

## Recommended next phase

Phase 2C should independently replicate only the promoted runs using a longer point-in-time event archive and licensed multi-year intraday data, with parameters frozen before the new sample.

Do not add live-trading infrastructure in either case.

## Limitations

- The extended study still uses adjusted daily Yahoo/yfinance candles; it cannot resolve intraday path ordering.
- Earnings dates are retrospective rather than a point-in-time announcement archive.
- The universe is controlled but survivor-selected, so cross-sectional results retain survivorship bias.
- Pair stationarity uses rolling-correlation, beta-stability, half-life, crossings, and ADF proxies; it is not proof of a stable economic equilibrium.
- One-at-a-time density and local-neighborhood tests diagnose fragility but do not explore all parameter interactions.
- Strict-cost estimates hold the realized trade path fixed; selected candidates also receive local reruns, but queue and quote data remain unavailable.