# Campaign replay 7: residual_grid:MRK/XLV

Campaign `residual_grid:MRK:2023-07-12T00:00:00`. Behavior is shown at each available daily candle; action reasons identify every add/exit.

```text
 replay_id                   run                           campaign_id  timestamp      price       state active_grid_levels  filled_legs  average_entry  open_exposure  realized_pnl  unrealized_pnl                                            action_reason
         7 residual_grid:MRK/XLV residual_grid:MRK:2023-07-12T00:00:00 2023-07-13 106.320000 GRID_ACTIVE                  ;            2     107.372934   16872.562699      0.000000      -60.708245 residual grid layer 1; beta hedge: residual grid layer 1
         7 residual_grid:MRK/XLV residual_grid:MRK:2023-07-12T00:00:00 2023-07-14 107.339996 GRID_ACTIVE                  ;            2     106.775605   39031.204829      0.000000     -121.708462 residual grid layer 2; beta hedge: residual grid layer 2
         7 residual_grid:MRK/XLV residual_grid:MRK:2023-07-12T00:00:00 2023-07-17 105.570000 GRID_ACTIVE                  ;            2     106.885121   60913.480493      0.000000     -435.581969 residual grid layer 3; beta hedge: residual grid layer 3
         7 residual_grid:MRK/XLV residual_grid:MRK:2023-07-12T00:00:00 2023-07-18 105.949997        KILL                  ;            2     106.594457   88066.066668      0.000000     -696.595506 residual grid layer 4; beta hedge: residual grid layer 4
         7 residual_grid:MRK/XLV residual_grid:MRK:2023-07-12T00:00:00 2023-07-19 105.949997    COOLDOWN                  ;            2       0.000000       0.000000   -897.880861        0.000000                             residual kill; residual kill
```
