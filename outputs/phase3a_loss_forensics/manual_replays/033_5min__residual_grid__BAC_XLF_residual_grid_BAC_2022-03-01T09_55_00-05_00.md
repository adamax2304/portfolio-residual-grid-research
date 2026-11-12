# Campaign replay — residual_grid:BAC:2022-03-01T09:55:00-05:00

Selection: **STOPPED_THEN_REVERTED**  
Run: `5min__residual_grid__BAC_XLF`  
Period: 2022-03-01 10:00:00-05:00 → 2022-03-01 10:10:00-05:00  
Net P&L: **$4.10**; stock leg $-42.90; hedge leg $47.02  
MAE/MFE: $4.10 / $72.79  
Grid: 1/4 levels; step/ATR 0.225; average-entry improvement 0.0000  
TP/stop: 0.690 ATR / 0.957 ATR  
Exit: residual kill  
Failure classification: **WINNING_CAMPAIGN**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-01 10:00:00-05:00 | 42.53 | 42.77 | 42.53 | 42.62 | 995821.0 | -0.6685579857638517 | 44.04 | 42.45 | 0.2125329157822628 | BUY BAC 940.5126@42.5470 residual grid layer 1 \| SELL XLF 1041.3910@37.6249 beta hedge: residual grid layer 1 |
| 2022-03-01 10:05:00-05:00 | 42.62 | 42.62 | 42.4 | 42.49 | 1015823.0 | -0.7441383063284616 | 44.04 | 42.45 | 0.2130662789406725 | SELL BAC 313.5042@42.6030 residual TP1 \| BUY XLF 347.1303@37.6350 residual TP1 |
| 2022-03-01 10:10:00-05:00 | 42.47 | 42.51 | 42.39 | 42.4 | 675235.0 | -0.3752380941106762 | 44.04 | 42.4 | 0.20641868758776716 | SELL BAC 627.0084@42.4530 residual kill \| BUY XLF 694.2607@37.5500 residual kill |

## Interpretation

Observed campaign is profitable; it is included as a comparison case, not as evidence of a stable edge.
