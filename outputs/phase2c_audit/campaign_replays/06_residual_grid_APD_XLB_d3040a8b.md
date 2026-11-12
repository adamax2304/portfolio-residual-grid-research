# Campaign replay 6: residual_grid:APD/XLB

Campaign `residual_grid:APD:2025-10-03T00:00:00`. Behavior is shown at each available daily candle; action reasons identify every add/exit.

```text
 replay_id                   run                           campaign_id  timestamp      price        state active_grid_levels  filled_legs  average_entry  open_exposure  realized_pnl  unrealized_pnl                                            action_reason
         6 residual_grid:APD/XLB residual_grid:APD:2025-10-03T00:00:00 2025-10-06 270.950012  GRID_ACTIVE                  ;            2     271.458546   14607.114197      0.000000       -7.209874 residual grid layer 1; beta hedge: residual grid layer 1
         6 residual_grid:APD/XLB residual_grid:APD:2025-10-03T00:00:00 2025-10-07 270.890015  GRID_ACTIVE                  ;            2     270.873964   32856.688518      0.000000       80.712645 residual grid layer 2; beta hedge: residual grid layer 2
         6 residual_grid:APD/XLB residual_grid:APD:2025-10-03T00:00:00 2025-10-08 268.579987  GRID_ACTIVE                               0     270.873964   32791.931015      0.000000     -150.489667                                                mark only
         6 residual_grid:APD/XLB residual_grid:APD:2025-10-03T00:00:00 2025-10-09 262.709991  GRID_ACTIVE                  ;            2     269.929974   50349.242653      0.000000     -360.679867 residual grid layer 3; beta hedge: residual grid layer 3
         6 residual_grid:APD/XLB residual_grid:APD:2025-10-03T00:00:00 2025-10-10 257.079987 GRID_EXITING                  ;            2     267.823874   71073.470401      0.000000     -455.598901 residual grid layer 4; beta hedge: residual grid layer 4
         6 residual_grid:APD/XLB residual_grid:APD:2025-10-03T00:00:00 2025-10-13 260.859985         SCAN                  ;            2       0.000000       0.000000   -609.765477        0.000000                   residual time stop; residual time stop
```
