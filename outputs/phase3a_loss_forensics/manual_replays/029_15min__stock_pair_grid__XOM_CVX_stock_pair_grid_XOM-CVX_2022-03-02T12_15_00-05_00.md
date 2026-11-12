# Campaign replay — stock_pair_grid:XOM-CVX:2022-03-02T12:15:00-05:00

Selection: **ALL_STOCK_PAIR_TRADES**  
Run: `15min__stock_pair_grid__XOM_CVX`  
Period: 2022-03-02 12:30:00-05:00 → 2022-03-02 13:00:00-05:00  
Net P&L: **$-131.31**; stock leg $-102.28; hedge leg $-28.92  
MAE/MFE: $-131.31 / $-76.85  
Grid: 2/4 levels; step/ATR UNAVAILABLE; average-entry improvement 0.0444  
TP/stop: UNAVAILABLE ATR / UNAVAILABLE ATR  
Exit: pair kill  
Failure classification: **NO_MEAN_REVERSION**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-02 12:30:00-05:00 | 81.06 | 81.3 | 80.97 | 81.13 | 890789.0 | 2.34360754584644 | None | None | None | SELL XOM 495.3780@81.0276 pair grid layer 1 \| BUY CVX 106.2994@154.7319 hedge: pair grid layer 1 |
| 2022-03-02 12:45:00-05:00 | 81.14 | 81.22 | 80.99 | 81.13 | 680183.0 | 2.1077415999089855 | None | None | None | SELL XOM 618.6120@81.1075 pair grid layer 2 \| BUY CVX 133.2571@154.3917 hedge: pair grid layer 2 |
| 2022-03-02 13:00:00-05:00 | 81.13 | 81.28 | 81.07 | 81.15 | 639562.0 | 1.9894774106639235 | None | None | None | BUY XOM 1113.9900@81.1625 pair kill \| SELL CVX 239.5565@154.4282 pair kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
