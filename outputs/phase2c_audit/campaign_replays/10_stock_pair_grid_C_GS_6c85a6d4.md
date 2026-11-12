# Campaign replay 10: stock_pair_grid:C/GS

Campaign `stock_pair_grid:C-GS:2022-10-28T00:00:00`. Behavior is shown at each available daily candle; action reasons identify every add/exit.

```text
 replay_id                  run                              campaign_id  timestamp     price       state active_grid_levels  filled_legs  average_entry  open_exposure  realized_pnl  unrealized_pnl                                                                    action_reason
        10 stock_pair_grid:C/GS stock_pair_grid:C-GS:2022-10-28T00:00:00 2022-10-31 45.860001 GRID_ACTIVE                  ;            2      45.728283   17157.734542      0.000000      -84.826355                                      pair grid layer 1; hedge: pair grid layer 1
        10 stock_pair_grid:C/GS stock_pair_grid:C-GS:2022-10-28T00:00:00 2022-11-01 46.220001 GRID_ACTIVE                  ;            2      46.054322   38435.705437      0.000000     -294.874556                                      pair grid layer 2; hedge: pair grid layer 2
        10 stock_pair_grid:C/GS stock_pair_grid:C-GS:2022-10-28T00:00:00 2022-11-02 45.549999 GRID_ACTIVE                  ;            2      46.087896   58865.231108      0.000000     -795.498833                                      pair grid layer 3; hedge: pair grid layer 3
        10 stock_pair_grid:C/GS stock_pair_grid:C-GS:2022-10-28T00:00:00 2022-11-03 44.580002        KILL                  ;            2      45.811122   82397.659657      0.000000    -1420.418231                                      pair grid layer 4; hedge: pair grid layer 4
        10 stock_pair_grid:C/GS stock_pair_grid:C-GS:2022-10-28T00:00:00 2022-11-04 45.130001    COOLDOWN                  ;            2       0.000000       0.000000  -2141.135138        0.000000 campaign maximum adverse excursion stop; campaign maximum adverse excursion stop
```
