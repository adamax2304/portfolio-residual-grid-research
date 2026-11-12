# Phase 3B signal-density report

Counts compare the exact legacy intraday-20-bar liquidity measure with corrected prior-session ADV on the same prepared bars. Final campaigns are state-machine outcomes and therefore need not equal raw signal-bar counts.

| strategy_family | legacy_intraday_liquidity_valid_bars | corrected_adv_liquidity_valid_bars | campaigns_before | campaigns_after |
|---|---|---|---|---|
| natural_long_grid | 6602 | 139687 | 2 | 64 |
| residual_grid | 1019 | 16214 | 3031 | 2945 |
| stock_pair_grid | 323 | 30699 | 4 | 355 |

| strategy_family | stage | before_legacy | after_corrected_adv | absolute_change |
|---|---|---|---|---|
| natural_long_grid | AFTER_COST_TP | 139.0000 | 743.0000 | 604.0000 |
| natural_long_grid | AFTER_DATA_SESSION | 1,372,809.0000 | 1,372,809.0000 | 0.0000 |
| natural_long_grid | AFTER_EVENT_FILTER_UNAVAILABLE | 1,797.0000 | 35,130.0000 | 33,333.0000 |
| natural_long_grid | AFTER_GRID_GEOMETRY | 139.0000 | 743.0000 | 604.0000 |
| natural_long_grid | AFTER_LIQUIDITY | 6,602.0000 | 139,687.0000 | 133,085.0000 |
| natural_long_grid | AFTER_MARKET_REGIME | 339,599.0000 | 339,599.0000 | 0.0000 |
| natural_long_grid | AFTER_RANGE | 682,381.0000 | 682,381.0000 | 0.0000 |
| natural_long_grid | AFTER_SUPPORT_PROXIMITY | 1,797.0000 | 35,130.0000 | 33,333.0000 |
| natural_long_grid | AFTER_TREND | 379,773.0000 | 379,773.0000 | 0.0000 |
| natural_long_grid | AFTER_VOLATILITY | 346,986.0000 | 346,986.0000 | 0.0000 |
| natural_long_grid | FINAL_ARMED_SIGNALS | 133.0000 | 80.0000 | -53.0000 |
| natural_long_grid | FINAL_CAMPAIGNS | 2.0000 | 64.0000 | 62.0000 |
| natural_long_grid | TOTAL_CANDLES | 1,374,129.0000 | 1,374,129.0000 | 0.0000 |
| residual_grid | AFTER_DATA_SESSION | 1,363,707.0000 | 1,363,707.0000 | 0.0000 |
| residual_grid | AFTER_LIQUIDITY | 1,019.0000 | 16,214.0000 | 15,195.0000 |
| residual_grid | ENTRY_SIGNAL_BARS | 1,019.0000 | 16,214.0000 | 15,195.0000 |
| residual_grid | FINAL_CAMPAIGNS | 3,031.0000 | 2,945.0000 | -86.0000 |
| residual_grid | PAIR_OR_RELATION_CANDIDATES | 113,266.0000 | 113,266.0000 | 0.0000 |
| residual_grid | REGIME_VALID | 40,112.0000 | 40,112.0000 | 0.0000 |
| residual_grid | SPREAD_OR_Z_VALID | 1,019.0000 | 16,214.0000 | 15,195.0000 |
| residual_grid | TOTAL_CANDLES | 1,367,007.0000 | 1,367,007.0000 | 0.0000 |
| stock_pair_grid | AFTER_DATA_SESSION | 870,062.0000 | 870,062.0000 | 0.0000 |
| stock_pair_grid | AFTER_LIQUIDITY | 323.0000 | 30,699.0000 | 30,376.0000 |
| stock_pair_grid | ENTRY_SIGNAL_BARS | 51.0000 | 4,629.0000 | 4,578.0000 |
| stock_pair_grid | FINAL_CAMPAIGNS | 4.0000 | 355.0000 | 351.0000 |
| stock_pair_grid | PAIR_OR_RELATION_CANDIDATES | 257,940.0000 | 257,940.0000 | 0.0000 |
| stock_pair_grid | REGIME_VALID | 109,162.0000 | 109,162.0000 | 0.0000 |
| stock_pair_grid | SPREAD_OR_Z_VALID | 51.0000 | 4,629.0000 | 4,578.0000 |
| stock_pair_grid | TOTAL_CANDLES | 872,162.0000 | 872,162.0000 | 0.0000 |
