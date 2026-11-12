# Campaign replay — residual_grid:JPM:2022-03-01T15:40:00-05:00

Selection: **STOPPED_THEN_REVERTED**  
Run: `5min__residual_grid__JPM_XLF`  
Period: 2022-03-01 15:45:00-05:00 → 2022-03-02 09:50:00-05:00  
Net P&L: **$605.86**; stock leg $-1592.84; hedge leg $2204.29  
MAE/MFE: $-114.74 / $740.47  
Grid: 3/4 levels; step/ATR 0.364; average-entry improvement 0.3347  
TP/stop: 1.644 ATR / 1.027 ATR  
Exit: residual kill  
Failure classification: **WINNING_CAMPAIGN**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-01 15:45:00-05:00 | 136.26 | 136.39 | 135.85 | 135.87 | 459885.0 | 2.276743086182622 | 137.2 | 133.58 | 0.4474341670508487 | SELL JPM 293.5564@136.2055 residual grid layer 1 \| BUY XLF 1418.0404@37.1248 beta hedge: residual grid layer 1 |
| 2022-03-01 15:50:00-05:00 | 135.85 | 136.48 | 135.67 | 136.43 | 539205.0 | 2.3668289638368556 | 137.2 | 133.58 | 0.47333172654721684 | SELL JPM 368.0530@135.7957 residual grid layer 2 \| BUY XLF 1771.8870@36.9748 beta hedge: residual grid layer 2 |
| 2022-03-02 09:40:00-05:00 | 137.62 | 137.97 | 137.34 | 137.77 | 262005.0 | 0.3726677818123749 | 137.1 | 133.58 | 0.5495223175081294 | SELL JPM 363.3193@137.5650 residual grid layer 3 \| BUY XLF 1688.2929@37.5550 beta hedge: residual grid layer 3 |
| 2022-03-02 09:45:00-05:00 | 137.77 | 138.48 | 137.72 | 138.21 | 363228.0 | 0.3139594181896979 | 137.97 | 133.58 | 0.5645564376861195 | BUY JPM 341.6429@137.8251 residual TP1 \| SELL XLF 1626.0734@37.6249 residual TP1 |
| 2022-03-02 09:50:00-05:00 | 138.17 | 138.42 | 137.94 | 138.41 | 183738.0 | 0.4255676525799808 | 138.48 | 133.58 | 0.5585166921371103 | BUY JPM 683.2858@138.2253 residual kill \| SELL XLF 3252.1469@37.6949 residual kill |

## Interpretation

Observed campaign is profitable; it is included as a comparison case, not as evidence of a stable edge.
