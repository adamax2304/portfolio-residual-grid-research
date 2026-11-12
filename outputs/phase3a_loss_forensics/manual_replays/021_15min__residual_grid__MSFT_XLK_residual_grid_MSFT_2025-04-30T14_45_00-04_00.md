# Campaign replay — residual_grid:MSFT:2025-04-30T14:45:00-04:00

Selection: **RESIDUAL_WINNER**  
Run: `15min__residual_grid__MSFT_XLK`  
Period: 2025-04-30 15:00:00-04:00 → 2025-05-01 10:00:00-04:00  
Net P&L: **$2986.62**; stock leg $3987.35; hedge leg $-998.60  
MAE/MFE: $39.49 / $3021.86  
Grid: 1/4 levels; step/ATR 0.194; average-entry improvement 0.0000  
TP/stop: 0.924 ATR / 0.501 ATR  
Exit: residual kill  
Failure classification: **WINNING_CAMPAIGN**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2025-04-30 15:00:00-04:00 | 387.003512 | 388.025651 | 387.003512 | 387.985956 | 19016.0 | -1.4992088376527883 | 391.985767 | 381.70427 | 1.394653353517536 | BUY MSFT 96.1613@387.1583 residual grid layer 1 \| SELL XLK 314.5105@103.5002 beta hedge: residual grid layer 1 |
| 2025-04-30 15:15:00-04:00 | 388.095117 | 388.154659 | 386.874505 | 387.216871 | 14858.0 | -1.3557435020479742 | 391.985767 | 381.70427 | 1.3864748282662822 |  |
| 2025-04-30 15:30:00-04:00 | 387.241681 | 388.348171 | 386.963818 | 388.224125 | 26723.0 | -1.4214182013911407 | 391.985767 | 381.70427 | 1.3863232691044032 |  |
| 2025-04-30 15:45:00-04:00 | 388.23901 | 393.58291 | 388.23901 | 391.032525 | 142807.0 | -0.4892041781289352 | 391.985767 | 381.70427 | 1.6700705355969467 |  |
| 2025-05-01 09:45:00-04:00 | 431.007082 | 431.354412 | 426.908585 | 427.236068 | 166105.0 | 28.38689419442437 | 393.58291 | 381.70427 | 4.430914568768594 | SELL MSFT 32.0538@430.8347 residual TP1 \| BUY XLK 104.8368@106.8198 residual TP1 |
| 2025-05-01 10:00:00-04:00 | 427.712407 | 428.645236 | 425.866594 | 426.501713 | 99238.0 | 5.705228990859614 | 431.354412 | 381.70427 | 4.312895099570837 | SELL MSFT 64.1075@427.5413 residual kill \| BUY XLK 209.6737@106.5959 residual kill |

## Interpretation

Observed campaign is profitable; it is included as a comparison case, not as evidence of a stable edge.
