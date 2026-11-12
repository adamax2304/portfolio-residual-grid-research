# Campaign replay — residual_grid:CVX:2025-12-15T14:50:00-05:00

Selection: **HIGHEST_COST_TP_RATIO**  
Run: `5min__residual_grid__CVX_XLE`  
Period: 2025-12-15 14:55:00-05:00 → 2025-12-15 15:00:00-05:00  
Net P&L: **$-39.65**; stock leg $-42.66; hedge leg $3.01  
MAE/MFE: $-39.65 / $-23.80  
Grid: 1/4 levels; step/ATR 0.236; average-entry improvement -0.0000  
TP/stop: 0.685 ATR / 1.044 ATR  
Exit: residual kill  
Failure classification: **STOP_OR_EXIT_FAILURE**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-12-15 14:55:00-05:00 | 147.782971 | 147.891897 | 147.723556 | 147.891897 | 2910.0 | 1.584097633383119 | 147.891897 | 146.980879 | 0.1241806823706881 | SELL CVX 210.9528@147.7239 residual grid layer 1 \| BUY XLE 584.3277@44.4245 beta hedge: residual grid layer 1 |
| 2025-12-15 15:00:00-05:00 | 147.86219 | 147.921604 | 147.82258 | 147.872092 | 1628.0 | 1.444185672741758 | 147.891897 | 146.980879 | 0.12238377648706855 | BUY CVX 210.9528@147.9213 residual kill \| SELL XLE 584.3277@44.4314 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
