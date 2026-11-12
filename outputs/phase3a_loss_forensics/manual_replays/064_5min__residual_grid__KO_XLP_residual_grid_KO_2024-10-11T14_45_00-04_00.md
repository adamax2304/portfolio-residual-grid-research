# Campaign replay — residual_grid:KO:2024-10-11T14:45:00-04:00

Selection: **HIGHEST_COST_TP_RATIO**  
Run: `5min__residual_grid__KO_XLP`  
Period: 2024-10-11 14:50:00-04:00 → 2024-10-11 15:15:00-04:00  
Net P&L: **$-84.27**; stock leg $-85.28; hedge leg $1.07  
MAE/MFE: $-84.27 / $-11.16  
Grid: 2/4 levels; step/ATR 0.348; average-entry improvement 0.0399  
TP/stop: 0.817 ATR / 1.738 ATR  
Exit: residual kill  
Failure classification: **NO_MEAN_REVERSION**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2024-10-11 14:50:00-04:00 | 66.52052 | 66.525307 | 66.50616 | 66.525307 | 2531.0 | 1.3699179712140361 | 66.544454 | 66.056212 | 0.03745143887581717 | SELL KO 530.5487@66.5062 residual grid layer 1 \| BUY XLP 397.0652@78.4184 beta hedge: residual grid layer 1 |
| 2024-10-11 14:55:00-04:00 | 66.530094 | 66.5636 | 66.530094 | 66.54924 | 2297.0 | 1.5057164782294639 | 66.544454 | 66.056212 | 0.037511550384687085 |  |
| 2024-10-11 15:00:00-04:00 | 66.54924 | 66.568387 | 66.53488 | 66.558814 | 1773.0 | 1.7358280922183005 | 66.5636 | 66.056212 | 0.03722551107149517 |  |
| 2024-10-11 15:05:00-04:00 | 66.5636 | 66.621041 | 66.54924 | 66.611467 | 2750.0 | 2.456299102815745 | 66.568387 | 66.132799 | 0.039695188852103214 |  |
| 2024-10-11 15:10:00-04:00 | 66.597107 | 66.616254 | 66.577961 | 66.592321 | 2680.0 | 1.4421978100193846 | 66.621041 | 66.252466 | 0.039595032505524125 | SELL KO 662.4232@66.5780 residual grid layer 2 \| BUY XLP 549.0310@78.4882 beta hedge: residual grid layer 2 |
| 2024-10-11 15:15:00-04:00 | 66.601894 | 66.616254 | 66.592321 | 66.592321 | 1741.0 | 1.2498603036135936 | 66.621041 | 66.266826 | 0.038476315897986654 | BUY KO 1192.9719@66.6163 residual kill \| SELL XLP 946.0962@78.4617 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
