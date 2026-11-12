# Phase 3B liquidity-gate fix

## Result

The unit mismatch is fixed. The gate now uses `rolling_mean(prior daily close × prior daily volume, 20 completed sessions)`; the result is lagged one full session and held constant across the next session. Current-day intraday volume cannot affect eligibility. Missing volume fails closed and early closes use their actual completed-session volume. Legacy configs without the new basis flag retain the old calculation, preserving Phase 2D/3A reproducibility.

| strategy_family | legacy_intraday_liquidity_valid_bars | corrected_adv_liquidity_valid_bars | campaigns_before | campaigns_after |
|---|---|---|---|---|
| natural_long_grid | 6602 | 139687 | 2 | 64 |
| residual_grid | 1019 | 16214 | 3031 | 2945 |
| stock_pair_grid | 323 | 30699 | 4 | 355 |

The before/after campaign count is descriptive because the corrected gate changes the state path; it is not a causal P&L claim.
