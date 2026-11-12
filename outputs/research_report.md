# Residual Grid + Breakout Continuation Research Report

Generated: 2026-09-07T12:59:46.815418+00:00

## Executive verdict

This run validates software behavior on synthetic data only. It makes **no market-edge claim**, regardless of simulated returns.

## Scope and methodology

- Data source: deterministic synthetic fixture (pipeline validation only; not evidence of edge)
- Price basis: total-return adjusted on every relationship leg.
- Execution: signals at bar close, fills at the next bar open; no lookahead.
- Ambiguous same-bar stop/target: adverse outcome first by default.
- Core intraday session: 09:30–16:00 America/New_York; open/close confirmation buffers are configurable.
- Event coverage: No historical event file supplied; event-filtered claims are provisional.
- Configuration: `C:\Users\adama\Documents\residual_grid_research\config\default.yaml`
- Live order routing: deliberately absent.

## Phase 1a — relationship diagnostics

| Relationship | N | Corr 60 | Half-life | Crossings/year | Kill failure | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| CSCO/XLK | 750 | 0.816 | 3.5 | 23.5 | 7.14% | GO: relationship shows testable mean-reversion structure |
| CSCO/QQQ | 750 | 0.844 | 4.0 | 19.8 | 6.78% | GO: relationship shows testable mean-reversion structure |
| VZ/XLC | 750 | 0.872 | 3.6 | 19.8 | 13.56% | GO: relationship shows testable mean-reversion structure |
| MO/XLP | 750 | 0.855 | 3.9 | 20.2 | 6.67% | GO: relationship shows testable mean-reversion structure |
| JPM/XLF | 750 | 0.816 | 3.3 | 20.8 | 11.29% | GO: relationship shows testable mean-reversion structure |
| XOM/XLE | 750 | 0.706 | 3.1 | 20.2 | 10.00% | GO: relationship shows testable mean-reversion structure |
| VZ/T | 750 | 0.730 | 3.8 | 24.5 | 2.74% | GO: relationship shows testable mean-reversion structure |
| KO/PEP | 750 | 0.841 | 3.5 | 20.8 | 0.00% | GO: relationship shows testable mean-reversion structure |
| XOM/CVX | 750 | 0.864 | 3.5 | 21.2 | 1.59% | GO: relationship shows testable mean-reversion structure |
| JPM/BAC | 750 | 0.784 | 4.0 | 23.2 | 7.25% | GO: relationship shows testable mean-reversion structure |
| MA/V | 750 | 0.862 | 3.4 | 20.8 | 9.68% | GO: relationship shows testable mean-reversion structure |
| HD/LOW | 750 | 0.838 | 2.8 | 21.8 | 3.08% | GO: relationship shows testable mean-reversion structure |
| WMT/TGT | 750 | 0.879 | 3.5 | 17.5 | 7.69% | GO: relationship shows testable mean-reversion structure |
| UPS/FDX | 750 | 0.822 | 3.6 | 22.2 | 4.55% | GO: relationship shows testable mean-reversion structure |
| COP/EOG | 750 | 0.811 | 4.1 | 17.5 | 5.77% | GO: relationship shows testable mean-reversion structure |
| MS/GS | 750 | 0.883 | 3.3 | 20.5 | 1.64% | GO: relationship shows testable mean-reversion structure |
| AEP/EXC | 750 | 0.851 | 3.9 | 23.5 | 2.86% | GO: relationship shows testable mean-reversion structure |
| DOW/DD | 750 | 0.922 | 3.6 | 23.2 | 1.45% | GO: relationship shows testable mean-reversion structure |

## Strategy results

| Strategy | Return | Annualized | Max DD | Sharpe | Sortino | PF | Win rate | Fills | Kills | Cost drag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| residual_grid:CSCO/XLK | 0.91% | 0.26% | -0.34% | 0.462 | 0.720 | 4.433 | 60.00% | 9 | 0 | $100.92 |
| residual_grid:CSCO/QQQ | 0.26% | 0.08% | -0.06% | 0.810 | 1.387 | 1.782 | 40.00% | 7 | 0 | $36.82 |
| residual_grid:VZ/XLC | 0.13% | 0.04% | -0.08% | 0.316 | 0.506 | 111.205 | 75.00% | 6 | 0 | $40.44 |
| residual_grid:MO/XLP | 0.83% | 0.24% | -0.48% | 0.500 | 0.772 | 3.162 | 33.33% | 9 | 0 | $107.99 |
| residual_grid:JPM/XLF | 0.50% | 0.15% | -0.03% | 0.851 | 8.874 | 3.158 | 33.33% | 5 | 0 | $32.28 |
| residual_grid:XOM/XLE | -0.22% | -0.06% | -0.30% | -0.534 | -0.378 | 0.242 | 20.00% | 9 | 0 | $64.80 |
| stock_pair_grid:VZ/T | 0.16% | 0.05% | -0.88% | 0.062 | 0.072 | 1.072 | 50.00% | 10 | 0 | $172.70 |
| stock_pair_grid:KO/PEP | -0.38% | -0.11% | -0.49% | -0.537 | -0.422 | 0.615 | 50.00% | 8 | 0 | $62.79 |
| stock_pair_grid:XOM/CVX | 0.14% | 0.04% | -0.11% | 0.315 | 0.360 | 1.336 | 50.00% | 8 | 0 | $61.50 |
| stock_pair_grid:JPM/BAC | 0.24% | 0.07% | -0.00% | 0.671 | 105.990 | 3.441 | 42.86% | 9 | 0 | $16.16 |
| stock_pair_grid:MA/V | -0.35% | -0.10% | -0.35% | -0.554 | -0.353 | 0.021 | 25.00% | 6 | 1 | $36.95 |
| stock_pair_grid:HD/LOW | -0.06% | -0.02% | -0.17% | -0.144 | -0.139 | 0.884 | 60.00% | 9 | 0 | $55.14 |
| stock_pair_grid:WMT/TGT | 0.29% | 0.08% | -0.08% | 0.528 | 1.571 | 2.079 | 71.43% | 9 | 0 | $34.21 |
| stock_pair_grid:UPS/FDX | 0.61% | 0.18% | -0.16% | 0.780 | 1.116 | 1.912 | 53.33% | 23 | 0 | $143.19 |
| stock_pair_grid:COP/EOG | 0.55% | 0.16% | -0.16% | 0.502 | 1.088 | 1.834 | 42.86% | 11 | 0 | $67.06 |
| stock_pair_grid:MS/GS | -0.09% | -0.03% | -0.33% | -0.167 | -0.159 | 0.769 | 33.33% | 9 | 0 | $101.13 |
| stock_pair_grid:AEP/EXC | 0.24% | 0.07% | -0.03% | 0.585 | 2.487 | 2.259 | 71.43% | 9 | 0 | $41.87 |
| stock_pair_grid:DOW/DD | 0.03% | 0.01% | -0.17% | 0.077 | 0.078 | 1.049 | 33.33% | 5 | 0 | $31.34 |
| natural_long_grid:CSCO | 1.62% | 0.47% | -2.98% | 0.199 | 0.235 | 2.104 | 77.78% | 21 | 1 | $59.58 |
| natural_long_grid:VZ | 0.94% | 0.27% | -0.79% | 0.405 | 0.487 | 2.416 | 57.14% | 14 | 2 | $31.81 |
| natural_long_grid:MO | 0.70% | 0.20% | -1.88% | 0.163 | 0.179 | 75.675 | 75.00% | 8 | 0 | $20.68 |
| natural_long_grid:JPM | -2.47% | -0.72% | -3.97% | -0.253 | -0.273 | 0.144 | 60.00% | 13 | 1 | $44.58 |
| natural_long_grid:XOM | 5.61% | 1.60% | -10.99% | 0.203 | 0.219 | 27.515 | 60.00% | 10 | 1 | $125.77 |
| natural_long_grid:KO | -0.92% | -0.27% | -0.92% | -0.531 | -0.355 | 0.000 | 0.00% | 3 | 1 | $25.23 |
| natural_long_grid:PEP | 0.72% | 0.21% | -2.08% | 0.146 | 0.176 | 151.304 | 75.00% | 8 | 0 | $19.01 |
| natural_long_grid:MA | -0.08% | -0.02% | -3.00% | -0.002 | -0.002 | 0.911 | 50.00% | 8 | 1 | $33.94 |
| natural_long_grid:V | 0.51% | 0.15% | -2.48% | 0.096 | 0.101 | 7.739 | 50.00% | 8 | 0 | $22.69 |
| natural_long_grid:HD | 5.19% | 1.48% | -1.30% | 0.735 | 0.946 | 226.529 | 85.71% | 14 | 0 | $43.08 |
| natural_long_grid:LOW | -8.01% | -2.40% | -11.91% | -0.805 | -0.590 | 0.209 | 50.00% | 26 | 1 | $117.78 |

### Execution and outcome detail

| Strategy | Expectancy R | Mean hold h | Exposure | Turnover | MR success | Breakout success | Return @ 0.5x slip | Return @ 2x slip |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| residual_grid:CSCO/XLK | 0.189 | 84.0 | 0.56% | 2.21 | 60.00% | n/a | 0.94% | 0.84% |
| residual_grid:CSCO/QQQ | 0.055 | 84.0 | 0.44% | 0.77 | 40.00% | n/a | 0.28% | 0.24% |
| residual_grid:VZ/XLC | 0.037 | 84.0 | 0.33% | 0.79 | 75.00% | n/a | 0.14% | 0.11% |
| residual_grid:MO/XLP | 0.290 | 84.0 | 0.56% | 2.32 | 33.33% | n/a | 0.87% | 0.76% |
| residual_grid:JPM/XLF | 0.171 | 84.0 | 0.33% | 0.69 | 33.33% | n/a | 0.51% | 0.48% |
| residual_grid:XOM/XLE | -0.042 | 32.0 | 0.56% | 1.76 | 0.00% | 25.00% | -0.19% | -0.27% |
| stock_pair_grid:VZ/T | 0.056 | 84.0 | 0.56% | 3.41 | 50.00% | n/a | 0.21% | 0.06% |
| stock_pair_grid:KO/PEP | -0.090 | 84.0 | 0.44% | 1.16 | 50.00% | n/a | -0.37% | -0.42% |
| stock_pair_grid:XOM/CVX | 0.041 | 84.0 | 0.44% | 1.27 | 50.00% | n/a | 0.16% | 0.11% |
| stock_pair_grid:JPM/BAC | 0.034 | 36.0 | 0.56% | 0.35 | 42.86% | n/a | 0.24% | 0.23% |
| stock_pair_grid:MA/V | -0.086 | 36.0 | 0.33% | 0.85 | 25.00% | n/a | -0.34% | -0.38% |
| stock_pair_grid:HD/LOW | -0.010 | 32.0 | 0.56% | 1.44 | 100.00% | 50.00% | -0.04% | -0.10% |
| stock_pair_grid:WMT/TGT | 0.042 | 84.0 | 0.56% | 0.75 | 71.43% | n/a | 0.30% | 0.26% |
| stock_pair_grid:UPS/FDX | 0.043 | 108.0 | 1.33% | 3.37 | 53.33% | n/a | 0.66% | 0.51% |
| stock_pair_grid:COP/EOG | 0.081 | 84.0 | 0.67% | 1.56 | 42.86% | n/a | 0.57% | 0.50% |
| stock_pair_grid:MS/GS | -0.023 | 84.0 | 0.56% | 2.52 | 33.33% | n/a | -0.06% | -0.17% |
| stock_pair_grid:AEP/EXC | 0.035 | 48.0 | 0.56% | 1.01 | 71.43% | n/a | 0.25% | 0.21% |
| stock_pair_grid:DOW/DD | 0.012 | 84.0 | 0.33% | 0.66 | 33.33% | n/a | 0.03% | 0.01% |
| natural_long_grid:CSCO | 0.180 | 2490.0 | 2.33% | 1.64 | 77.78% | n/a | 1.64% | 1.57% |
| natural_long_grid:VZ | 0.135 | 696.0 | 1.56% | 0.83 | 57.14% | n/a | 0.96% | 0.92% |
| natural_long_grid:MO | 0.175 | 1944.0 | 0.89% | 0.56 | 75.00% | n/a | 0.71% | 0.68% |
| natural_long_grid:JPM | -0.492 | 3008.0 | 1.44% | 1.27 | 60.00% | n/a | -2.45% | -2.50% |
| natural_long_grid:XOM | 1.122 | 1112.0 | 1.11% | 4.03 | 60.00% | n/a | 5.67% | 5.49% |
| natural_long_grid:KO | -0.458 | 12.0 | 0.33% | 0.79 | 0.00% | n/a | -0.90% | -0.94% |
| natural_long_grid:PEP | 0.181 | 2340.0 | 0.89% | 0.50 | 75.00% | n/a | 0.73% | 0.71% |
| natural_long_grid:MA | -0.020 | 2460.0 | 0.89% | 1.00 | 50.00% | n/a | -0.07% | -0.11% |
| natural_long_grid:V | 0.128 | 3864.0 | 0.89% | 0.62 | 50.00% | n/a | 0.52% | 0.49% |
| natural_long_grid:HD | 0.743 | 1568.0 | 1.56% | 1.20 | 85.71% | n/a | 5.21% | 5.16% |
| natural_long_grid:LOW | -0.800 | 4614.0 | 2.89% | 3.49 | 50.00% | n/a | -7.96% | -8.11% |

### Best and worst realized trade legs

| Strategy | Best 5 | Worst 5 |
| --- | --- | --- |
| residual_grid:CSCO/XLK | $800.71, $393.09, $23.91, $-112.25, $-162.43 | $-162.43, $-112.25, $23.91, $393.09, $800.71 |
| residual_grid:CSCO/QQQ | $537.41, $89.47, $-15.49, $-40.11, $-296.27 | $-296.27, $-40.11, $-15.49, $89.47, $537.41 |
| residual_grid:VZ/XLC | $92.66, $49.73, $6.01, $-1.33 | $-1.33, $6.01, $49.73, $92.66 |
| residual_grid:MO/XLP | $1,273.23, $-3.38, $-399.27 | $-399.27, $-3.38, $1,273.23 |
| residual_grid:JPM/XLF | $750.02, $-0.65, $-236.85 | $-236.85, $-0.65, $750.02 |
| residual_grid:XOM/XLE | $67.17, $-7.07, $-10.14, $-88.16, $-172.16 | $-172.16, $-88.16, $-10.14, $-7.07, $67.17 |
| stock_pair_grid:VZ/T | $3,283.34, $76.50, $-50.75, $-3,083.32 | $-3,083.32, $-50.75, $76.50, $3,283.34 |
| stock_pair_grid:KO/PEP | $532.59, $41.62, $-34.99, $-898.01 | $-898.01, $-34.99, $41.62, $532.59 |
| stock_pair_grid:XOM/CVX | $639.50, $15.07, $-14.78, $-475.20 | $-475.20, $-14.78, $15.07, $639.50 |
| stock_pair_grid:JPM/BAC | $156.28, $94.66, $86.47, $-1.50, $-19.29 | $-46.78, $-30.48, $-19.29, $-1.50, $86.47 |
| stock_pair_grid:MA/V | $7.54, $-13.13, $-145.17, $-193.47 | $-193.47, $-145.17, $-13.13, $7.54 |
| stock_pair_grid:HD/LOW | $309.17, $51.96, $4.82, $-193.58, $-220.46 | $-220.46, $-193.58, $4.82, $51.96, $309.17 |
| stock_pair_grid:WMT/TGT | $229.76, $203.95, $74.19, $51.82, $5.74 | $-191.63, $-80.34, $5.74, $51.82, $74.19 |
| stock_pair_grid:UPS/FDX | $462.93, $280.01, $165.51, $148.47, $102.45 | $-350.07, $-143.15, $-97.04, $-65.82, $-40.24 |
| stock_pair_grid:COP/EOG | $542.98, $380.29, $316.36, $-2.96, $-135.46 | $-368.38, $-169.24, $-135.46, $-2.96, $316.36 |
| stock_pair_grid:MS/GS | $234.67, $-12.10, $-293.00 | $-293.00, $-12.10, $234.67 |
| stock_pair_grid:AEP/EXC | $183.63, $148.73, $78.07, $26.13, $2.57 | $-97.29, $-97.11, $2.57, $26.13, $78.07 |
| stock_pair_grid:DOW/DD | $759.43, $-7.67, $-716.60 | $-716.60, $-7.67, $759.43 |
| natural_long_grid:CSCO | $972.64, $827.66, $549.87, $339.38, $288.38 | $-1,459.05, $-10.55, $26.12, $87.90, $288.38 |
| natural_long_grid:VZ | $679.58, $597.83, $290.98, $49.21, $-12.15 | $-537.92, $-119.57, $-12.15, $49.21, $290.98 |
| natural_long_grid:MO | $384.28, $205.23, $120.21, $-9.38 | $-9.38, $120.21, $205.23, $384.28 |
| natural_long_grid:JPM | $190.07, $144.23, $78.86, $-36.40, $-2,839.14 | $-2,839.14, $-36.40, $78.86, $144.23, $190.07 |
| natural_long_grid:XOM | $2,824.00, $1,571.70, $1,424.96, $-4.42, $-207.12 | $-207.12, $-4.42, $1,424.96, $1,571.70, $2,824.00 |
| natural_long_grid:KO | $-6.26, $-909.44 | $-909.44, $-6.26 |
| natural_long_grid:PEP | $429.18, $177.18, $121.72, $-4.81 | $-4.81, $121.72, $177.18, $429.18 |
| natural_long_grid:MA | $492.11, $324.52, $-3.60, $-892.75 | $-892.75, $-3.60, $324.52, $492.11 |
| natural_long_grid:V | $451.23, $138.09, $-8.14, $-68.01 | $-68.01, $-8.14, $138.09, $451.23 |
| natural_long_grid:HD | $2,252.46, $1,491.87, $716.65, $377.86, $277.32 | $-23.05, $104.97, $277.32, $377.86, $716.65 |
| natural_long_grid:LOW | $1,791.16, $136.32, $92.82, $52.90, $40.74 | $-9,551.18, $-421.88, $-52.36, $-49.22, $-39.14 |

## Mandatory baseline comparison

| Strategy | Strategy net | Buy & hold | SPY | Naive MR | Beat all? |
| --- | --- | --- | --- | --- | --- |
| residual_grid:CSCO/XLK | 0.91% | -30.48% | -29.74% | -9.19% | YES |
| residual_grid:CSCO/QQQ | 0.26% | -30.48% | -29.74% | -3.37% | YES |
| residual_grid:VZ/XLC | 0.13% | -33.31% | -29.74% | -27.55% | YES |
| residual_grid:MO/XLP | 0.83% | -28.78% | -29.74% | -1.80% | YES |
| residual_grid:JPM/XLF | 0.50% | -35.75% | -29.74% | -4.24% | YES |
| residual_grid:XOM/XLE | -0.22% | -33.64% | -29.74% | 8.08% | NO |
| stock_pair_grid:VZ/T | 0.16% | -33.31% | -29.74% | -16.41% | YES |
| stock_pair_grid:KO/PEP | -0.38% | -37.21% | -29.74% | -0.22% | NO |
| stock_pair_grid:XOM/CVX | 0.14% | -33.64% | -29.74% | 14.30% | NO |
| stock_pair_grid:JPM/BAC | 0.24% | -35.75% | -29.74% | -2.04% | YES |
| stock_pair_grid:MA/V | -0.35% | -26.07% | -29.74% | 12.91% | NO |
| stock_pair_grid:HD/LOW | -0.06% | -33.22% | -29.74% | 6.24% | NO |
| stock_pair_grid:WMT/TGT | 0.29% | -36.64% | -29.74% | 0.82% | NO |
| stock_pair_grid:UPS/FDX | 0.61% | -28.60% | -29.74% | -10.71% | YES |
| stock_pair_grid:COP/EOG | 0.55% | -28.95% | -29.74% | 5.12% | NO |
| stock_pair_grid:MS/GS | -0.09% | -31.14% | -29.74% | -9.17% | YES |
| stock_pair_grid:AEP/EXC | 0.24% | -24.18% | -29.74% | 15.54% | NO |
| stock_pair_grid:DOW/DD | 0.03% | -38.48% | -29.74% | -2.02% | YES |
| natural_long_grid:CSCO | 1.62% | -30.48% | -29.74% | 6.75% | NO |
| natural_long_grid:VZ | 0.94% | -33.31% | -29.74% | 1.78% | NO |
| natural_long_grid:MO | 0.70% | -28.78% | -29.74% | -11.84% | YES |
| natural_long_grid:JPM | -2.47% | -35.75% | -29.74% | -5.70% | YES |
| natural_long_grid:XOM | 5.61% | -33.64% | -29.74% | -8.83% | YES |
| natural_long_grid:KO | -0.92% | -37.21% | -29.74% | -19.89% | YES |
| natural_long_grid:PEP | 0.72% | -33.19% | -29.74% | -9.86% | YES |
| natural_long_grid:MA | -0.08% | -26.07% | -29.74% | -3.00% | YES |
| natural_long_grid:V | 0.51% | -31.17% | -29.74% | -11.59% | YES |
| natural_long_grid:HD | 5.19% | -33.22% | -29.74% | -15.62% | YES |
| natural_long_grid:LOW | -8.01% | -22.83% | -29.74% | -7.72% | NO |

## Selection-bias check

| Universe | Relationships | GO | GO rate | Backtests | Avg net return | Beat-all rate |
| --- | --- | --- | --- | --- | --- | --- |
| Curated | 12 | 12 | 100.00% | 12 | 0.18% | 58.33% |
| Blind expansion | 6 | 6 | 100.00% | 6 | 0.27% | 50.00% |

## Risk, implementation, and interpretation notes

- Grid size is solved against every configured layer being filled and liquidated at the kill threshold.
- Gross, net, and realized exposures are accounted for; a hedge is not treated as risk-free.
- Commission, spread, slippage, placeholder borrow, and placeholder overnight financing are charged as configured.
- Historical hard-to-borrow status and true borrow rates are unavailable. All short-leg results are less reliable and must not be presented on equal footing with long-only results.
- AI research hooks are advisory, event-scoped, cached, and unable to override deterministic risk decisions.
- The manually curated relationships are correlated by construction. Blind-expansion results are required before generalizing.
- Any future point-in-time universe must retain delisted/acquired constituents to avoid survivorship bias.

## Warnings emitted during the run

- None.

## Reproducibility

Re-run through the CLI using the recorded configuration and data cache. Cached provider files are intentionally not committed. Reports are deterministic for a fixed dataset/configuration; synthetic demos additionally use the configured seed.
