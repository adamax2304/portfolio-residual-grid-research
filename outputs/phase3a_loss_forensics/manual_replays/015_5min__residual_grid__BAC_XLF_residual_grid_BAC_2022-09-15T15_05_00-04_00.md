# Campaign replay — residual_grid:BAC:2022-09-15T15:05:00-04:00

Selection: **TYPICAL_RESIDUAL_LOSER**  
Run: `5min__residual_grid__BAC_XLF`  
Period: 2022-09-15 15:10:00-04:00 → 2022-09-15 15:35:00-04:00  
Net P&L: **$-84.80**; stock leg $235.61; hedge leg $-320.30  
MAE/MFE: $-92.13 / $-45.83  
Grid: 2/4 levels; step/ATR 0.281; average-entry improvement -0.0203  
TP/stop: 1.343 ATR / 0.719 ATR  
Exit: residual kill  
Failure classification: **HEDGE_DRAG**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-09-15 15:10:00-04:00 | 31.601846 | 31.606414 | 31.537893 | 31.560733 | 28156.0 | 2.359059926650726 | 31.880497 | 31.282081 | 0.06633666868337695 | SELL BAC 1211.3358@31.5892 residual grid layer 1 \| BUY XLF 1726.0261@31.3384 beta hedge: residual grid layer 1 |
| 2022-09-15 15:15:00-04:00 | 31.565301 | 31.569869 | 31.492212 | 31.501348 | 22098.0 | 1.88957635224033 | 31.880497 | 31.282081 | 0.06714526377742161 | SELL BAC 1515.9227@31.5527 residual grid layer 2 \| BUY XLF 2145.1414@31.3009 beta hedge: residual grid layer 2 |
| 2022-09-15 15:20:00-04:00 | 31.505916 | 31.551597 | 31.47394 | 31.551597 | 20058.0 | 1.9339977884099695 | 31.880497 | 31.282081 | 0.0678961020790345 |  |
| 2022-09-15 15:25:00-04:00 | 31.547029 | 31.565301 | 31.483076 | 31.501348 | 16837.0 | 1.5879991120690469 | 31.880497 | 31.282081 | 0.06891959478767498 |  |
| 2022-09-15 15:30:00-04:00 | 31.501348 | 31.542461 | 31.469372 | 31.469372 | 20979.0 | 1.0909424623491835 | 31.880497 | 31.282081 | 0.06921740944569817 |  |
| 2022-09-15 15:35:00-04:00 | 31.469372 | 31.515052 | 31.464804 | 31.487644 | 25679.0 | 0.6302361247511077 | 31.880497 | 31.282081 | 0.06786245162814829 | BUY BAC 2727.2585@31.4820 residual kill \| SELL XLF 3871.1675@31.2353 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
