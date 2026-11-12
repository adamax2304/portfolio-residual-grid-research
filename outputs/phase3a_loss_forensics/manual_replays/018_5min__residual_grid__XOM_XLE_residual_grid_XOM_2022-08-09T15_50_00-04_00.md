# Campaign replay — residual_grid:XOM:2022-08-09T15:50:00-04:00

Selection: **TYPICAL_RESIDUAL_LOSER**  
Run: `5min__residual_grid__XOM_XLE`  
Period: 2022-08-10 09:40:00-04:00 → 2022-08-10 09:45:00-04:00  
Net P&L: **$-23.89**; stock leg $-40.15; hedge leg $16.27  
MAE/MFE: $-23.89 / $4.73  
Grid: 1/4 levels; step/ATR 0.350; average-entry improvement 0.0000  
TP/stop: 1.148 ATR / 1.421 ATR  
Exit: residual kill  
Failure classification: **NO_MEAN_REVERSION**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-08-10 09:40:00-04:00 | 79.550582 | 79.665006 | 79.400952 | 79.497772 | 2594.0 | -3.210697513844897 | 80.271982 | 79.594248 | 0.12482833739246843 | BUY XOM 481.9673@79.5824 residual grid layer 1 \| SELL XLE 783.4241@32.9016 beta hedge: residual grid layer 1 |
| 2022-08-10 09:45:00-04:00 | 79.532979 | 79.629799 | 79.321736 | 79.418556 | 10224.0 | -3.2822407215442855 | 80.271982 | 79.400952 | 0.13791652757872097 | SELL XOM 481.9673@79.5012 residual kill \| BUY XLE 783.4241@32.8795 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
