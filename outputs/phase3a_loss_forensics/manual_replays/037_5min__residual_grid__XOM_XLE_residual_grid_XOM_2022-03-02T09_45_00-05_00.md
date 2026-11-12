# Campaign replay — residual_grid:XOM:2022-03-02T09:45:00-05:00

Selection: **STOPPED_THEN_REVERTED**  
Run: `5min__residual_grid__XOM_XLE`  
Period: 2022-03-02 09:50:00-05:00 → 2022-03-02 09:55:00-05:00  
Net P&L: **$-42.20**; stock leg $-67.33; hedge leg $25.15  
MAE/MFE: $-42.20 / $-3.61  
Grid: 1/4 levels; step/ATR 0.264; average-entry improvement -0.0000  
TP/stop: 1.161 ATR / 0.773 ATR  
Exit: residual kill  
Failure classification: **STOP_OR_EXIT_FAILURE**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-02 09:50:00-05:00 | 81.58 | 81.81 | 81.51 | 81.64 | 1227991.0 | 1.0878979846178436 | 81.62 | 78.61 | 0.3759682759756903 | SELL XOM 490.2999@81.5474 residual grid layer 1 \| BUY XLE 849.2128@36.4996 beta hedge: residual grid layer 1 |
| 2022-03-02 09:55:00-05:00 | 81.65 | 81.75 | 81.38 | 81.68 | 1014110.0 | 0.7613267035988773 | 81.81 | 78.61 | 0.37554197054885563 | BUY XOM 490.2999@81.6827 residual kill \| SELL XLE 849.2128@36.5304 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
