# Campaign replay 9: residual_grid:XOM/XLE

Campaign `residual_grid:XOM:2025-03-17T00:00:00`. Behavior is shown at each available daily candle; action reasons identify every add/exit.

```text
 replay_id                   run                           campaign_id  timestamp      price        state active_grid_levels  filled_legs  average_entry  open_exposure  realized_pnl  unrealized_pnl                                            action_reason
         9 residual_grid:XOM/XLE residual_grid:XOM:2025-03-17T00:00:00 2025-03-18 113.639999  GRID_ACTIVE                  ;            2     114.044360   12732.977888      0.000000       12.600804 residual grid layer 1; beta hedge: residual grid layer 1
         9 residual_grid:XOM/XLE residual_grid:XOM:2025-03-17T00:00:00 2025-03-19 115.410004  GRID_ACTIVE                  ;            2     114.105421   29322.621245      0.000000      -93.450206 residual grid layer 2; beta hedge: residual grid layer 2
         9 residual_grid:XOM/XLE residual_grid:XOM:2025-03-17T00:00:00 2025-03-20 115.900002  GRID_ACTIVE                  ;            2     114.307877   46005.343416      0.000000     -207.036836 residual grid layer 3; beta hedge: residual grid layer 3
         9 residual_grid:XOM/XLE residual_grid:XOM:2025-03-17T00:00:00 2025-03-21 115.500000      WARNING                  ;            2     114.649258   65931.529145      0.000000     -243.371833 residual grid layer 4; beta hedge: residual grid layer 4
         9 residual_grid:XOM/XLE residual_grid:XOM:2025-03-17T00:00:00 2025-03-24 115.800003 GRID_EXITING                               0     114.649258   66124.584129      0.000000     -275.984081                                                mark only
         9 residual_grid:XOM/XLE residual_grid:XOM:2025-03-17T00:00:00 2025-03-25 116.589996    CANDIDATE                  ;            2       0.000000       0.000000   -440.846403        0.000000                   residual time stop; residual time stop
```
