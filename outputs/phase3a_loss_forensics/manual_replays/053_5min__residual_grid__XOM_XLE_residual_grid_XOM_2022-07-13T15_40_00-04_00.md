# Campaign replay — residual_grid:XOM:2022-07-13T15:40:00-04:00

Selection: **BIGGEST_HEDGE_DRAG**  
Run: `5min__residual_grid__XOM_XLE`  
Period: 2022-07-13 15:45:00-04:00 → 2022-07-14 09:45:00-04:00  
Net P&L: **$-516.52**; stock leg $3799.09; hedge leg $-4310.20  
MAE/MFE: $-516.52 / $-71.08  
Grid: 3/4 levels; step/ATR 0.160; average-entry improvement -1.1452  
TP/stop: 0.784 ATR / 0.392 ATR  
Exit: residual kill  
Failure classification: **HEDGE_DRAG**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-07-13 15:45:00-04:00 | 74.819619 | 74.876831 | 74.784412 | 74.868029 | 13025.0 | 2.807462576674483 | 75.343326 | 73.996652 | 0.17254026728868924 | SELL XOM 521.9619@74.7897 residual grid layer 1 \| BUY XLE 1395.2626@30.3350 beta hedge: residual grid layer 1 |
| 2022-07-13 15:50:00-04:00 | 74.780011 | 74.815218 | 74.639183 | 74.758007 | 14890.0 | 2.5120776189290743 | 75.343326 | 73.996652 | 0.17656210533949745 | SELL XOM 652.7979@74.7501 residual grid layer 2 \| BUY XLE 1735.0965@30.2987 beta hedge: residual grid layer 2 |
| 2022-07-14 09:40:00-04:00 | 71.734335 | 71.892767 | 71.540696 | 71.567102 | 9181.0 | 3.044630668059975 | 75.343326 | 73.996652 | 0.39375845495810546 | SELL XOM 680.5142@71.7056 residual grid layer 3 \| BUY XLE 1787.0484@29.1409 beta hedge: residual grid layer 3 |
| 2022-07-14 09:45:00-04:00 | 71.567102 | 71.782745 | 71.338256 | 71.439476 | 10216.0 | 0.18436346526612013 | 75.343326 | 71.540696 | 0.3973820653182411 | BUY XOM 1855.2740@71.5957 residual kill \| SELL XLE 4917.4076@29.0121 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
