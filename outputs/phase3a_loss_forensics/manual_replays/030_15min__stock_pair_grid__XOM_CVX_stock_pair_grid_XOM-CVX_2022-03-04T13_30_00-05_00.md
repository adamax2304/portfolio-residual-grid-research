# Campaign replay — stock_pair_grid:XOM-CVX:2022-03-04T13:30:00-05:00

Selection: **ALL_STOCK_PAIR_TRADES**  
Run: `15min__stock_pair_grid__XOM_CVX`  
Period: 2022-03-04 13:45:00-05:00 → 2022-03-04 14:00:00-05:00  
Net P&L: **$-59.35**; stock leg $20.24; hedge leg $-79.55  
MAE/MFE: $-59.35 / $-31.17  
Grid: 1/4 levels; step/ATR UNAVAILABLE; average-entry improvement -0.0000  
TP/stop: UNAVAILABLE ATR / UNAVAILABLE ATR  
Exit: pair kill  
Failure classification: **HEDGE_DRAG**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-04 13:45:00-05:00 | 82.77 | 82.9 | 82.64 | 82.66 | 708452.0 | 2.5723192460847466 | None | None | None | SELL XOM 484.5091@82.7369 pair grid layer 1 \| BUY CVX 177.4221@157.1600 hedge: pair grid layer 1 |
| 2022-03-04 14:00:00-05:00 | 82.66 | 83.05 | 82.61 | 83.01 | 1667275.0 | 2.9650743969741598 | None | None | None | BUY XOM 484.5091@82.6931 pair kill \| SELL CVX 177.4221@156.7173 pair kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
