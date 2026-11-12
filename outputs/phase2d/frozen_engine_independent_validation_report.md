# Phase 2D — Frozen Engine Independent Validation

## Executive conclusion

Phase 2D stopped at the mandatory independent-data gate. The frozen engine, universe, XNYS calendar, dual raw/adjusted adapter, conservative intraday fills, and separated grid/breakout accounting are implemented and mechanically tested, but **no independent market result was produced**. The environment contains no Alpha Vantage or alternative licensed-provider credential, and Alpha Vantage's multi-year intraday endpoint requires credentialed premium access. Substituting yfinance would violate the protocol.

This is not evidence that any strategy works or fails. It means the independent replication question remains unanswered. Phase 2A/2B remain partially invalid numerically, the Phase 2C mechanical findings stand, and live trading remains NO-GO.

## Frozen protocol and preservation

- Frozen universe: 25 symbols; selected before Phase 2D results.
- Baseline: 5m RTH raw execution; 15m robustness; 2021-09-01 through 2026-09-04; minimum two years.
- Parameters: frozen; diagnostics preregistered and not used for selection.
- Prior artifact integrity: PASS across 94 files.
- Automated tests: PASS (`.............................................                            [100%]`).
- Calendar validation: PASS.

## Answers to the required questions

1. **Did the corrected engine replicate on independent intraday data?** Not evaluated; no qualifying dataset was available.
2. **Were Phase 2A/2B conclusions confirmed?** Inconclusive. Their live NO-GO remains the only safe status, but independent directional replication did not occur.
3. **Does natural long still outperform residual stock-to-ETF?** Inconclusive.
4. **Are stock-to-stock pairs still weak?** Inconclusive.
5. **Does breakout help or hurt?** Inconclusive on markets. Separate attribution now reconciles mechanically.
6. **Were grids too narrow, wide, sparse, or badly stopped?** Inconclusive; diagnostic families were registered but not run.
7. **Does averaging improve campaign entry?** Inconclusive on independent data.
8. **Are stop/TP mechanics realistic on 5m/15m?** Mechanical rules pass deterministic tests; empirical behavior is unvalidated.
9. **How much did daily OHLC distort results?** Not measurable without the independent intraday comparison.
10. **Robust after costs/slippage?** Not evaluated.
11. **Robust after removing best campaign/month?** Not evaluated.
12. **Remaining leakage/accounting issue?** No known mechanical lookahead or reconciliation defect in tests; event provenance and market-data correctness remain uncertified.
13. **Ready for deeper research?** No strategy is promoted. Resume the same frozen Phase 2D only after the data gate passes.
14. **Ready for paper/live?** No.
15. **Exact next phase?** `Phase 2D-R`: provision a licensed independent intraday source with raw/adjusted 5m or 15m RTH data and historical events, verify entitlement/coverage, then rerun this unchanged snapshot from the beginning.

## Required conclusion block

```text
BACKTEST ENGINE STATUS: PASS_WITH_ISSUES
INDEPENDENT DATA STATUS: FAIL
PHASE 2A/2B CORRECTED CONCLUSION: INCONCLUSIVE
NATURAL LONG GRID STATUS: INCONCLUSIVE
RESIDUAL STOCK-TO-ETF STATUS: INCONCLUSIVE
STOCK-TO-STOCK PAIRS STATUS: INCONCLUSIVE
BREAKOUT CONTINUATION STATUS: INCONCLUSIVE
GRID PARAMETER REASONABLENESS: MIXED
STOP/TP MECHANICS: MIXED
LIVE TRADING STATUS: NO-GO
RESEARCH CONTINUATION: NO-GO
NEXT RECOMMENDED PHASE: PHASE 2D-R — resume the unchanged frozen protocol after licensed independent intraday and event data are provisioned
```

PHASE 2D STATUS: **NO-GO-DATA**
