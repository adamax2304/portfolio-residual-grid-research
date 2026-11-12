# Campaign replay 8: residual_grid:PEP/XLP

Campaign `residual_grid:PEP:2023-01-17T00:00:00`. Behavior is shown at each available daily candle; action reasons identify every add/exit.

```text
 replay_id                   run                           campaign_id  timestamp      price        state active_grid_levels  filled_legs  average_entry  open_exposure  realized_pnl  unrealized_pnl                                            action_reason
         8 residual_grid:PEP/XLP residual_grid:PEP:2023-01-17T00:00:00 2023-01-18 171.619995  GRID_ACTIVE                  ;            2     175.310101   14645.550441      0.000000      -83.620755 residual grid layer 1; beta hedge: residual grid layer 1
         8 residual_grid:PEP/XLP residual_grid:PEP:2023-01-17T00:00:00 2023-01-19 169.630005  GRID_ACTIVE                  ;            2     173.086889   32871.389081      0.000000     -241.420246 residual grid layer 2; beta hedge: residual grid layer 2
         8 residual_grid:PEP/XLP residual_grid:PEP:2023-01-17T00:00:00 2023-01-20 169.880005  GRID_ACTIVE                  ;            2     171.611261   51579.412985      0.000000     -277.665741 residual grid layer 3; beta hedge: residual grid layer 3
         8 residual_grid:PEP/XLP residual_grid:PEP:2023-01-17T00:00:00 2023-01-23 169.119995      WARNING                  ;            2     171.148387   73880.790857      0.000000     -581.937560 residual grid layer 4; beta hedge: residual grid layer 4
         8 residual_grid:PEP/XLP residual_grid:PEP:2023-01-17T00:00:00 2023-01-24 170.690002 GRID_EXITING                               0     171.148387   74437.612983      0.000000     -230.876197                                                mark only
         8 residual_grid:PEP/XLP residual_grid:PEP:2023-01-17T00:00:00 2023-01-25 171.929993    CANDIDATE                  ;            2       0.000000       0.000000   -211.858375        0.000000                   residual time stop; residual time stop
```
