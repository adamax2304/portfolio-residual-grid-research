# Campaign replay 1: stock_pair_grid:WFC/MS

Campaign `stock_pair_grid:WFC-MS:2022-10-21T00:00:00`. Behavior is shown at each available daily candle; action reasons identify every add/exit.

```text
 replay_id                    run                                campaign_id  timestamp     price       state active_grid_levels  filled_legs  average_entry  open_exposure  realized_pnl  unrealized_pnl                               action_reason
         1 stock_pair_grid:WFC/MS stock_pair_grid:WFC-MS:2022-10-21T00:00:00 2022-10-24 45.200001 GRID_ACTIVE                  ;            2      44.932021   10932.397264      0.000000      -48.801977 pair grid layer 1; hedge: pair grid layer 1
         1 stock_pair_grid:WFC/MS stock_pair_grid:WFC-MS:2022-10-21T00:00:00 2022-10-25 45.369999 GRID_ACTIVE                  ;            2      44.837454   24636.935928      0.000000      -39.668643 pair grid layer 2; hedge: pair grid layer 2
         1 stock_pair_grid:WFC/MS stock_pair_grid:WFC-MS:2022-10-21T00:00:00 2022-10-26 45.700001 GRID_ACTIVE                  ;            2      45.121423   38002.810399      0.000000     -112.966510 pair grid layer 3; hedge: pair grid layer 3
         1 stock_pair_grid:WFC/MS stock_pair_grid:WFC-MS:2022-10-21T00:00:00 2022-10-27 45.650002 GRID_ACTIVE                  ;            2      45.381917   53408.308806      0.000000     -118.519249 pair grid layer 4; hedge: pair grid layer 4
         1 stock_pair_grid:WFC/MS stock_pair_grid:WFC-MS:2022-10-21T00:00:00 2022-10-28 46.349998        KILL                               0      45.381917   54290.761617      0.000000     -337.220072                                   mark only
         1 stock_pair_grid:WFC/MS stock_pair_grid:WFC-MS:2022-10-21T00:00:00 2022-10-31 45.990002    COOLDOWN                  ;            2       0.000000       0.000000   -292.269875        0.000000                        pair kill; pair kill
```
