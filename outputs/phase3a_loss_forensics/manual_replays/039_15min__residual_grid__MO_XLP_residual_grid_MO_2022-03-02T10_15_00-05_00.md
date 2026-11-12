# Campaign replay — residual_grid:MO:2022-03-02T10:15:00-05:00

Selection: **STOPPED_THEN_REVERTED**  
Run: `15min__residual_grid__MO_XLP`  
Period: 2022-03-02 10:30:00-05:00 → 2022-03-02 10:45:00-05:00  
Net P&L: **$-161.09**; stock leg $-165.07; hedge leg $4.00  
MAE/MFE: $-161.09 / $-147.43  
Grid: 1/4 levels; step/ATR 0.481; average-entry improvement -0.0000  
TP/stop: 1.968 ATR / 1.563 ATR  
Exit: residual kill  
Failure classification: **NO_MEAN_REVERSION**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-02 10:30:00-05:00 | 52.01 | 52.29 | 51.88 | 52.27 | 329667.0 | 2.6043154438827845 | 52.12 | 50.74 | 0.24012316387851718 | SELL MO 543.7851@51.9892 residual grid layer 1 \| BUY XLP 125.2909@75.0700 beta hedge: residual grid layer 1 |
| 2022-03-02 10:45:00-05:00 | 52.27 | 52.3 | 52.08 | 52.23 | 226238.0 | 2.288384102636468 | 52.29 | 50.74 | 0.23868579503005158 | BUY MO 543.7851@52.2909 residual kill \| SELL XLP 125.2909@75.1099 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
