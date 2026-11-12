# Campaign replay — residual_grid:MO:2022-03-01T09:50:00-05:00

Selection: **STOPPED_THEN_REVERTED**  
Run: `5min__residual_grid__MO_XLP`  
Period: 2022-03-01 09:55:00-05:00 → 2022-03-01 10:20:00-05:00  
Net P&L: **$-165.50**; stock leg $69.79; hedge leg $-235.14  
MAE/MFE: $-325.64 / $-41.68  
Grid: 3/4 levels; step/ATR 0.307; average-entry improvement 0.0677  
TP/stop: 1.176 ATR / 1.079 ATR  
Exit: residual kill  
Failure classification: **HEDGE_DRAG**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-01 09:55:00-05:00 | 51.52 | 51.59 | 51.48 | 51.5 | 58935.0 | 1.8995621084980472 | 51.89 | 50.8 | 0.16095124472718852 | SELL MO 776.3975@51.4994 residual grid layer 1 \| BUY XLP 502.9045@74.9100 beta hedge: residual grid layer 1 |
| 2022-03-01 10:00:00-05:00 | 51.52 | 51.71 | 51.47 | 51.71 | 62150.0 | 2.280937883827584 | 51.89 | 50.8 | 0.16659758438953234 | SELL MO 970.4969@51.4994 residual grid layer 2 \| BUY XLP 654.5672@74.8799 beta hedge: residual grid layer 2 |
| 2022-03-01 10:05:00-05:00 | 51.71 | 51.73 | 51.53 | 51.6 | 71662.0 | 2.251619003938664 | 51.89 | 50.8 | 0.16898347121885116 | SELL MO 966.9310@51.6893 residual grid layer 3 \| BUY XLP 676.2528@75.0400 beta hedge: residual grid layer 3 |
| 2022-03-01 10:10:00-05:00 | 51.59 | 51.65 | 51.56 | 51.58 | 61740.0 | 2.0742949971559637 | 51.89 | 50.8 | 0.1633417947032187 |  |
| 2022-03-01 10:15:00-05:00 | 51.57 | 51.57 | 51.5 | 51.52 | 76823.0 | 1.3527204782630902 | 51.89 | 50.8 | 0.15738880936727437 |  |
| 2022-03-01 10:20:00-05:00 | 51.52 | 51.57 | 51.32 | 51.33 | 68471.0 | 1.0053306992897642 | 51.89 | 50.8 | 0.16400389441246904 | BUY MO 2713.8254@51.5406 residual kill \| SELL XLP 1833.7245@74.8201 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
