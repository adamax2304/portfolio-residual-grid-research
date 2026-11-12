# Campaign replay 2: stock_pair_grid:WFC/GS

Campaign `stock_pair_grid:WFC-GS:2025-06-12T00:00:00`. Behavior is shown at each available daily candle; action reasons identify every add/exit.

```text
 replay_id                    run                                campaign_id  timestamp     price        state active_grid_levels  filled_legs  average_entry  open_exposure  realized_pnl  unrealized_pnl                               action_reason
         2 stock_pair_grid:WFC/GS stock_pair_grid:WFC-GS:2025-06-12T00:00:00 2025-06-13 72.360001  GRID_ACTIVE                  ;            2      72.949166   16918.217466      0.000000      -48.898259 pair grid layer 1; hedge: pair grid layer 1
         2 stock_pair_grid:WFC/GS stock_pair_grid:WFC-GS:2025-06-12T00:00:00 2025-06-16 73.150002  GRID_ACTIVE                  ;            2      73.215163   38407.353516      0.000000     -302.650480 pair grid layer 2; hedge: pair grid layer 2
         2 stock_pair_grid:WFC/GS stock_pair_grid:WFC-GS:2025-06-12T00:00:00 2025-06-17 72.500000  GRID_ACTIVE                  ;            2      73.069626   59065.060967      0.000000     -457.879596 pair grid layer 3; hedge: pair grid layer 3
         2 stock_pair_grid:WFC/GS stock_pair_grid:WFC-GS:2025-06-12T00:00:00 2025-06-18 74.739998  GRID_ACTIVE                  ;            2      72.952016   86071.979909      0.000000      331.248928 pair grid layer 4; hedge: pair grid layer 4
         2 stock_pair_grid:WFC/GS stock_pair_grid:WFC-GS:2025-06-12T00:00:00 2025-06-20 75.400002 GRID_EXITING                               0      72.952016   86829.126127      0.000000      432.222758                                   mark only
         2 stock_pair_grid:WFC/GS stock_pair_grid:WFC-GS:2025-06-12T00:00:00 2025-06-23 77.010002    CANDIDATE                  ;            2       0.000000       0.000000    311.942846        0.000000              pair time stop; pair time stop
```
