# Phase 3A loss attribution

## Scope and evidence quality

This report replays the unchanged Phase 2D frozen engine over cached HF R-LITE bars. The source remains **LIMITED**: adjusted OHLC, IEX-only after March 2022, RTH only, survivorship-biased, and without point-in-time event history. Event effects are therefore `UNAVAILABLE`, never zero.

## Family/timeframe attribution

| attribution_dimension | strategy_family | timeframe | campaigns | trades_legs | net_pnl | average_pnl | median_pnl | win_rate | profit_factor | expectancy | max_drawdown | average_mae | average_mfe | average_cost | cost_as_pct_gross_profit | profit_concentration | loss_concentration | symbols | months | diagnostic_flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| strategy_family_timeframe | natural_long_grid | 15min | 2 | 6 | 1020.235 | 510.117 | 510.11741310626167 | 0.5 | 4.401 | 510.11741310626167 | -299.955 | -225.1916014265771 | 803.526048752281 | 33.685 | 0.051031041738893244 | 1.0 | 1.0 | 2 | 1 | TOO_SPARSE;STOP_DOMINATED |
| strategy_family_timeframe | residual_grid | 15min | 1006 | 1793 | -95107.933 | -94.541 | -61.59827754575294 | 0.31510934393638174 | 0.441 | -94.54068910209664 | -95572.111 | -199.8868033891458 | 85.34032725193318 | 99.248 | 1.329899110482088 | 0.054651972978574194 | 0.015674391943834208 | 11 | 54 | SUFFICIENT_SAMPLE;COST_DOMINATED;STOP_DOMINATED;BAD_GEOMETRY |
| strategy_family_timeframe | residual_grid | 5min | 2025 | 3765 | -155201.723 | -76.643 | -53.7504366505448 | 0.2730864197530864 | 0.313 | -76.6428260516287 | -155401.967 | -138.12828461426156 | 40.86950392958554 | 88.072 | 2.518344233494616 | 0.03237538431049461 | 0.006537860434199559 | 11 | 55 | SUFFICIENT_SAMPLE;COST_DOMINATED;STOP_DOMINATED;BAD_GEOMETRY |
| strategy_family_timeframe | stock_pair_grid | 15min | 3 | 4 | 197.697 | 65.899 | -59.346138076438784 | 0.3333333333333333 | 2.037 | 65.89896222071205 | -190.658 | -7.386574367311414 | 95.42548682541626 | 65.229 | 0.5038901181935792 | 1.0 | 0.6887305573882773 | 1 | 1 | TOO_SPARSE;COST_DOMINATED;STOP_DOMINATED;HEDGE_DRAG;BAD_GEOMETRY |
| strategy_family_timeframe | stock_pair_grid | 5min | 1 | 2 | 399.973 | 399.973 | 399.97265058376246 | 1.0 | UNAVAILABLE | 399.97265058376246 | 0.000 | -93.17993511723762 | 415.674033174786 | 115.242 | 0.28812353281038094 | 1.0 | nan | 1 | 1 | TOO_SPARSE;HEDGE_DRAG |
| separate_breakout_attribution | breakout_module | 15min | 110 | 162 | -2897.596 | -26.342 | 0.0 | 0.05454545454545454 | 0.123 | -26.34178135238834 | -2897.596 | -142.05356498223063 | -1.7717002477582768 | 80.525 | 21.82191849136126 | 0.6340738141470963 | 0.053318351791869584 | 10 | 36 | SUFFICIENT_SAMPLE;COST_DOMINATED;BAD_GEOMETRY |
| separate_breakout_attribution | breakout_module | 5min | 181 | 298 | -4073.173 | -22.504 | 0.0 | 0.06077348066298342 | 0.140 | -22.503716188600652 | -4102.467 | -138.42109098959935 | 15.950854055366253 | 76.551 | 20.94485449679698 | 0.451345038704319 | 0.13811908255056685 | 10 | 45 | SUFFICIENT_SAMPLE;COST_DOMINATED;BAD_GEOMETRY |

## Interpretation

The largest campaign-level failure class is **NO_MEAN_REVERSION**. Secondary classes are HEDGE_DRAG, STOP_TOO_TIGHT, GRID_TOO_NARROW. Flags are descriptive. `POTENTIAL_CONDITIONAL_EDGE` requires at least 30 campaigns or 100 legs, multiple symbols and months, PF > 1.15, positive expectancy, and <=25% single-campaign profit concentration.

Bucket-level details are in the five attribution CSV files. Tiny samples are labeled `UNDERPOWERED` or `TOO_SPARSE`.
