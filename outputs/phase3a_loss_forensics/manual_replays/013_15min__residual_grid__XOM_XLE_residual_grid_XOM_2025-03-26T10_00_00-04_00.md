# Campaign replay — residual_grid:XOM:2025-03-26T10:00:00-04:00

Selection: **TYPICAL_RESIDUAL_LOSER**  
Run: `15min__residual_grid__XOM_XLE`  
Period: 2025-03-26 10:15:00-04:00 → 2025-03-26 10:30:00-04:00  
Net P&L: **$-162.58**; stock leg $-145.56; hedge leg $-16.99  
MAE/MFE: $-162.58 / $-137.68  
Grid: 1/4 levels; step/ATR 0.151; average-entry improvement -0.0000  
TP/stop: 0.758 ATR / 0.350 ATR  
Exit: residual kill z  
Failure classification: **NO_MEAN_REVERSION**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-03-26 10:15:00-04:00 | 114.526385 | 115.154801 | 114.468378 | 114.884099 | 45205.0 | 3.23927304781282 | 114.845427 | 111.007637 | 0.4183424430417462 | SELL XOM 328.6789@114.4806 residual grid layer 1 \| BUY XLE 651.0716@45.8571 beta hedge: residual grid layer 1 |
| 2025-03-26 10:30:00-04:00 | 114.874431 | 115.222477 | 114.724578 | 115.125798 | 44649.0 | 3.6864035679737115 | 115.154801 | 111.007637 | 0.4240250542530503 | BUY XOM 328.6789@114.9204 residual kill z \| SELL XLE 651.0716@45.8325 residual kill z |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
