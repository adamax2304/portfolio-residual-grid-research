# Campaign replay — residual_grid:MSFT:2022-09-12T15:25:00-04:00

Selection: **HIGHEST_COST_TP_RATIO**  
Run: `5min__residual_grid__MSFT_XLK`  
Period: 2022-09-12 15:30:00-04:00 → 2022-09-13 09:45:00-04:00  
Net P&L: **$-718.80**; stock leg $-1701.74; hedge leg $985.37  
MAE/MFE: $-718.80 / $-6.72  
Grid: 2/4 levels; step/ATR 0.200; average-entry improvement 0.0702  
TP/stop: 0.592 ATR / 0.872 ATR  
Exit: residual kill  
Failure classification: **NO_MEAN_REVERSION**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-09-12 15:30:00-04:00 | 258.591821 | 258.742439 | 258.441203 | 258.441203 | 3951.0 | -1.81512514895829 | 259.694734 | 257.809579 | 0.31808913341092915 | BUY MSFT 147.7675@258.6953 residual grid layer 1 \| SELL XLK 384.9228@67.6201 beta hedge: residual grid layer 1 |
| 2022-09-12 15:35:00-04:00 | 258.465496 | 258.684135 | 258.382899 | 258.55781 | 7340.0 | -1.7496521549323127 | 259.694734 | 257.809579 | 0.3168853381672926 | BUY MSFT 184.7996@258.5689 residual grid layer 2 \| SELL XLK 470.0898@67.5694 beta hedge: residual grid layer 2 |
| 2022-09-12 15:40:00-04:00 | 258.538376 | 258.985371 | 258.324595 | 258.956219 | 4517.0 | -0.9916698852969711 | 259.694734 | 257.809579 | 0.34144895686962873 |  |
| 2022-09-12 15:45:00-04:00 | 258.902774 | 258.99023 | 258.59668 | 258.927068 | 6736.0 | -0.6250339165268116 | 259.694734 | 257.809579 | 0.3451704599503699 |  |
| 2022-09-12 15:50:00-04:00 | 258.888198 | 259.043675 | 258.752156 | 258.849329 | 11710.0 | -0.5513486397036401 | 259.694734 | 257.809579 | 0.3413382128110573 | SELL MSFT 110.8557@258.7846 residual TP1 \| BUY XLK 285.0042@67.7298 residual TP1 |
| 2022-09-13 09:40:00-04:00 | 251.673942 | 251.931452 | 250.852828 | 251.037457 | 6993.0 | -17.56621869590434 | 259.694734 | 257.809579 | 0.8881355547531262 |  |
| 2022-09-13 09:45:00-04:00 | 250.979153 | 251.57191 | 250.755655 | 251.183217 | 12168.0 | -2.8726493689090122 | 259.694734 | 250.852828 | 0.883001229413618 | SELL MSFT 221.7114@250.8788 residual kill \| BUY XLK 570.0084@65.7912 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
