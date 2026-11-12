# Conditional edge search

Eligible conditional buckets: **0**. Positive but ineligible/underpowered buckets: **53**.

A bucket is eligible only with >=30 campaigns or >=100 legs, PF > 1.15, positive expectancy, <=25% profit concentration, >=2 symbols, and >=2 months. All buckets use pre-entry fields or immutable campaign mechanics; filled-level and averaging buckets are mechanics diagnostics rather than deployable entry filters.

## Eligible buckets

_No rows._

## Positive but not eligible

| strategy_family | condition | condition_bucket | campaigns | profit_factor | expectancy | diagnostic_flags |
|---|---|---|---|---|---|---|
| natural_long_grid | spy_regime | RANGE_OK | 1 | inf | 1320.1897180912201 | TOO_SPARSE |
| stock_pair_grid | spy_regime | RANGE_OK | 3 | 6.00345968091587 | 219.00522510744577 | TOO_SPARSE;HEDGE_DRAG |
| natural_long_grid | qqq_regime | RANGE_OK | 2 | 4.401294174009041 | 510.11741310626167 | TOO_SPARSE;STOP_DOMINATED |
| stock_pair_grid | qqq_regime | RANGE_OK | 3 | 6.00345968091587 | 219.00522510744577 | TOO_SPARSE;HEDGE_DRAG |
| natural_long_grid | sector_etf_regime | UNAVAILABLE | 2 | 4.401294174009041 | 510.11741310626167 | TOO_SPARSE;STOP_DOMINATED |
| stock_pair_grid | sector_etf_regime | TREND_DOWN | 1 | inf | 399.97265058376246 | TOO_SPARSE;HEDGE_DRAG |
| stock_pair_grid | sector_etf_regime | TREND_UP | 2 | 2.957494255991909 | 128.52151236928748 | TOO_SPARSE;STOP_DOMINATED;HEDGE_DRAG;BAD_GEOMETRY |
| natural_long_grid | market_regime | RANGE_OK | 2 | 4.401294174009041 | 510.11741310626167 | TOO_SPARSE;STOP_DOMINATED |
| stock_pair_grid | market_regime | RANGE_OK | 3 | 6.00345968091587 | 219.00522510744577 | TOO_SPARSE;HEDGE_DRAG |
| natural_long_grid | time_of_day_bucket | MIDDAY | 2 | 4.401294174009041 | 510.11741310626167 | TOO_SPARSE;STOP_DOMINATED |
| stock_pair_grid | time_of_day_bucket | FIRST_HOUR | 1 | inf | 388.35530008843295 | TOO_SPARSE;HEDGE_DRAG;BAD_GEOMETRY |
| stock_pair_grid | time_of_day_bucket | MIDDAY | 3 | 2.097849464893301 | 69.77141238582189 | TOO_SPARSE;COST_DOMINATED;STOP_DOMINATED;HEDGE_DRAG |
| natural_long_grid | day_of_week | Tuesday | 1 | inf | 1320.1897180912201 | TOO_SPARSE |
| stock_pair_grid | day_of_week | Wednesday | 3 | 6.00345968091587 | 219.00522510744577 | TOO_SPARSE;HEDGE_DRAG |
| natural_long_grid | breakout_flag | False | 2 | 4.401294174009041 | 510.11741310626167 | TOO_SPARSE;STOP_DOMINATED |
| stock_pair_grid | breakout_flag | False | 4 | 4.134766132295236 | 149.41738431147462 | TOO_SPARSE;STOP_DOMINATED;HEDGE_DRAG;BAD_GEOMETRY |
| natural_long_grid | enough_legs_to_average | True | 2 | 4.401294174009041 | 510.11741310626167 | TOO_SPARSE;STOP_DOMINATED |
| stock_pair_grid | enough_legs_to_average | False | 2 | 6.543901805172648 | 164.5045810059971 | TOO_SPARSE;STOP_DOMINATED;HEDGE_DRAG;BAD_GEOMETRY |
| stock_pair_grid | enough_legs_to_average | True | 2 | 3.0459654249239616 | 134.33018761695223 | TOO_SPARSE;COST_DOMINATED;STOP_DOMINATED;HEDGE_DRAG |
| natural_long_grid | entry_sweep_reclaim | False | 2 | 4.401294174009041 | 510.11741310626167 | TOO_SPARSE;STOP_DOMINATED |
| stock_pair_grid | entry_sweep_reclaim | False | 4 | 4.134766132295236 | 149.41738431147462 | TOO_SPARSE;STOP_DOMINATED;HEDGE_DRAG;BAD_GEOMETRY |
| natural_long_grid | realized_volatility | HIGH | 2 | 4.401294174009041 | 510.11741310626167 | TOO_SPARSE;STOP_DOMINATED |
| stock_pair_grid | realized_volatility | EXTREME | 2 | 2.957494255991909 | 128.52151236928748 | TOO_SPARSE;STOP_DOMINATED;HEDGE_DRAG;BAD_GEOMETRY |
| stock_pair_grid | realized_volatility | HIGH | 1 | inf | 399.97265058376246 | TOO_SPARSE;HEDGE_DRAG |
| natural_long_grid | volume_ratio | NORMAL | 2 | 4.401294174009041 | 510.11741310626167 | TOO_SPARSE;STOP_DOMINATED |
| natural_long_grid | adx | RANGE_LIMIT | 2 | 4.401294174009041 | 510.11741310626167 | TOO_SPARSE;STOP_DOMINATED |
| natural_long_grid | position_vs_swing_low | NEAR | 1 | inf | 1320.1897180912201 | TOO_SPARSE |
| natural_long_grid | distance_to_vwap_atr | BELOW_1ATR | 2 | 4.401294174009041 | 510.11741310626167 | TOO_SPARSE;STOP_DOMINATED |
| natural_long_grid | previous_1d_return | PULLBACK | 2 | 4.401294174009041 | 510.11741310626167 | TOO_SPARSE;STOP_DOMINATED |
| stock_pair_grid | previous_1d_return | UP | 1 | inf | 399.97265058376246 | TOO_SPARSE;HEDGE_DRAG |

_Showing 30 of 53 rows._

No bucket is a final strategy. Any surviving condition must be frozen in Phase 3B and tested on a separate OOS interval/source.
