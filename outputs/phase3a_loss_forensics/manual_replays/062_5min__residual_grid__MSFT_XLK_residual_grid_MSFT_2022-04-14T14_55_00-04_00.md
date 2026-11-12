# Campaign replay — residual_grid:MSFT:2022-04-14T14:55:00-04:00

Selection: **HIGHEST_COST_TP_RATIO**  
Run: `5min__residual_grid__MSFT_XLK`  
Period: 2022-04-14 15:00:00-04:00 → 2022-04-14 15:10:00-04:00  
Net P&L: **$-182.85**; stock leg $-190.34; hedge leg $7.52  
MAE/MFE: $-182.85 / $-52.00  
Grid: 2/4 levels; step/ATR 0.183; average-entry improvement 0.0148  
TP/stop: 0.439 ATR / 0.899 ATR  
Exit: residual kill  
Failure classification: **NO_MEAN_REVERSION**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-04-14 15:00:00-04:00 | 272.04018 | 272.18044 | 271.822537 | 272.049853 | 13562.0 | -1.9925116684823962 | 276.069008 | 272.025671 | 0.39865875707917786 | BUY MSFT 145.9338@272.1490 residual grid layer 1 \| SELL XLK 502.2140@71.4133 beta hedge: residual grid layer 1 |
| 2022-04-14 15:05:00-04:00 | 272.045017 | 272.122401 | 271.571037 | 271.619403 | 4254.0 | -2.3810194677576884 | 276.069008 | 271.822537 | 0.4095662744306677 | BUY MSFT 182.4140@272.1224 residual grid layer 2 \| SELL XLK 611.6302@71.4138 beta hedge: residual grid layer 2 |
| 2022-04-14 15:10:00-04:00 | 271.667768 | 272.04018 | 271.542018 | 271.977306 | 10333.0 | -1.378911355614473 | 275.333856 | 271.571037 | 0.4158945405427654 | SELL MSFT 328.3478@271.5591 residual kill \| BUY XLK 1113.8442@71.4055 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
