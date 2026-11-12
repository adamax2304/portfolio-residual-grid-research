# Campaign replay 5: stock_pair_grid:MA/V

Campaign `stock_pair_grid:MA-V:2025-08-15T00:00:00`. Behavior is shown at each available daily candle; action reasons identify every add/exit.

```text
 replay_id                  run                              campaign_id  timestamp      price        state active_grid_levels  filled_legs  average_entry  open_exposure  realized_pnl  unrealized_pnl                               action_reason
         5 stock_pair_grid:MA/V stock_pair_grid:MA-V:2025-08-15T00:00:00 2025-08-18 584.140015  GRID_ACTIVE                  ;            2     581.787212   14529.917884      0.000000      -56.513409 pair grid layer 1; hedge: pair grid layer 1
         5 stock_pair_grid:MA/V stock_pair_grid:MA-V:2025-08-15T00:00:00 2025-08-19 585.510010  GRID_ACTIVE                  ;            2     583.136282   32429.178173      0.000000     -114.217367 pair grid layer 2; hedge: pair grid layer 2
         5 stock_pair_grid:MA/V stock_pair_grid:MA-V:2025-08-15T00:00:00 2025-08-20 592.679993  GRID_ACTIVE                  ;            2     584.124094   50464.558199      0.000000     -469.515647 pair grid layer 3; hedge: pair grid layer 3
         5 stock_pair_grid:MA/V stock_pair_grid:MA-V:2025-08-15T00:00:00 2025-08-21 591.919983  GRID_ACTIVE                  ;            2     585.520177   71225.390826      0.000000     -501.451047 pair grid layer 4; hedge: pair grid layer 4
         5 stock_pair_grid:MA/V stock_pair_grid:MA-V:2025-08-15T00:00:00 2025-08-22 598.960022 GRID_EXITING                               0     585.520177   72219.545263      0.000000     -670.213249                                   mark only
         5 stock_pair_grid:MA/V stock_pair_grid:MA-V:2025-08-15T00:00:00 2025-08-25 593.210022    CANDIDATE                  ;            2       0.000000       0.000000   -633.842767        0.000000              pair time stop; pair time stop
```
