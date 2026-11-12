# Campaign replay — residual_grid:CSCO:2022-03-02T10:15:00-05:00

Selection: **STOPPED_THEN_REVERTED**  
Run: `15min__residual_grid__CSCO_XLK`  
Period: 2022-03-02 10:30:00-05:00 → 2022-03-02 12:00:00-05:00  
Net P&L: **$145.51**; stock leg $-255.11; hedge leg $400.88  
MAE/MFE: $-114.68 / $207.11  
Grid: 2/4 levels; step/ATR 0.412; average-entry improvement 0.0444  
TP/stop: 1.599 ATR / 1.421 ATR  
Exit: residual kill  
Failure classification: **WINNING_CAMPAIGN**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-02 10:30:00-05:00 | 55.72 | 55.93 | 55.61 | 55.79 | 476210.0 | 2.0125211990979537 | 56.08 | 54.26 | 0.32007616282745016 | SELL CSCO 450.7137@55.6977 residual grid layer 1 \| BUY XLK 368.7550@76.2605 beta hedge: residual grid layer 1 |
| 2022-03-02 10:45:00-05:00 | 55.8 | 55.84 | 55.54 | 55.67 | 338918.0 | 1.9938744179303771 | 56.08 | 54.26 | 0.31864215119691836 | SELL CSCO 562.5844@55.7777 residual grid layer 2 \| BUY XLK 454.6394@76.3150 beta hedge: residual grid layer 2 |
| 2022-03-02 11:00:00-05:00 | 55.67 | 56.08 | 55.53 | 56.07 | 654717.0 | 1.5170212530636213 | 56.08 | 54.26 | 0.3351677118257097 |  |
| 2022-03-02 11:15:00-05:00 | 56.07 | 56.11 | 55.83 | 55.91 | 458802.0 | 1.2609061095454281 | 56.08 | 54.26 | 0.33122716098101623 |  |
| 2022-03-02 11:30:00-05:00 | 55.91 | 56.04 | 55.86 | 55.92 | 517031.0 | 1.348806269938475 | 56.11 | 54.26 | 0.32042522091094366 |  |
| 2022-03-02 11:45:00-05:00 | 55.91 | 56.02 | 55.89 | 55.97 | 189862.0 | 1.1738489284891673 | 56.11 | 54.26 | 0.306823419417305 |  |
| 2022-03-02 12:00:00-05:00 | 55.97 | 56.08 | 55.9 | 56.07 | 382551.0 | 0.9074353886652248 | 56.11 | 54.26 | 0.29776460374464037 | BUY CSCO 1013.2982@55.9924 residual kill \| SELL XLK 823.3944@76.7793 residual kill |

## Interpretation

Observed campaign is profitable; it is included as a comparison case, not as evidence of a stable edge.
