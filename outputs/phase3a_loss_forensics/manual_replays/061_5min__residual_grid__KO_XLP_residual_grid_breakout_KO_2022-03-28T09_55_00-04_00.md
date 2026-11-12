# Campaign replay — residual_grid:breakout:KO:2022-03-28T09:55:00-04:00

Selection: **HIGHEST_COST_TP_RATIO**  
Run: `5min__residual_grid__KO_XLP`  
Period: 2022-03-28 10:00:00-04:00 → 2022-03-28 10:05:00-04:00  
Net P&L: **$-24.75**; stock leg $28.52; hedge leg $-53.26  
MAE/MFE: $-24.75 / $0.57  
Grid: 1/4 levels; step/ATR 0.194; average-entry improvement 0.0000  
TP/stop: 0.386 ATR / 1.039 ATR  
Exit: residual breakout exit  
Failure classification: **HEDGE_DRAG**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-28 10:00:00-04:00 | 54.653294 | 54.742118 | 54.617765 | 54.733236 | 2030.0 | 2.3787763985752517 | 54.684383 | 54.276676 | 0.07747264877663967 | BUY KO 726.6688@54.6752 residual breakout continuation \| SELL XLP 646.5975@67.2479 beta hedge: residual breakout continuation |
| 2022-03-28 10:05:00-04:00 | 54.737677 | 54.773206 | 54.662177 | 54.706589 | 2544.0 | 2.1307771716706245 | 54.742118 | 54.276676 | 0.07986953100687984 | SELL KO 726.6688@54.7158 residual breakout exit \| BUY XLP 646.5975@67.3287 residual breakout exit |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
