# HF Data Library Phase 2D-R-LITE report

HF SOURCE CLASSIFICATION: **LIMITED**

- Public catalog coverage: **25/25** (PASS)
- `HFDL_API_KEY` present: **False**
- Complete authenticated local candle cache: **True**
- 5m data-quality coverage: **25/25**
- 15m data-quality coverage: **25/25**
- Calendar-invalid bars removed from working views: **85 (5m), 39 (15m)**
- R-LITE status: **COMPLETED_LIMITED**
- Reason: Price-only adjusted/IEX-limited run completed; not eligible for Phase 2D acceptance

## Frozen LITE metrics

- Completed rows: **58**
- Active runs: **26/58**
- Zero-trade runs: **32/58**
- Runs with positive return: **5/58**
- Runs passing PF > 1.15 + positive expectancy + >=30 trades: **0/58**

| timeframe | family | runs | active_runs | positive_return | pf_gt_115 | median_return | median_pf | total_trades |
|---|---|---|---|---|---|---|---|---|
| 5min | natural_long_grid | 11 | 0 | 0 | 0 | 0.000000 | 0.000000 | 0 |
| 5min | residual_grid | 11 | 11 | 0 | 0 | -0.159485 | 0.337863 | 2025 |
| 5min | stock_pair_grid | 7 | 1 | 1 | 1 | 0.000000 | 0.000000 | 1 |
| 15min | natural_long_grid | 11 | 2 | 1 | 1 | 0.000000 | 0.000000 | 2 |
| 15min | residual_grid | 11 | 11 | 2 | 1 | -0.098542 | 0.406548 | 1006 |
| 15min | stock_pair_grid | 7 | 1 | 1 | 1 | 0.000000 | 0.000000 | 3 |

No run passes the minimum combined research screen. All PF > 1.15 positive-expectancy runs have at most 5 trades. The closest sufficiently active run is residual_grid:CSCO/XLK on 15min with 50 trades and PF 1.015.

## Mandatory limitations

- Post-March-2022 bars are IEX-only and represent roughly 2–3% of consolidated volume.
- OHLCV is split/dividend adjusted; raw as-traded execution prices are unavailable.
- Neither Raw nor Clean version contains extended-hours bars; the clock range is RTH.
- Missing no-trade minutes are preserved; no LOCF gap fill is permitted.
- The library's 1,391-symbol universe is a circa-2022/2023 snapshot and is survivorship-biased historically.
- This is price-only LITE: point-in-time earnings/dividend/split events were not available without separate event-provider keys.
- Frozen lookback values are unchanged and therefore interpreted as bar counts on both 5m and 15m; this is a mechanics trial, not an intraday parameter calibration.
- LITE applies a six-month warm-up and then one frozen remaining-period run; it is not the full rolling monthly walk-forward required by Phase 2D.

## Decision

The public catalog and candle gate pass. R-LITE completed on the frozen parameters, but 0/58 runs pass the minimum combined research screen. It remains limited research because HF bars are adjusted and IEX-only after March 2022. Live trading remains NO-GO.
