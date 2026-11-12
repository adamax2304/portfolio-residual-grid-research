# Campaign replay — residual_grid:MSFT:2022-04-21T10:00:00-04:00

Selection: **TP_MISSED_THEN_REVERSED**  
Run: `15min__residual_grid__MSFT_XLK`  
Period: 2022-04-21 10:15:00-04:00 → 2022-04-21 11:15:00-04:00  
Net P&L: **$-15.95**; stock leg $104.62; hedge leg $-120.46  
MAE/MFE: $-37.14 / $24.81  
Grid: 1/4 levels; step/ATR 0.120; average-entry improvement -0.0000  
TP/stop: 0.468 ATR / 0.410 ATR  
Exit: residual TP3  
Failure classification: **HEDGE_DRAG**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-04-21 10:15:00-04:00 | 281.156625 | 281.978834 | 280.261869 | 281.896613 | 23914.0 | 1.0394860259478387 | 283.700635 | 269.258717 | 1.4062959994051327 | SELL MSFT 140.4216@281.0442 residual grid layer 1 \| BUY XLK 616.9054@73.5512 beta hedge: residual grid layer 1 |
| 2022-04-21 10:30:00-04:00 | 281.973997 | 282.201314 | 281.088914 | 281.156625 | 34473.0 | 0.628736430581776 | 283.700635 | 269.258717 | 1.3853034280190546 |  |
| 2022-04-21 10:45:00-04:00 | 281.156625 | 281.156625 | 279.096268 | 279.521881 | 36266.0 | -0.4610765853488822 | 283.700635 | 269.258717 | 1.4335215403034087 | BUY MSFT 46.8072@281.1566 residual TP1 \| SELL XLK 205.6351@73.4705 residual TP1 |
| 2022-04-21 11:00:00-04:00 | 279.502535 | 280.276379 | 279.188162 | 279.928149 | 37738.0 | -0.20993206413168977 | 283.700635 | 269.258717 | 1.4088569302817397 | BUY MSFT 46.8072@279.6143 residual TP2 \| SELL XLK 205.6351@73.2599 residual TP2 |
| 2022-04-21 11:15:00-04:00 | 279.971678 | 280.518205 | 279.367113 | 279.599266 | 34556.0 | -0.44512389693450105 | 283.700635 | 269.258717 | 1.3904451495473302 | BUY MSFT 46.8072@280.0837 residual TP3 \| SELL XLK 205.6351@73.3469 residual TP3 |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
