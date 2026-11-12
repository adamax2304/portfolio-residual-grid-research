# Campaign replay — stock_pair_grid:XOM-CVX:2022-03-02T11:20:00-05:00

Selection: **ALL_STOCK_PAIR_TRADES**  
Run: `5min__stock_pair_grid__XOM_CVX`  
Period: 2022-03-02 11:25:00-05:00 → 2022-03-02 12:15:00-05:00  
Net P&L: **$399.97**; stock leg $571.27; hedge leg $-171.21  
MAE/MFE: $-93.18 / $415.67  
Grid: 2/4 levels; step/ATR UNAVAILABLE; average-entry improvement 0.0167  
TP/stop: UNAVAILABLE ATR / UNAVAILABLE ATR  
Exit: pair TP3  
Failure classification: **WINNING_CAMPAIGN**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-02 11:25:00-05:00 | 80.0 | 80.32 | 79.96 | 79.98 | 367670.0 | -1.9556685267396208 | None | None | None | BUY XOM 500.0000@80.0320 pair grid layer 1 \| SELL CVX 150.4089@153.9100 hedge: pair grid layer 1 |
| 2022-03-02 11:30:00-05:00 | 79.97 | 80.27 | 79.92 | 79.99 | 422901.0 | -1.6943639375776427 | None | None | None | BUY XOM 625.2345@80.0020 pair grid layer 2 \| SELL CVX 185.4432@154.2883 hedge: pair grid layer 2 |
| 2022-03-02 11:35:00-05:00 | 79.98 | 80.07 | 79.82 | 80.05 | 277250.0 | -1.3003319916332592 | None | None | None |  |
| 2022-03-02 11:40:00-05:00 | 80.04 | 80.27 | 80.04 | 80.2 | 307995.0 | -0.7918428435130017 | None | None | None |  |
| 2022-03-02 11:45:00-05:00 | 80.2 | 80.29 | 80.09 | 80.22 | 255174.0 | -0.6257150826296688 | None | None | None | SELL XOM 375.0782@80.1679 pair TP1 \| BUY CVX 111.9507@154.3617 pair TP1 |
| 2022-03-02 11:50:00-05:00 | 80.21 | 80.51 | 80.17 | 80.5 | 404209.0 | -0.024142491797236116 | None | None | None |  |
| 2022-03-02 11:55:00-05:00 | 80.51 | 80.59 | 80.38 | 80.57 | 368365.0 | -0.0020120001541886444 | None | None | None | SELL XOM 375.0782@80.4778 pair TP2 \| BUY CVX 111.9507@154.7219 pair TP2 |
| 2022-03-02 12:00:00-05:00 | 80.57 | 80.61 | 80.49 | 80.52 | 324818.0 | -0.14958773026902578 | None | None | None |  |
| 2022-03-02 12:05:00-05:00 | 80.53 | 80.6 | 80.36 | 80.53 | 265034.0 | -0.03682219179859211 | None | None | None |  |
| 2022-03-02 12:10:00-05:00 | 80.53 | 80.97 | 80.52 | 80.96 | 773417.0 | 1.658133027476769 | None | None | None |  |
| 2022-03-02 12:15:00-05:00 | 80.96 | 81.04 | 80.93 | 81.0 | 501706.0 | 2.1456742117286005 | None | None | None | SELL XOM 375.0782@80.9300 pair TP3 \| BUY CVX 111.9507@154.7800 pair TP3 |

## Interpretation

Observed campaign is profitable; it is included as a comparison case, not as evidence of a stable edge.
