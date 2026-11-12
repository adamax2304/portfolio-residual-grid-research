# Manual campaign replay report

All prices below are the raw execution OHLC. Indicator range levels are adjusted internally; fill metadata preserves the submitted raw grid/TP/stop levels. These are representative mechanics replays, not best-variant selection.

## A. Best natural long grid campaign

Run: `natural_long_grid:MRK`; campaign: `natural_long_grid:MRK:2021-09-16T00:00:00`; reported P&L: $2,200.98; MAE/MFE: $121.73 / $2,200.98; final reason: natural grid time stop.

Price path:

```text
 timestamp      open      high       low     close
2021-09-17 71.190002 72.000000 70.889999 71.680000
2021-09-20 71.160004 72.610001 71.120003 71.930000
2021-09-21 72.480003 72.680000 71.769997 71.970001
2021-09-22 72.330002 72.410004 71.860001 72.040001
2021-09-23 72.680000 74.040001 72.570000 73.050003
2021-09-24 73.589996 74.629997 73.349998 73.610001
2021-09-27 73.510002 74.269997 73.339996 73.360001
2021-09-28 73.550003 73.820000 72.660004 73.320000
2021-09-29 73.610001 75.699997 73.580002 75.089996
2021-09-30 75.580002 76.650002 75.099998 75.110001
2021-10-01 81.559998 84.339996 80.629997 81.400002
```

Fills, levels, and state reasons:

```text
 timestamp symbol side   quantity     price                 reason  realized_pnl                                                                                                                                                                                                              metadata
2021-09-17    MRK  BUY 264.837029 71.218478   natural grid layer 1      0.000000 {'direction': 1, 'grid_layer': 1, 'grid_level': 71.97000122070312, 'adjusted_grid_level': 62.12773132324219, 'stop_price': 71.20928902418558, 'tp_prices': [75.20311902772875, 77.96733736176684, 78.52625175699642]}
2021-09-30    MRK SELL  88.279010 75.549770            natural TP1    382.362114                                                                                                                                                            {'close_fraction': 0.3333333333333333, 'close_all': False}
2021-10-01    MRK SELL 176.558019 81.527374 natural grid time stop   1820.118101                                                                                                                                                                            {'close_fraction': 1.0, 'close_all': True}
```

Mechanics verdict: fills occur at the recorded next-open/limit rule, averaging is average-cost, both relationship legs share timestamps, and the exit reason matches the recorded terminal campaign state.

## B. Worst natural long grid campaign

Run: `natural_long_grid:MDLZ`; campaign: `natural_long_grid:MDLZ:2023-09-25T00:00:00`; reported P&L: $-1,796.50; MAE/MFE: $-1,796.50 / $160.64; final reason: campaign maximum adverse excursion stop.

Price path:

```text
 timestamp      open      high       low     close
2023-09-26 69.529999 70.940002 69.459999 70.570000
2023-09-27 70.790001 70.959999 69.639999 69.989998
2023-09-28 69.809998 70.050003 69.330002 69.389999
2023-09-29 69.589996 69.980003 69.099998 69.400002
2023-10-02 69.199997 69.290001 68.040001 68.489998
2023-10-03 68.239998 68.260002 67.370003 67.599998
2023-10-04 67.790001 68.800003 67.379997 68.680000
2023-10-05 68.339996 68.360001 65.019997 65.070000
2023-10-06 64.379997 64.410004 61.189999 63.360001
```

Fills, levels, and state reasons:

```text
 timestamp symbol side   quantity     price                                  reason  realized_pnl                                                                                                                                                                                                              metadata
2023-09-26   MDLZ  BUY 159.194957 69.557811                    natural grid layer 1      0.000000 {'direction': 1, 'grid_layer': 1, 'grid_level': 69.70999908447266, 'adjusted_grid_level': 63.91245269775391, 'stop_price': 68.45042550082405, 'tp_prices': [72.89499755266604, 76.29534281490211, 76.76999135563207]}
2023-09-29   MDLZ  BUY 199.977660 69.187886                    natural grid layer 2      0.000000  {'direction': 1, 'grid_layer': 2, 'grid_level': 69.1878856896697, 'adjusted_grid_level': 63.43376171960928, 'stop_price': 68.45042550082405, 'tp_prices': [72.89499755266604, 76.29534281490211, 76.76999135563207]}
2023-10-06   MDLZ SELL 359.172618 64.354245 campaign maximum adverse excursion stop  -1795.001496                                                                                                                                                                            {'close_fraction': 1.0, 'close_all': True}
```

Mechanics verdict: fills occur at the recorded next-open/limit rule, averaging is average-cost, both relationship legs share timestamps, and the exit reason matches the recorded terminal campaign state.

## C. Typical natural long grid campaign

Run: `natural_long_grid:PEP`; campaign: `natural_long_grid:PEP:2023-06-29T00:00:00`; reported P&L: $59.13; MAE/MFE: $42.69 / $87.17; final reason: natural grid kill.

Price path:

```text
 timestamp       open       high        low      close
2023-06-30 184.039993 185.520004 183.880005 185.220001
2023-07-03 184.300003 185.639999 183.470001 185.600006
2023-07-05 185.000000 186.690002 184.970001 186.580002
2023-07-06 185.809998 186.750000 184.889999 186.600006
2023-07-07 185.820007 185.880005 183.029999 183.080002
```

Fills, levels, and state reasons:

```text
 timestamp symbol side  quantity      price               reason  realized_pnl                                                                                                                                                                                                                   metadata
2023-06-30    PEP  BUY 32.230403 183.880005 natural grid layer 1      0.000000 {'direction': 1, 'grid_layer': 1, 'grid_level': 183.88000488281253, 'adjusted_grid_level': 163.8555450439453, 'stop_price': 177.67468380657382, 'tp_prices': [187.33139610037585, 194.28604716780163, 195.51425681615444]}
2023-07-07    PEP SELL 32.230403 185.745679    natural grid kill     60.131439                                                                                                                                                                                 {'close_fraction': 1.0, 'close_all': True}
```

Mechanics verdict: fills occur at the recorded next-open/limit rule, averaging is average-cost, both relationship legs share timestamps, and the exit reason matches the recorded terminal campaign state.

## D. Best residual grid campaign

Run: `residual_grid:SHW/XLB`; campaign: `residual_grid:SHW:2025-06-16T00:00:00`; reported P&L: $1,312.43; MAE/MFE: $-33.87 / $1,322.04; final reason: residual time stop.

Price path:

```text
 timestamp       open       high        low      close
2025-06-17 333.929993 335.160004 329.140015 331.029999
2025-06-18 331.640015 333.950012 329.899994 331.470001
2025-06-20 334.000000 337.179993 330.220001 333.500000
2025-06-23 333.420013 344.559998 331.709991 343.769989
2025-06-24 347.859985 349.450012 340.769989 345.690002
```

Fills, levels, and state reasons:

```text
 timestamp symbol side   quantity      price                            reason  realized_pnl                                     metadata
2025-06-17    SHW  BUY  24.432606 334.063565             residual grid layer 1      0.000000   {'direction': 1, 'z': -2.6806741239646676}
2025-06-17    XLB SELL 141.067707  43.922423 beta hedge: residual grid layer 1      0.000000 {'beta': 0.7597355128367225, 'direction': 1}
2025-06-18    SHW  BUY  30.751642 331.772671             residual grid layer 2      0.000000    {'direction': 1, 'z': -2.786856671578643}
2025-06-18    XLB SELL 173.051856  43.657529 beta hedge: residual grid layer 2      0.000000 {'beta': 0.7410950920988907, 'direction': 1}
2025-06-20    SHW  BUY  30.534356 334.133600             residual grid layer 3      0.000000   {'direction': 1, 'z': -2.4764930629337356}
2025-06-20    XLB SELL 168.242410  43.737499 beta hedge: residual grid layer 3      0.000000 {'beta': 0.7218184011571331, 'direction': 1}
2025-06-24    SHW SELL  85.718604 347.720841                residual time stop   1238.992954   {'close_fraction': 1.0, 'close_all': True}
2025-06-24    XLB  BUY 482.361973  43.582425                residual time stop     87.049829   {'close_fraction': 1.0, 'close_all': True}
```

Mechanics verdict: fills occur at the recorded next-open/limit rule, averaging is average-cost, both relationship legs share timestamps, and the exit reason matches the recorded terminal campaign state.

## E. Worst residual grid campaign

Run: `residual_grid:NEE/XLU`; campaign: `residual_grid:NEE:2024-10-30T00:00:00`; reported P&L: $-2,305.93; MAE/MFE: $-2,305.93 / $613.20; final reason: campaign maximum adverse excursion stop.

Price path:

```text
 timestamp      open      high       low     close
2024-10-31 78.389999 79.849998 78.139999 79.250000
2024-11-01 79.389999 79.459999 76.970001 77.349998
2024-11-04 77.349998 78.820000 77.099998 78.370003
2024-11-05 77.769997 78.790001 76.970001 78.650002
2024-11-06 74.300003 74.980003 72.690002 74.519997
2024-11-07 73.610001 75.089996 73.570000 74.620003
```

Fills, levels, and state reasons:

```text
 timestamp symbol side   quantity     price                                  reason  realized_pnl                                     metadata
2024-10-31    NEE  BUY 154.920762 78.421355                   residual grid layer 1      0.000000    {'direction': 1, 'z': -1.986435301278726}
2024-10-31    XLU SELL 231.977291 39.629142       beta hedge: residual grid layer 1      0.000000 {'beta': 0.7572924254585104, 'direction': 1}
2024-11-01    NEE  BUY 191.211717 79.421755                   residual grid layer 2      0.000000   {'direction': 1, 'z': -2.2146131380933127}
2024-11-01    XLU SELL 281.539684 39.934021       beta hedge: residual grid layer 2      0.000000 {'beta': 0.7409281776709636, 'direction': 1}
2024-11-04    NEE  BUY 196.254666 77.380938                   residual grid layer 3      0.000000   {'direction': 1, 'z': -2.5497113271490477}
2024-11-04    XLU SELL 282.815841 38.659529       beta hedge: residual grid layer 3      0.000000 {'beta': 0.7205327826266835, 'direction': 1}
2024-11-07    NEE SELL 542.387145 73.580557 campaign maximum adverse excursion stop  -2612.688557   {'close_fraction': 1.0, 'close_all': True}
2024-11-07    XLU  BUY 796.332816 38.985589 campaign maximum adverse excursion stop    324.095925   {'close_fraction': 1.0, 'close_all': True}
```

Mechanics verdict: fills occur at the recorded next-open/limit rule, averaging is average-cost, both relationship legs share timestamps, and the exit reason matches the recorded terminal campaign state.

## F. Best stock-pair campaign

Run: `stock_pair_grid:BAC/WFC`; campaign: `stock_pair_grid:BAC-WFC:2025-02-25T00:00:00`; reported P&L: $929.18; MAE/MFE: $-37.36 / $1,446.62; final reason: pair kill.

Price path:

```text
 timestamp      open      high       low     close
2025-02-26 44.040001 44.549999 43.860001 43.939999
2025-02-27 44.090000 44.779999 43.939999 44.119999
2025-02-28 44.320000 46.200001 44.200001 46.099998
2025-03-03 46.209999 46.959999 45.220001 45.560001
2025-03-04 44.730000 44.840000 42.029999 42.669998
```

Fills, levels, and state reasons:

```text
 timestamp symbol side   quantity     price                   reason  realized_pnl                                                   metadata
2025-02-26    BAC  BUY 253.937342 44.057617        pair grid layer 1      0.000000              {'direction': 1, 'beta': 0.33929255989894225}
2025-02-26    WFC SELL  49.698032 76.319458 hedge: pair grid layer 1      0.000000              {'direction': 1, 'beta': 0.33929255989894225}
2025-02-27    BAC  BUY 317.061713 44.107636        pair grid layer 2      0.000000               {'direction': 1, 'beta': 0.3303037816151666}
2025-02-27    WFC SELL  59.974017 76.959202 hedge: pair grid layer 2      0.000000               {'direction': 1, 'beta': 0.3303037816151666}
2025-02-28    BAC  BUY 315.416315 44.337728        pair grid layer 3      0.000000              {'direction': 1, 'beta': 0.31756918286829533}
2025-02-28    WFC SELL  57.624341 77.009185 hedge: pair grid layer 3      0.000000              {'direction': 1, 'beta': 0.31756918286829533}
2025-03-03    BAC SELL 295.471790 46.191515                 pair TP1    595.769813 {'close_fraction': 0.3333333333333333, 'close_all': False}
2025-03-03    WFC  BUY  55.765464 78.891545                 pair TP1   -117.395905 {'close_fraction': 0.3333333333333333, 'close_all': False}
2025-03-04    BAC SELL 590.943579 44.712108                pair kill    317.293237                 {'close_fraction': 1.0, 'close_all': True}
2025-03-04    WFC  BUY 111.530927 75.500189                pair kill    143.449201                 {'close_fraction': 1.0, 'close_all': True}
```

Mechanics verdict: fills occur at the recorded next-open/limit rule, averaging is average-cost, both relationship legs share timestamps, and the exit reason matches the recorded terminal campaign state.

## G. Worst stock-pair campaign

Run: `stock_pair_grid:C/GS`; campaign: `stock_pair_grid:C-GS:2022-10-28T00:00:00`; reported P&L: $-2,154.63; MAE/MFE: $-2,154.63 / $-85.83; final reason: campaign maximum adverse excursion stop.

Price path:

```text
 timestamp      open      high       low     close
2022-10-31 45.709999 46.220001 45.570000 45.860001
2022-11-01 46.299999 46.480000 46.000000 46.220001
2022-11-02 46.130001 47.009998 45.540001 45.549999
2022-11-03 45.160000 45.410000 44.509998 44.580002
2022-11-04 44.610001 45.450001 44.270000 45.130001
```

Fills, levels, and state reasons:

```text
 timestamp symbol side   quantity      price                                  reason  realized_pnl                                     metadata
2022-10-31      C  BUY 153.490800  45.728283                       pair grid layer 1      0.000000 {'direction': 1, 'beta': 1.4278103966236242}
2022-10-31     GS SELL  29.371124 340.933579                hedge: pair grid layer 1      0.000000 {'direction': 1, 'beta': 1.4278103966236242}
2022-11-01      C  BUY 189.418587  46.318519                       pair grid layer 2      0.000000  {'direction': 1, 'beta': 1.394061716799647}
2022-11-01     GS SELL  35.424429 344.991953                hedge: pair grid layer 2      0.000000  {'direction': 1, 'beta': 1.394061716799647}
2022-11-02      C  BUY 190.116632  46.148453                       pair grid layer 3      0.000000 {'direction': 1, 'beta': 1.3508546326494126}
2022-11-02     GS SELL  34.080617 347.480947                hedge: pair grid layer 3      0.000000 {'direction': 1, 'beta': 1.3508546326494126}
2022-11-03      C  BUY 233.040225  45.178064                       pair grid layer 4      0.000000 {'direction': 1, 'beta': 1.3015364038715669}
2022-11-03     GS SELL  39.417251 347.361000                hedge: pair grid layer 4      0.000000 {'direction': 1, 'beta': 1.3015364038715669}
2022-11-04      C SELL 766.066243  44.592157 campaign maximum adverse excursion stop   -933.807926   {'close_fraction': 1.0, 'close_all': True}
2022-11-04     GS  BUY 138.293421 354.141600 campaign maximum adverse excursion stop  -1206.327213   {'close_fraction': 1.0, 'close_all': True}
```

Mechanics verdict: fills occur at the recorded next-open/limit rule, averaging is average-cost, both relationship legs share timestamps, and the exit reason matches the recorded terminal campaign state.

## H. Campaign killed by stop

Run: `residual_grid:CSCO/XLK`; campaign: `residual_grid:CSCO:2022-10-25T00:00:00`; reported P&L: $47.37; MAE/MFE: $47.37 / $100.98; final reason: residual kill.

Price path:

```text
 timestamp  open  high       low     close
2022-10-26 44.93 45.23 44.279999 44.380001
2022-10-27 44.77 45.09 44.360001 44.419998
```

Fills, levels, and state reasons:

```text
 timestamp symbol side   quantity     price                            reason  realized_pnl                                      metadata
2022-10-26   CSCO SELL 167.540043 44.912028             residual grid layer 1      0.000000    {'direction': -1, 'z': 1.7928289451758024}
2022-10-26    XLK  BUY  77.874366 62.640048 beta hedge: residual grid layer 1      0.000000 {'beta': 0.6477655958879743, 'direction': -1}
2022-10-27   CSCO  BUY 167.540043 44.787908                     residual kill     20.795045    {'close_fraction': 1.0, 'close_all': True}
2022-10-27    XLK SELL  77.874366 63.014785                     residual kill     29.182425    {'close_fraction': 1.0, 'close_all': True}
```

Mechanics verdict: fills occur at the recorded next-open/limit rule, averaging is average-cost, both relationship legs share timestamps, and the exit reason matches the recorded terminal campaign state.

## I. Campaign closed by time stop

Run: `residual_grid:ORCL/XLK`; campaign: `residual_grid:ORCL:2024-12-16T00:00:00`; reported P&L: $25.40; MAE/MFE: $-29.42 / $288.04; final reason: residual time stop.

Price path:

```text
 timestamp       open       high        low      close
2024-12-17 170.750000 172.990005 169.270004 169.710007
2024-12-18 169.410004 171.229996 165.360001 165.410004
2024-12-19 167.550003 171.000000 167.399994 168.789993
2024-12-20 167.729996 171.259995 165.630005 169.660004
2024-12-23 169.589996 169.619995 167.169998 169.139999
2024-12-24 169.699997 171.770004 169.029999 171.410004
```

Fills, levels, and state reasons:

```text
 timestamp symbol side  quantity      price                            reason  realized_pnl                                     metadata
2024-12-17   ORCL  BUY 19.087644 170.818300             residual grid layer 1      0.000000    {'direction': 1, 'z': -2.745974842668488}
2024-12-17    XLK SELL 41.991790 119.817052 beta hedge: residual grid layer 1      0.000000 {'beta': 1.5443429223918554, 'direction': 1}
2024-12-18   ORCL  BUY 24.048278 169.477768             residual grid layer 2      0.000000   {'direction': 1, 'z': -2.4884854847840407}
2024-12-18    XLK SELL 47.611651 120.346839 beta hedge: residual grid layer 2      0.000000 {'beta': 1.4070147070162171, 'direction': 1}
2024-12-24   ORCL SELL 43.135922 169.632117                residual time stop    -18.929605   {'close_fraction': 1.0, 'close_all': True}
2024-12-24    XLK  BUY 89.603441 119.507783                residual time stop     52.935570   {'close_fraction': 1.0, 'close_all': True}
```

Mechanics verdict: fills occur at the recorded next-open/limit rule, averaging is average-cost, both relationship legs share timestamps, and the exit reason matches the recorded terminal campaign state.

## J. Campaign skipped due to event

No pending entry reached an event day in the corrected historical run. Golden path 07 verifies deterministic cancellation; the historical event file remains retrospective and is not point-in-time complete.

## K. Campaign where breakout should have happened

Run: `residual_grid:MSFT/XLK`; campaign: `residual_grid:MSFT:2022-11-01T00:00:00`; reported P&L: $39.19; MAE/MFE: $-69.81 / $39.88; final reason: convert residual grid to breakout.

Price path:

```text
 timestamp       open       high        low      close
2022-11-02 229.460007 231.300003 220.039993 220.100006
2022-11-03 220.089996 220.410004 213.979996 214.250000
```

Fills, levels, and state reasons:

```text
 timestamp symbol side   quantity      price                            reason  realized_pnl                                     metadata
2022-11-02   MSFT  BUY  38.168490 229.551791             residual grid layer 1      0.000000   {'direction': 1, 'z': -2.9372451427332606}
2022-11-02    XLK SELL 137.734281  63.329658 beta hedge: residual grid layer 1      0.000000 {'beta': 0.9963477740111678, 'direction': 1}
2022-11-03   MSFT SELL  38.168490 220.001960 convert residual grid to breakout   -364.502607   {'close_fraction': 1.0, 'close_all': True}
2022-11-03    XLK  BUY 137.734281  60.379142 convert residual grid to breakout    406.387199   {'close_fraction': 1.0, 'close_all': True}
```

Mechanics verdict: fills occur at the recorded next-open/limit rule, averaging is average-cost, both relationship legs share timestamps, and the exit reason matches the recorded terminal campaign state.

## L. Campaign where breakout fakeout occurred

No corrected campaign was labelled failed breakout. Golden path 10 demonstrates rejection of a break/reclaim fakeout.
