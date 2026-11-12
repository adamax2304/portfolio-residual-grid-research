# Campaign replay — residual_grid:KO:2022-03-02T12:15:00-05:00

Selection: **STOPPED_THEN_REVERTED**  
Run: `15min__residual_grid__KO_XLP`  
Period: 2022-03-02 12:30:00-05:00 → 2022-03-02 13:45:00-05:00  
Net P&L: **$58.60**; stock leg $310.03; hedge leg $-250.90  
MAE/MFE: $-173.41 / $156.44  
Grid: 3/4 levels; step/ATR 0.168; average-entry improvement 0.0197  
TP/stop: 1.071 ATR / 0.161 ATR  
Exit: residual kill  
Failure classification: **WINNING_CAMPAIGN**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-02 12:30:00-05:00 | 62.61 | 62.71 | 62.6 | 62.63 | 337458.0 | -2.8206992213192215 | 62.88 | 61.45 | 0.22268012716832875 | BUY KO 638.8756@62.6350 residual grid layer 1 \| SELL XLP 598.1959@75.4500 beta hedge: residual grid layer 1 |
| 2022-03-02 12:45:00-05:00 | 62.63 | 62.63 | 62.5 | 62.57 | 323989.0 | -2.98598906457783 | 62.88 | 61.45 | 0.2160601180848769 | BUY KO 798.3395@62.6300 residual grid layer 2 \| SELL XLP 740.7935@75.4598 beta hedge: residual grid layer 2 |
| 2022-03-02 13:00:00-05:00 | 62.56 | 62.66 | 62.52 | 62.53 | 316844.0 | -2.8765303319140703 | 62.88 | 61.45 | 0.21062725250738523 | BUY KO 799.2327@62.5850 residual grid layer 3 \| SELL XLP 730.0077@75.4398 beta hedge: residual grid layer 3 |
| 2022-03-02 13:15:00-05:00 | 62.53 | 62.68 | 62.52 | 62.66 | 279125.0 | -1.9654755839507132 | 62.88 | 61.45 | 0.2070110201854289 |  |
| 2022-03-02 13:30:00-05:00 | 62.65 | 62.82 | 62.62 | 62.77 | 415912.0 | -1.5792326365145373 | 62.88 | 61.45 | 0.20651023302932706 |  |
| 2022-03-02 13:45:00-05:00 | 62.78 | 62.83 | 62.74 | 62.78 | 205006.0 | -1.319584809394925 | 62.88 | 61.45 | 0.19818807352723203 | SELL KO 2236.4478@62.7549 residual kill \| BUY XLP 2068.9972@75.5702 residual kill |

## Interpretation

Observed campaign is profitable; it is included as a comparison case, not as evidence of a stable edge.
