# Campaign replay — residual_grid:XOM:2024-10-10T15:35:00-04:00

Selection: **HIGHEST_COST_TP_RATIO, TYPICAL_RESIDUAL_LOSER**  
Run: `5min__residual_grid__XOM_XLE`  
Period: 2024-10-10 15:40:00-04:00 → 2024-10-11 09:55:00-04:00  
Net P&L: **$-0.05**; stock leg $15.01; hedge leg $-12.93  
MAE/MFE: $-15.32 / $8.17  
Grid: 1/4 levels; step/ATR 0.191; average-entry improvement -0.0000  
TP/stop: 0.452 ATR / 0.947 ATR  
Exit: residual TP3  
Failure classification: **HEDGE_DRAG**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2024-10-10 15:40:00-04:00 | 117.306511 | 117.320763 | 117.263754 | 117.292259 | 4243.0 | 0.8691624103876419 | 117.534549 | 116.669905 | 0.10984729678292675 | SELL XOM 292.4546@117.2638 residual grid layer 1 \| BUY XLE 754.6401@44.0978 beta hedge: residual grid layer 1 |
| 2024-10-10 15:45:00-04:00 | 117.287508 | 117.320763 | 117.201994 | 117.201994 | 4199.0 | 1.052366480475838 | 117.534549 | 116.669905 | 0.110484561298432 |  |
| 2024-10-10 15:50:00-04:00 | 117.230498 | 117.287508 | 117.102227 | 117.268505 | 6740.0 | 0.3425211750534848 | 117.534549 | 116.669905 | 0.11582716406282995 |  |
| 2024-10-11 09:40:00-04:00 | 117.02889 | 117.171411 | 116.848363 | 117.171411 | 3400.0 | -0.33685626356445786 | 117.534549 | 116.669905 | 0.137563938058342 | BUY XOM 97.4849@117.0757 residual TP1 \| SELL XLE 251.5467@44.0182 residual TP1 |
| 2024-10-11 09:45:00-04:00 | 117.180912 | 117.22842 | 116.986134 | 117.009887 | 3631.0 | 0.04071552584431589 | 117.534549 | 116.669905 | 0.1450440853398885 | BUY XOM 97.4849@117.2278 residual TP2 \| SELL XLE 251.5467@44.0849 residual TP2 |
| 2024-10-11 09:50:00-04:00 | 116.986134 | 117.347187 | 116.981383 | 117.275927 | 1692.0 | -1.4146039532280519 | 117.534549 | 116.669905 | 0.1608126506727544 |  |
| 2024-10-11 09:55:00-04:00 | 117.266425 | 117.370941 | 117.171411 | 117.370941 | 3928.0 | 0.03623272258938004 | 117.534549 | 116.669905 | 0.16357817562470023 | BUY XOM 97.4849@117.3133 residual TP3 \| SELL XLE 251.5467@44.1469 residual TP3 |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
