# Campaign replay — residual_grid:KO:2023-11-03T12:25:00-04:00

Selection: **HIGHEST_COST_TP_RATIO**  
Run: `5min__residual_grid__KO_XLP`  
Period: 2023-11-03 12:30:00-04:00 → 2023-11-03 12:55:00-04:00  
Net P&L: **$20.87**; stock leg $43.51; hedge leg $-22.60  
MAE/MFE: $-18.26 / $26.54  
Grid: 1/4 levels; step/ATR 0.178; average-entry improvement -0.0000  
TP/stop: 0.626 ATR / 0.679 ATR  
Exit: residual TP3  
Failure classification: **WINNING_CAMPAIGN**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2023-11-03 12:30:00-04:00 | 53.18 | 53.198575 | 53.156781 | 53.189287 | 7212.0 | 1.6333232555408528 | 53.29145 | 52.928919 | 0.05214958483474501 | SELL KO 679.6857@53.1587 residual grid layer 1 \| BUY XLP 216.4158@64.6441 beta hedge: residual grid layer 1 |
| 2023-11-03 12:35:00-04:00 | 53.189287 | 53.189287 | 53.14285 | 53.161425 | 3560.0 | 0.8256059588025032 | 53.29145 | 52.928919 | 0.05174154306083447 |  |
| 2023-11-03 12:40:00-04:00 | 53.156781 | 53.156781 | 53.101057 | 53.101057 | 2365.0 | -0.4109334265317851 | 53.29145 | 52.938207 | 0.052357718556489435 |  |
| 2023-11-03 12:45:00-04:00 | 53.096413 | 53.101057 | 53.082482 | 53.082482 | 648.0 | -0.7775739860120136 | 53.29145 | 52.938207 | 0.0499446672310258 | BUY KO 226.5619@53.1011 residual TP1 \| SELL XLP 72.1386@64.5435 residual TP1 |
| 2023-11-03 12:50:00-04:00 | 53.087125 | 53.096413 | 53.073194 | 53.073194 | 1428.0 | -1.1726943008359036 | 53.29145 | 52.938207 | 0.048035691000238065 | BUY KO 226.5619@53.0964 residual TP2 \| SELL XLP 72.1386@64.5481 residual TP2 |
| 2023-11-03 12:55:00-04:00 | 53.063907 | 53.077838 | 53.054619 | 53.06855 | 1505.0 | -1.0687591866995532 | 53.29145 | 52.938207 | 0.046263070214506596 | BUY KO 226.5619@53.0778 residual TP3 \| SELL XLP 72.1386@64.5550 residual TP3 |

## Interpretation

Observed campaign is profitable; it is included as a comparison case, not as evidence of a stable edge.
