# Campaign replay — residual_grid:CVX:2025-02-18T10:00:00-05:00

Selection: **TYPICAL_RESIDUAL_LOSER**  
Run: `15min__residual_grid__CVX_XLE`  
Period: 2025-02-18 10:15:00-05:00 → 2025-02-18 10:30:00-05:00  
Net P&L: **$-114.93**; stock leg $92.36; hedge leg $-207.25  
MAE/MFE: $-114.93 / $-95.08  
Grid: 1/4 levels; step/ATR 0.350; average-entry improvement 0.0000  
TP/stop: 3.361 ATR / 0.000 ATR  
Exit: residual kill z  
Failure classification: **HEDGE_DRAG**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-02-18 10:15:00-05:00 | 148.659831 | 149.119012 | 148.621566 | 149.109445 | 3525.0 | -4.007472513668011 | 150.593274 | 146.08402 | 0.387193964155154 | BUY CVX 240.6976@148.7193 residual grid layer 1 \| SELL XLE 1042.8567@43.5909 beta hedge: residual grid layer 1 |
| 2025-02-18 10:30:00-05:00 | 149.166843 | 149.166843 | 148.760276 | 148.793758 | 3863.0 | -3.934211105515879 | 150.593274 | 146.08402 | 0.38857775242978554 | SELL CVX 240.6976@149.1072 residual kill z \| BUY XLE 1042.8567@43.7887 residual kill z |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
