# Campaign replay — residual_grid:MSFT:2022-06-16T09:45:00-04:00

Selection: **TYPICAL_RESIDUAL_LOSER**  
Run: `5min__residual_grid__MSFT_XLK`  
Period: 2022-06-16 09:50:00-04:00 → 2022-06-16 10:00:00-04:00  
Net P&L: **$-411.36**; stock leg $-272.87; hedge leg $-138.45  
MAE/MFE: $-411.36 / $19.42  
Grid: 2/4 levels; step/ATR 0.070; average-entry improvement -0.4891  
TP/stop: 0.467 ATR / 0.045 ATR  
Exit: residual kill z  
Failure classification: **NO_MEAN_REVERSION**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-06-16 09:50:00-04:00 | 239.003566 | 239.008415 | 237.888449 | 238.140562 | 11352.0 | 1.9144659856500352 | 246.73167 | 237.723606 | 1.712036654277113 | SELL MSFT 164.8142@238.9080 residual grid layer 1 \| BUY XLK 616.1467@60.6319 beta hedge: residual grid layer 1 |
| 2022-06-16 09:55:00-04:00 | 238.062989 | 239.265376 | 238.029051 | 239.1975 | 11000.0 | 3.4452072876573645 | 246.73167 | 237.723606 | 1.6780572504001758 | SELL MSFT 206.8317@238.0291 residual grid layer 2 \| BUY XLK 737.6481@60.4839 beta hedge: residual grid layer 2 |
| 2022-06-16 10:00:00-04:00 | 239.129623 | 239.149016 | 238.286012 | 238.509036 | 11261.0 | 2.1398963141803073 | 246.73167 | 237.723606 | 1.6233023039430197 | BUY MSFT 371.6459@239.1490 residual kill z \| SELL XLK 1353.7947@60.4501 residual kill z |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
