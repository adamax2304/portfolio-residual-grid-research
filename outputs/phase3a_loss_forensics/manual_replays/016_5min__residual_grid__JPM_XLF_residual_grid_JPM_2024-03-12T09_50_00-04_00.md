# Campaign replay — residual_grid:JPM:2024-03-12T09:50:00-04:00

Selection: **TYPICAL_RESIDUAL_LOSER**  
Run: `5min__residual_grid__JPM_XLF`  
Period: 2024-03-12 09:55:00-04:00 → 2024-03-12 10:00:00-04:00  
Net P&L: **$-61.70**; stock leg $-118.98; hedge leg $57.29  
MAE/MFE: $-61.70 / $-36.15  
Grid: 1/4 levels; step/ATR 0.353; average-entry improvement -0.0000  
TP/stop: 0.836 ATR / 1.755 ATR  
Exit: residual kill  
Failure classification: **STOP_OR_EXIT_FAILURE**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2024-03-12 09:55:00-04:00 | 180.520525 | 181.042482 | 180.520525 | 181.013751 | 1220.0 | 0.6169051623530014 | 180.568411 | 178.699773 | 0.2360752523423597 | SELL JPM 205.3136@180.5205 residual grid layer 1 \| BUY XLF 1274.4723@39.4305 beta hedge: residual grid layer 1 |
| 2024-03-12 10:00:00-04:00 | 181.042482 | 181.095157 | 180.683338 | 180.683338 | 659.0 | 0.46084151212446883 | 181.042482 | 178.699773 | 0.2486283771750489 | BUY JPM 205.3136@181.0952 residual kill \| SELL XLF 1274.4723@39.4762 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
