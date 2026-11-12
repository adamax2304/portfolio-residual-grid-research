# Campaign replay — stock_pair_grid:XOM-CVX:2022-03-02T10:00:00-05:00

Selection: **ALL_STOCK_PAIR_TRADES**  
Run: `15min__stock_pair_grid__XOM_CVX`  
Period: 2022-03-02 10:15:00-05:00 → 2022-03-02 11:30:00-05:00  
Net P&L: **$388.36**; stock leg $427.21; hedge leg $-38.76  
MAE/MFE: $168.50 / $394.29  
Grid: 1/4 levels; step/ATR UNAVAILABLE; average-entry improvement -0.0000  
TP/stop: UNAVAILABLE ATR / UNAVAILABLE ATR  
Exit: pair TP3  
Failure classification: **WINNING_CAMPAIGN**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-02 10:15:00-05:00 | 81.32 | 81.41 | 80.76 | 80.82 | 1588497.0 | 1.4203281730166541 | None | None | None | SELL XOM 424.1045@81.2875 pair grid layer 1 \| BUY CVX 84.1112@154.8319 hedge: pair grid layer 1 |
| 2022-03-02 10:30:00-05:00 | 80.82 | 81.18 | 80.21 | 80.34 | 1620096.0 | 0.424191274416439 | None | None | None |  |
| 2022-03-02 10:45:00-05:00 | 80.35 | 80.69 | 79.91 | 80.41 | 1872751.0 | 0.30760779720677756 | None | None | None | BUY XOM 141.3682@80.3821 pair TP1 \| SELL CVX 28.0371@154.1683 pair TP1 |
| 2022-03-02 11:00:00-05:00 | 80.41 | 80.57 | 80.03 | 80.26 | 1478046.0 | 0.1663060151768522 | None | None | None | BUY XOM 141.3682@80.4422 pair TP2 \| SELL CVX 28.0371@154.7281 pair TP2 |
| 2022-03-02 11:15:00-05:00 | 80.27 | 80.32 | 79.85 | 79.98 | 1319269.0 | -0.4278969204418364 | None | None | None |  |
| 2022-03-02 11:30:00-05:00 | 79.97 | 80.27 | 79.82 | 80.2 | 1008146.0 | 0.1452884875002118 | None | None | None | BUY XOM 141.3682@80.0020 pair TP3 \| SELL CVX 28.0371@154.2883 pair TP3 |

## Interpretation

Observed campaign is profitable; it is included as a comparison case, not as evidence of a stable edge.
