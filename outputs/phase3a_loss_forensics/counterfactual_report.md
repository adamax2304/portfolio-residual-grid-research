# Counterfactual failure modes

| primary_failure_mode | campaigns | net_pnl |
|---|---|---|
| NO_MEAN_REVERSION | 846 | -229134.69981529377 |
| HEDGE_DRAG | 536 | -81823.8969649797 |
| STOP_TOO_TIGHT | 551 | -61338.30514465329 |
| GRID_TOO_NARROW | 57 | -8680.191733113015 |
| COST_DOMINATED | 52 | -7070.07633653766 |
| TOO_FEW_LEVELS | 105 | -5359.873358349559 |
| TREND_CONTINUATION_AGAINST_GRID | 4 | -1223.9999425801293 |
| EXIT_TOO_LATE | 8 | -1149.100616789004 |
| ENTRY_BAD_LEVEL | 5 | -915.3292342208258 |

Each losing campaign receives one primary failure mode via a fixed, documented hierarchy. Boolean `would_*_help` fields are causal-path plausibility checks, not rerun P&L. They ignore portfolio opportunity cost and interactions unless an exact observed leg decomposition exists. They must not be used to select production parameters.
