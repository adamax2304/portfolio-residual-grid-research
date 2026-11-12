# Campaign replay — residual_grid:JPM:2022-06-09T14:30:00-04:00

Selection: **BIGGEST_HEDGE_DRAG**  
Run: `15min__residual_grid__JPM_XLF`  
Period: 2022-06-09 14:45:00-04:00 → 2022-06-10 09:45:00-04:00  
Net P&L: **$-712.63**; stock leg $3264.30; hedge leg $-3968.25  
MAE/MFE: $-712.63 / $-9.49  
Grid: 3/4 levels; step/ATR 0.303; average-entry improvement -0.2696  
TP/stop: 1.376 ATR / 0.849 ATR  
Exit: residual kill  
Failure classification: **HEDGE_DRAG**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-06-09 14:45:00-04:00 | 114.91239 | 115.030426 | 114.730797 | 114.758036 | 18823.0 | 1.8801640798376027 | 118.299135 | 114.580982 | 0.3827496056676641 | SELL JPM 342.6525@114.8664 residual grid layer 1 \| BUY XLF 1265.4525@31.8641 beta hedge: residual grid layer 1 |
| 2022-06-09 15:00:00-04:00 | 114.748956 | 114.748956 | 114.449327 | 114.467486 | 15601.0 | 1.9020311759662702 | 118.299135 | 114.580982 | 0.37746099097711716 | SELL JPM 428.9256@114.7031 residual grid layer 2 \| BUY XLF 1559.0512@31.8234 beta hedge: residual grid layer 2 |
| 2022-06-09 15:15:00-04:00 | 114.462946 | 114.694478 | 114.399389 | 114.413008 | 31830.0 | 2.01364287891742 | 118.299135 | 114.449327 | 0.37157727733589485 |  |
| 2022-06-09 15:30:00-04:00 | 114.394849 | 114.449327 | 114.176936 | 114.335831 | 32571.0 | 2.1840330113031743 | 118.299135 | 114.399389 | 0.36449254324047375 |  |
| 2022-06-09 15:45:00-04:00 | 114.322211 | 114.34945 | 113.750192 | 113.750192 | 61254.0 | 1.7684082027581698 | 118.299135 | 114.176936 | 0.3812615044375832 | SELL JPM 430.5267@114.2765 residual grid layer 3 \| BUY XLF 1490.0533@31.6322 beta hedge: residual grid layer 3 |
| 2022-06-10 09:45:00-04:00 | 111.834961 | 112.025635 | 110.618277 | 110.781713 | 18841.0 | 0.39712686986364654 | 118.299135 | 113.750192 | 0.5777367541206124 | BUY JPM 1202.1049@111.8797 residual kill \| SELL XLF 4314.5570@30.8501 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
