# Campaign replay — residual_grid:PFE:2025-11-28T10:00:00-05:00

Selection: **TYPICAL_RESIDUAL_LOSER**  
Run: `15min__residual_grid__PFE_XLV`  
Period: 2025-11-28 10:15:00-05:00 → 2025-11-28 10:45:00-05:00  
Net P&L: **$-43.05**; stock leg $-13.54; hedge leg $-29.40  
MAE/MFE: $-43.05 / $8.14  
Grid: 2/4 levels; step/ATR 0.561; average-entry improvement 0.0407  
TP/stop: 3.233 ATR / 0.878 ATR  
Exit: residual kill  
Failure classification: **STOP_OR_EXIT_FAILURE**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-11-28 10:15:00-05:00 | 25.335082 | 25.389175 | 25.325247 | 25.384258 | 49804.0 | 2.467825951501934 | 25.541452 | 24.812975 | 0.05295305189268654 | SELL PFE 1525.6034@25.3252 residual grid layer 1 \| BUY XLV 170.9778@156.0992 beta hedge: residual grid layer 1 |
| 2025-11-28 10:30:00-05:00 | 25.408845 | 25.408845 | 25.344918 | 25.35967 | 78546.0 | 2.2649649808029806 | 25.541452 | 24.812975 | 0.05373690532892319 | SELL PFE 1901.4682@25.3987 residual grid layer 2 \| BUY XLV 212.6396@156.5060 beta hedge: residual grid layer 2 |
| 2025-11-28 10:45:00-05:00 | 25.35967 | 25.369505 | 25.344918 | 25.35967 | 101364.0 | 2.2857283510776436 | 25.541452 | 24.812975 | 0.051654769234000135 | BUY PFE 3427.0716@25.3695 residual kill \| SELL XLV 383.6174@156.2520 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
