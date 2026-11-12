# Campaign replay 3: stock_pair_grid:PEP/PG

Campaign `stock_pair_grid:PEP-PG:2022-05-11T00:00:00`. Behavior is shown at each available daily candle; action reasons identify every add/exit.

```text
 replay_id                    run                                campaign_id  timestamp      price        state active_grid_levels  filled_legs  average_entry  open_exposure  realized_pnl  unrealized_pnl                               action_reason
         3 stock_pair_grid:PEP/PG stock_pair_grid:PEP-PG:2022-05-11T00:00:00 2022-05-12 170.399994  GRID_ACTIVE                  ;            2     171.181500   26572.588337      0.000000      -75.177462 pair grid layer 1; hedge: pair grid layer 1
         3 stock_pair_grid:PEP/PG stock_pair_grid:PEP-PG:2022-05-11T00:00:00 2022-05-13 173.720001  GRID_ACTIVE                  ;            2     170.875628   60760.036863      0.000000     -398.648726 pair grid layer 2; hedge: pair grid layer 2
         3 stock_pair_grid:PEP/PG stock_pair_grid:PEP-PG:2022-05-11T00:00:00 2022-05-16 175.470001  GRID_ACTIVE                  ;            2     171.852925   94966.558564      0.000000     -429.666326 pair grid layer 3; hedge: pair grid layer 3
         3 stock_pair_grid:PEP/PG stock_pair_grid:PEP-PG:2022-05-11T00:00:00 2022-05-17 174.460007  GRID_ACTIVE                  ;            2     172.855182  134397.792556      0.000000     -257.531839 pair grid layer 4; hedge: pair grid layer 4
         3 stock_pair_grid:PEP/PG stock_pair_grid:PEP-PG:2022-05-11T00:00:00 2022-05-18 163.649994 GRID_EXITING                               0     172.855182  126046.403384      0.000000     -136.604230                                   mark only
         3 stock_pair_grid:PEP/PG stock_pair_grid:PEP-PG:2022-05-11T00:00:00 2022-05-19 161.199997    CANDIDATE                  ;            2       0.000000       0.000000   -432.740182        0.000000              pair time stop; pair time stop
```
