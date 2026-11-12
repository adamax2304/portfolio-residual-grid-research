# Campaign replay — residual_grid:AAPL:2022-03-01T09:50:00-05:00

Selection: **STOPPED_THEN_REVERTED**  
Run: `5min__residual_grid__AAPL_XLK`  
Period: 2022-03-01 09:55:00-05:00 → 2022-03-01 10:00:00-05:00  
Net P&L: **$-53.61**; stock leg $-16.11; hedge leg $-37.49  
MAE/MFE: $-53.61 / $-27.26  
Grid: 1/4 levels; step/ATR 0.123; average-entry improvement -0.0000  
TP/stop: 1.256 ATR / 0.000 ATR  
Exit: residual kill z  
Failure classification: **STOP_OR_EXIT_FAILURE**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-01 09:55:00-05:00 | 165.82 | 166.04 | 165.41 | 165.73 | 1114981.0 | 3.354107415682566 | 166.51 | 162.43 | 0.6658329068897683 | SELL AAPL 241.2254@165.7537 residual grid layer 1 \| BUY XLK 422.1155@76.8607 beta hedge: residual grid layer 1 |
| 2022-03-01 10:00:00-05:00 | 165.75 | 166.34 | 165.45 | 165.6 | 1268454.0 | 3.412934974377755 | 166.51 | 162.43 | 0.6818448421119288 | BUY AAPL 241.2254@165.8163 residual kill z \| SELL XLK 422.1155@76.7743 residual kill z |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
