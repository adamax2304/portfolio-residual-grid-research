# Campaign replay — residual_grid:CVX:2025-06-16T14:30:00-04:00

Selection: **BIGGEST_RESIDUAL_LOSER**  
Run: `15min__residual_grid__CVX_XLE`  
Period: 2025-06-16 14:45:00-04:00 → 2025-06-17 10:00:00-04:00  
Net P&L: **$-1808.71**; stock leg $-2635.87; hedge leg $834.97  
MAE/MFE: $-1808.71 / $51.19  
Grid: 3/4 levels; step/ATR 0.243; average-entry improvement 0.0271  
TP/stop: 1.076 ATR / 0.703 ATR  
Exit: campaign maximum adverse excursion stop  
Failure classification: **NO_MEAN_REVERSION**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-06-16 14:45:00-04:00 | 141.064108 | 141.073793 | 140.93821 | 141.073793 | 6977.0 | 2.060250911170889 | 142.216561 | 139.412905 | 0.3745489492956598 | SELL CVX 244.8985@141.0077 residual grid layer 1 \| BUY XLE 305.1215@42.4394 beta hedge: residual grid layer 1 |
| 2025-06-16 15:00:00-04:00 | 141.064108 | 141.083477 | 140.783258 | 140.821996 | 4168.0 | 1.4871410900370414 | 142.216561 | 139.412905 | 0.3692396672031126 | SELL CVX 306.1231@141.0077 residual grid layer 2 \| BUY XLE 394.2625@42.4394 beta hedge: residual grid layer 2 |
| 2025-06-16 15:15:00-04:00 | 140.812312 | 141.054424 | 140.802627 | 140.98179 | 11835.0 | 1.9272941160794923 | 142.216561 | 139.412905 | 0.3608509052600339 |  |
| 2025-06-16 15:30:00-04:00 | 140.991475 | 141.102846 | 140.783258 | 141.102846 | 10277.0 | 2.1360942765410296 | 142.216561 | 139.412905 | 0.3579035548843179 |  |
| 2025-06-16 15:45:00-04:00 | 141.093162 | 141.751706 | 141.083477 | 141.509594 | 22292.0 | 2.6137793399988993 | 142.216561 | 139.412905 | 0.3800696581068684 | SELL CVX 306.0601@141.0835 residual grid layer 3 \| BUY XLE 427.9444@42.4104 beta hedge: residual grid layer 3 |
| 2025-06-17 09:45:00-04:00 | 143.570816 | 144.209985 | 143.444919 | 144.04535 | 15553.0 | 6.806487656648383 | 142.216561 | 139.412905 | 0.5458068968135203 |  |
| 2025-06-17 10:00:00-04:00 | 144.050193 | 144.248722 | 143.803241 | 143.996928 | 11703.0 | 4.607202081837036 | 144.209985 | 139.412905 | 0.5386407613268384 | BUY CVX 857.0816@144.1078 campaign maximum adverse excursion stop \| SELL XLE 1127.3285@43.1709 campaign maximum adverse excursion stop |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
