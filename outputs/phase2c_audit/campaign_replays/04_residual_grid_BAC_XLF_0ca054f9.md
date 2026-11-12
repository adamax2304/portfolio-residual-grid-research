# Campaign replay 4: residual_grid:BAC/XLF

Campaign `residual_grid:BAC:2021-09-24T00:00:00`. Behavior is shown at each available daily candle; action reasons identify every add/exit.

```text
 replay_id                   run                           campaign_id  timestamp     price           state active_grid_levels  filled_legs  average_entry  open_exposure  realized_pnl  unrealized_pnl                                                        action_reason
         4 residual_grid:BAC/XLF residual_grid:BAC:2021-09-24T00:00:00 2021-09-27 43.259998     GRID_ACTIVE                  ;            2      42.662928   21965.535738      0.000000      -78.785189             residual grid layer 1; beta hedge: residual grid layer 1
         4 residual_grid:BAC/XLF residual_grid:BAC:2021-09-24T00:00:00 2021-09-28 43.160000     GRID_ACTIVE                  ;            2      43.076201   49102.760737      0.000000     -459.354217             residual grid layer 2; beta hedge: residual grid layer 2
         4 residual_grid:BAC/XLF residual_grid:BAC:2021-09-24T00:00:00 2021-09-29 43.070000     GRID_ACTIVE                  ;            2      43.107064   77208.062784      0.000000     -413.208499             residual grid layer 3; beta hedge: residual grid layer 3
         4 residual_grid:BAC/XLF residual_grid:BAC:2021-09-24T00:00:00 2021-09-30 42.450001  BREAKOUT_SETUP                  ;            2      43.174495  109733.830470      0.000000     -789.718257             residual grid layer 4; beta hedge: residual grid layer 4
         4 residual_grid:BAC/XLF residual_grid:BAC:2021-09-24T00:00:00 2021-10-01 43.080002 BREAKOUT_ACTIVE                  ;            2       0.000000       0.000000   -698.136472        0.000000 convert residual grid to breakout; convert residual grid to breakout
```
