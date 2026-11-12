# Campaign replay — residual_grid:CSCO:2022-03-02T09:45:00-05:00

Selection: **STOPPED_THEN_REVERTED**  
Run: `5min__residual_grid__CSCO_XLK`  
Period: 2022-03-02 09:50:00-05:00 → 2022-03-02 10:05:00-05:00  
Net P&L: **$-416.98**; stock leg $-423.89; hedge leg $6.98  
MAE/MFE: $-416.98 / $-5.27  
Grid: 3/4 levels; step/ATR 0.266; average-entry improvement -0.0242  
TP/stop: 1.725 ATR / 0.229 ATR  
Exit: residual kill  
Failure classification: **NO_MEAN_REVERSION**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-02 09:50:00-05:00 | 55.39 | 55.43 | 55.33 | 55.34 | 117903.0 | 2.343735921519593 | 55.54 | 54.26 | 0.19724701489622348 | SELL CSCO 724.0844@55.3678 residual grid layer 1 \| BUY XLK 372.9934@76.3005 beta hedge: residual grid layer 1 |
| 2022-03-02 09:55:00-05:00 | 55.34 | 55.4 | 55.26 | 55.36 | 165729.0 | 2.7255503544639814 | 55.54 | 54.26 | 0.19315794240363612 | SELL CSCO 905.9232@55.3179 residual grid layer 2 \| BUY XLK 492.6901@76.2805 beta hedge: residual grid layer 2 |
| 2022-03-02 10:00:00-05:00 | 55.36 | 55.52 | 55.35 | 55.5 | 125019.0 | 2.6419089830660774 | 55.54 | 54.26 | 0.1915038036605194 | SELL CSCO 905.5960@55.3500 residual grid layer 3 \| BUY XLK 523.2897@76.1004 beta hedge: residual grid layer 3 |
| 2022-03-02 10:05:00-05:00 | 55.49 | 55.51 | 55.24 | 55.28 | 97815.0 | 3.1114910011620136 | 55.54 | 54.26 | 0.19711067482762487 | BUY CSCO 2535.6036@55.5100 residual kill \| SELL XLK 1388.9733@76.2245 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
