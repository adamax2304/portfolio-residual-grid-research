# Campaign replay — residual_grid:PFE:2022-03-01T10:10:00-05:00

Selection: **STOPPED_THEN_REVERTED**  
Run: `5min__residual_grid__PFE_XLV`  
Period: 2022-03-01 10:15:00-05:00 → 2022-03-01 10:35:00-05:00  
Net P&L: **$-640.27**; stock leg $-784.41; hedge leg $144.21  
MAE/MFE: $-640.27 / $-39.22  
Grid: 4/4 levels; step/ATR 0.351; average-entry improvement 0.0855  
TP/stop: 1.738 ATR / 0.835 ATR  
Exit: residual kill  
Failure classification: **NO_MEAN_REVERSION**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022-03-01 10:15:00-05:00 | 46.52 | 46.58 | 46.49 | 46.55 | 190995.0 | -2.2216252579325833 | 47.17 | 46.49 | 0.15151993632439784 | BUY PFE 859.8452@46.5386 residual grid layer 1 \| SELL XLV 177.8512@129.6500 beta hedge: residual grid layer 1 |
| 2022-03-01 10:20:00-05:00 | 46.55 | 46.55 | 46.35 | 46.39 | 214984.0 | -2.69894611799273 | 47.17 | 46.49 | 0.15498279801551199 | BUY PFE 1074.1139@46.5500 residual grid layer 2 \| SELL XLV 196.1389@129.8880 beta hedge: residual grid layer 2 |
| 2022-03-01 10:25:00-05:00 | 46.4 | 46.4 | 46.22 | 46.35 | 377003.0 | -2.594997145234081 | 47.17 | 46.35 | 0.15676974101440397 | BUY PFE 1077.5862@46.4000 residual grid layer 3 \| SELL XLV 164.6543@129.6981 beta hedge: residual grid layer 3 |
| 2022-03-01 10:30:00-05:00 | 46.35 | 46.36 | 46.28 | 46.29 | 204247.0 | -2.5719082352421903 | 47.17 | 46.22 | 0.15128618808480357 | BUY PFE 1294.4984@46.3600 residual grid layer 4 \| SELL XLV 160.6099@129.5781 beta hedge: residual grid layer 4 |
| 2022-03-01 10:35:00-05:00 | 46.29 | 46.39 | 46.26 | 46.26 | 180592.0 | -2.490608844778621 | 47.17 | 46.22 | 0.14976574607874638 | SELL PFE 4306.0437@46.2715 residual kill \| BUY XLV 699.2544@129.5018 residual kill |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
