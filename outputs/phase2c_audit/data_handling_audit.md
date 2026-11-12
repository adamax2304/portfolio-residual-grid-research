# Data handling audit

## Result

PASS_WITH_ISSUES. Corrected Phase 2C runs use raw, tradable Yahoo OHLC for fills and split/dividend-adjusted OHLC for indicators, beta, correlation, residuals, ATR, ADX, ranges, and breakout confirmation. The two views are stored together in immutable `data/real/raw/yahoo_phase2c/*_raw_with_adjusted_indicators.csv` caches; Phase 2A/2B caches were not overwritten.

```text
symbol  rows      start        end  duplicates  missing_ohlcv  nonpositive_prices  outlier_abs_return_gt_35pct  adjustment_factor_min  adjustment_factor_max timezone  raw_adjusted_close_different_rows
  AAPL  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.969138                    1.0     None                               1490
  ABBV  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.793073                    1.0     None                               1472
   ACN  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.908439                    1.0     None                               1468
   AEP  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.807385                    1.0     None                               1490
   AMT  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.838079                    1.0     None                               1451
  AMZN  1510 2020-09-01 2026-09-04           0              0                   0                            0               1.000000                    1.0     None                                  0
   APD  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.864235                    1.0     None                               1463
   AXP  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.928622                    1.0     None                               1464
   BAC  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.860849                    1.0     None                               1509
   BMY  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.790287                    1.0     None                               1464
     C  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.813938                    1.0     None                               1485
   CAT  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.898295                    1.0     None                               1475
    CL  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.868270                    1.0     None                               1475
   COP  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.807297                    1.0     None                               1495
  COST  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.916211                    1.0     None                               1479
  CSCO  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.842696                    1.0     None                               1465
   CVX  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.775183                    1.0     None                               1497
    DE  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.925839                    1.0     None                               1462
   DUK  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.793121                    1.0     None                               1494
   EOG  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.758929                    1.0     None                               1474
  EQIX  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.891417                    1.0     None                               1497
   FCX  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.929285                    1.0     None                               1472
    GE  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.972397                    1.0     None                               1465
 GOOGL  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.990574                    1.0     None                               1509
    GS  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.870444                    1.0     None                               1506
    HD  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.857298                    1.0     None                               1508
   HON  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.886838                    1.0     None                               1494
   HPE  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.835530                    1.0     None                               1453
   HPQ  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.806061                    1.0     None                               1449
   IBM  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.785411                    1.0     None                               1490
   JNJ  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.847963                    1.0     None                               1501
   JPM  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.858015                    1.0     None                               1465
   KHC  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.744733                    1.0     None                               1509
    KO  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.835622                    1.0     None                               1452
   LIN  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.917284                    1.0     None                               1508
   LLY  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.939588                    1.0     None                               1494
   LOW  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.895042                    1.0     None                               1477
    MA  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.966212                    1.0     None                               1468
   MCD  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.869780                    1.0     None                               1506
  MDLZ  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.857512                    1.0     None                               1462
   MDT  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.837507                    1.0     None                               1460
  META  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.991295                    1.0     None                               1452
    MO  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.630507                    1.0     None                               1452
   MRK  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.828284                    1.0     None                               1452
    MS  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.832521                    1.0     None                               1484
  MSFT  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.951001                    1.0     None                               1498
   NEE  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.857165                    1.0     None                               1504
   NEM  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.839632                    1.0     None                               1508
   NKE  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.905439                    1.0     None                               1506
  NVDA  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.995687                    1.0     None                               1445
     O  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.739255                    1.0     None                               1505
  ORCL  1510 2020-09-01 2026-09-04           0              0                   0                            1               0.920109                    1.0     None                               1469
   PEP  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.819993                    1.0     None                               1509
   PFE  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.737519                    1.0     None                               1479
    PG  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.858428                    1.0     None                               1479
   PLD  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.846374                    1.0     None                               1453
   QQQ  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.966390                    1.0     None                               1456
   RTX  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.875686                    1.0     None                               1494
  SBUX  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.873450                    1.0     None                               1494
   SHW  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.947948                    1.0     None                               1499
   SLB  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.878458                    1.0     None                               1507
    SO  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.799667                    1.0     None                               1495
   SPG  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.724453                    1.0     None                               1448
   SPY  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.920914                    1.0     None                               1455
     T  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.673157                    1.0     None                               1469
  TMUS  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.950806                    1.0     None                               1504
   UNH  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.902454                    1.0     None                               1452
   UNP  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.876664                    1.0     None                               1505
     V  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.957189                    1.0     None                               1491
    VZ  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.698225                    1.0     None                               1469
   WFC  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.872792                    1.0     None                               1489
   WMT  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.925010                    1.0     None                               1499
   XLB  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.889331                    1.0     None                               1456
   XLC  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.942983                    1.0     None                               1456
   XLE  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.792729                    1.0     None                               1456
   XLF  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.899526                    1.0     None                               1456
   XLI  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.914149                    1.0     None                               1456
   XLK  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.955027                    1.0     None                               1456
   XLP  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.853691                    1.0     None                               1456
  XLRE  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.816693                    1.0     None                               1456
   XLU  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.833086                    1.0     None                               1456
   XLV  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.908039                    1.0     None                               1456
   XLY  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.952917                    1.0     None                               1456
   XOM  1510 2020-09-01 2026-09-04           0              0                   0                            0               0.782361                    1.0     None                               1495
```

## Checks and limitations

- Splits/dividends: `adjustment_factor = Adj Close / Close`; the same factor adjusts all indicator OHLC. Actions remain explicit columns. Raw OHLC drives execution.
- Missing/duplicate candles: shown above; pair preparation uses an inner timestamp join, so unmatched dates cannot create forward fills.
- Timezone/RTH: daily bars are timezone-naive exchange dates and represent the regular US daily session. Intraday Phase 2A caches were not revalidated here.
- Trading calendar: daily indexes come from the provider. Event distance uses weekdays (`numpy.busday_count`), not the complete NYSE holiday calendar; this is a known event-window issue.
- Corporate actions/outliers: adjusted indicators remove mechanical split/dividend discontinuities. Raw fills around corporate-action dates are protected by the event filter, but Yahoo's repair/history is vendor-revisable.
- Point-in-time limitation: Yahoo earnings history is retrospective. It is not a survivorship-free, point-in-time event database.
