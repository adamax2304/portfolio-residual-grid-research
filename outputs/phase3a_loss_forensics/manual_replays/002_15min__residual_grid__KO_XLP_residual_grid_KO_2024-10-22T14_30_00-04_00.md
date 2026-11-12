# Campaign replay — residual_grid:KO:2024-10-22T14:30:00-04:00

Selection: **BIGGEST_RESIDUAL_LOSER**  
Run: `15min__residual_grid__KO_XLP`  
Period: 2024-10-22 14:45:00-04:00 → 2024-10-23 10:00:00-04:00  
Net P&L: **$-2285.58**; stock leg $-2530.34; hedge leg $254.54  
MAE/MFE: $-2285.58 / $-15.92  
Grid: 3/4 levels; step/ATR 0.634; average-entry improvement 0.5861  
TP/stop: 1.743 ATR / 2.903 ATR  
Exit: campaign maximum adverse excursion stop  
Failure classification: **NO_MEAN_REVERSION**

## Sampled path

| timestamp | open | high | low | close | volume | z_score | range_high | range_low | atr | state_or_fill |
|---|---|---|---|---|---|---|---|---|---|---|
| 2024-10-22 14:45:00-04:00 | 66.539147 | 66.558293 | 66.49128 | 66.50564 | 14592.0 | -1.3979776092656475 | 67.529238 | 66.237588 | 0.10268420822075693 | BUY KO 556.9885@66.5583 residual grid layer 1 \| SELL XLP 869.9429@78.6455 beta hedge: residual grid layer 1 |
| 2024-10-22 15:00:00-04:00 | 66.500853 | 66.539147 | 66.500853 | 66.529573 | 13184.0 | -1.6899840454307968 | 67.529238 | 66.237588 | 0.09808490763355954 |  |
| 2024-10-22 15:15:00-04:00 | 66.539147 | 66.596586 | 66.510427 | 66.567866 | 24150.0 | -1.9454060599292273 | 67.529238 | 66.237588 | 0.09723305708830493 |  |
| 2024-10-22 15:30:00-04:00 | 66.57744 | 66.649239 | 66.56308 | 66.634879 | 33788.0 | -1.9498181079090633 | 67.529238 | 66.237588 | 0.09644205301056852 | BUY KO 695.8352@66.6041 residual grid layer 2 \| SELL XLP 1041.4755@78.7442 beta hedge: residual grid layer 2 |
| 2024-10-22 15:45:00-04:00 | 66.630093 | 66.668386 | 66.400334 | 66.496067 | 120492.0 | -2.2185535885462326 | 67.529238 | 66.237588 | 0.1086999063669563 |  |
| 2024-10-23 09:45:00-04:00 | 64.873488 | 65.050594 | 64.466622 | 64.691595 | 53081.0 | -8.415357883903164 | 67.500518 | 66.237588 | 0.24589598448360195 | BUY KO 714.1118@64.8994 residual grid layer 3 \| SELL XLP 954.9891@78.3773 beta hedge: residual grid layer 3 |
| 2024-10-23 10:00:00-04:00 | 64.710741 | 65.246846 | 64.686808 | 64.863914 | 39786.0 | -6.1350767766657395 | 67.462226 | 64.466622 | 0.2683346998776308 | SELL KO 1966.9355@64.6868 campaign maximum adverse excursion stop \| BUY XLP 2866.4074@78.5025 campaign maximum adverse excursion stop |

## Interpretation

The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase.
