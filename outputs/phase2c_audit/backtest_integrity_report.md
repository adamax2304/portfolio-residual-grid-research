# Phase 2C backtest integrity and strategy mechanics audit

## Executive conclusion

The Phase 2A/2B direction — **NO-GO for live trading** — remains correct, but their numeric results are **not mechanically trustworthy as final evidence**. Ten implementation defects were found and fixed. The most material were natural-grid market fills instead of resting limits, breakout-before-kill ordering, failure to recheck queued orders against event dates, short-leg event-direction/exit-lead handling, and adjusted execution OHLC. Corrected research reruns were produced for the complete Phase 2A and Phase 2B run sets; their metrics changed enough that the archived figures are classified **PARTIALLY_INVALID**.

The corrected engine passes deterministic fill, ordering, inventory, residual-math, state-transition, event, and exact P&L checks. It remains `PASS_WITH_ISSUES` because daily OHLC cannot reveal intrabar paths, natural-grid grid-versus-breakout attribution shares a campaign ledger, event dates are retrospective rather than point-in-time, and event business days do not include a full exchange-holiday calendar.

## Required status block

```text
BACKTEST ENGINE STATUS: PASS_WITH_ISSUES
PHASE 2A/2B VALIDITY: PARTIALLY_INVALID
BUGS FOUND: YES
LOOKAHEAD RISK: NO
FILL MODEL STATUS: PASS
GRID MECHANICS STATUS: PASS
STOP LOGIC STATUS: PASS
TAKE_PROFIT LOGIC STATUS: PASS
RESIDUAL MATH STATUS: PASS
EVENT FILTER STATUS: PASS
P&L RECONCILIATION: PASS
LIVE TRADING STATUS: NO-GO
NEXT RECOMMENDED PHASE: Phase 2D — frozen-engine independent data replication and intraday ordering validation
```

`LOOKAHEAD RISK: NO` describes the corrected engine. The archived engine had a small financing-mark timing leak (B005); signal beta/z/ATR/range calculations themselves were causal.

## Bugs, expected behavior, actual behavior, and fixes

```text
  id                                                                                                                                 description                                                                    modules                        strategies                                                                                                                                     expected                                                                                                                                    actual                                                                                                                                   fix
B001                                            Natural-grid layers were close-triggered next-open market orders, not predefined resting limits.                  strategies/natural_grid.py; backtest/engine.py; models.py                 natural_long_grid                                                  Levels are fixed at campaign creation and fill only when a candle trades through the limit.             A close below a recalculated level queued a market order for the next open; the theoretical level did not constrain the fill.                 Added explicit LIMIT orders, locked entry-time ATR geometry, GTC handling, range-bound levels, and no-touch behavior.
B002                                                            Residual/pair breakout conversion was checked before the z-score kill threshold.                       strategies/residual_grid.py; strategies/pair_grid.py    residual_grid; stock_pair_grid                                                                            Kill/invalidation always has priority over optional continuation.                                                           A relationship already beyond kill could be converted to breakout continuation.                                         Moved kill evaluation ahead of breakout evaluation and added a deterministic regression test.
B003                                                  A queued entry/add was not revalidated against an event window at its execution timestamp.                                   backtest/engine.py; all strategy modules                               all                                                                          Known events block both new campaigns and new adds before the fill.                                                            Yesterday's safe signal could fill at today's open inside an exclusion window.                                                         Added pre-open pending-order validation and explicit cancellation audit rows.
B004                                                                                      Adjusted OHLC was used for simulated execution prices. data/yahoo_finance.py; data/alpha_vantage.py; all strategy prepare methods                all real-data runs                                              Raw tradable OHLC drives fills; adjusted OHLC drives long-horizon indicators and relationships.                                                                         The same total-return-adjusted OHLC drove both signals and fills.                       Added immutable raw-with-adjusted-indicator caches and separated engine execution columns from feature columns.
B005                                                            Financing was valued with the current bar close before that close was available.                                                         backtest/engine.py short residual and pair campaigns                                                                                                Overnight financing uses the last known mark.                                                      The loop updated prices to the current close before charging elapsed-time financing.                                                         Financing is now charged from the prior close before current-open processing.
B006                                                      Same-decision pair legs were risk-approved independently against stale gross exposure.                                        risk/manager.py; backtest/engine.py    residual_grid; stock_pair_grid                                                                         Both legs are accepted/scaled atomically against aggregate headroom.                                   Each leg saw the same pre-order portfolio, permitting joint limit overshoot or an unbalanced rejection.                                                               Added atomic batch sizing and all-or-none minimum/open-position checks.
B007                                              Relationship breakout confirmation omitted configured participation and break-distance checks.                       strategies/residual_grid.py; strategies/pair_grid.py    residual_grid; stock_pair_grid                           Persistent boundary break, minimum distance, participation, stable relationship, and optional retest are required.                                                                                    Persistent z closes alone could activate continuation.                   Added residual-distance buffer, volume/true-range participation, scored confirmation, and consecutive-close checks.
B008                                          Daily loss reference reset after the daily close, making the daily kill ineffective on daily bars.                                                         backtest/engine.py                    all daily runs                                                                                   A new trading day begins from the prior known equity mark.                                    The day-start mark was assigned after marking the current close, so the loss comparison began at zero.                                                           Moved day/week reference initialization to the start of the timestamp loop.
B009                                       Event checks did not consistently identify the actually short leg of an active relationship campaign.           strategies/residual_grid.py; strategies/pair_grid.py; phase2c.py    residual_grid; stock_pair_grid Earnings apply to both symbols; ex-dividend rules apply only to the leg that is or will be short, using the campaign direction while active. Residual checks could derive short status from the current signal instead of the active campaign; pair checks treated both legs as short.                              Split common-event and short-leg checks and bind the latter to prospective or active campaign direction.
B010 A close-generated short-leg dividend exit could execute on the ex-dividend open, after the economic exposure was already carried overnight.                       strategies/residual_grid.py; strategies/pair_grid.py    residual_grid; stock_pair_grid                                                                          An existing short leg is flat before the ex-dividend session opens.                               The configured buffer was checked at close without reserving a next-open execution bar or a holiday margin. Existing-position ex-dividend checks now add two conservative business-day lead units; new-entry checks retain the configured window.
```

## Before/after representative metrics

These are combined-stack before/after comparisons, not an attempt to attribute profit to one fix and not evidence of edge.

```text
                   run  oos_return_before  profit_factor_before  expectancy_usd_before  max_drawdown_before  campaigns_before  oos_return_after  profit_factor_after  expectancy_usd_after  max_drawdown_after  campaigns_after  oos_return_delta  profit_factor_delta  expectancy_usd_delta  max_drawdown_delta  campaigns_delta
natural_long_grid:CSCO          -0.001254              0.932364              -6.598180            -0.043176                19          0.001071             1.067651              7.138210           -0.013268               15          0.002324             0.135287             13.736390            0.029908               -4
 residual_grid:JPM/XLF           0.004092              1.222171              20.462086            -0.010696                20          0.005577             1.360842             29.351400           -0.010685               19          0.001484             0.138671              8.889314            0.000010               -1
  stock_pair_grid:MA/V           0.011170              3.535305              79.787928            -0.006828                14         -0.010634             0.426536            -75.958542           -0.013998               14         -0.021805            -3.108769           -155.746470           -0.007170                0
```

The full comparison is in `bug_impact_metrics.csv`. Phase 2A/2B outputs themselves remain unchanged.

## Answers to the 20 audit questions

1. **Are Phase 2A/2B results mechanically trustworthy?** Partly. The residual signal math and P&L ledger were sound, but execution/state defects materially changed campaign counts and returns.
2. **Were bugs found?** Yes: B001–B010 above.
3. **Which prior results are invalidated?** Natural-grid metrics are materially invalidated. Residual/pair metrics are partially invalidated by kill priority, breakout confirmation, event revalidation, raw execution, risk atomicity, daily kill timing, and financing timing.
4. **Fills conservative/correct?** Corrected market orders fill next open; limits/stops require an OHLC touch; gaps use the adverse open; stop/TP ambiguity is adverse-first; fills are clamped to observed high/low.
5. **Lookahead?** Corrected signals use current close with next-bar execution; beta/correlation/z moments use t-1 fits. No signal lookahead was found.
6. **Grid levels?** Corrected natural levels are locked from entry-time ATR, constrained to the range, and submitted as GTC limits. Relationship levels are explicitly z-space signal levels.
7. **Averaging?** Adds occur only at predefined natural limits or relationship z thresholds. Inventory uses one consistent average-cost ledger; no double-counting was found after atomic sizing.
8. **Stops?** Baseline natural stop is close/structure confirmed and executes next open; residual/pair kill is close-z based. Diagnostic alternatives show sensitivity but are not selected as edge. See `stop_logic_audit.md`.
9. **Take profits?** Natural legs carry shared campaign TP references and close proportionally at midpoint/upper-range stages. Relationship legs close together at z targets. All exits cover costs only when geometry permits; narrow cases are flagged.
10. **Breakout continuation?** Corrected relationship continuation requires kill priority, distance, consecutive closes, participation, relationship validity, and optional retest. Natural continuation retains the existing long exposure but cancels grid orders; it does not double size.
11. **Residual math?** PASS. Formula includes the required OLS intercept: `ln(A) - alpha - beta*ln(B)`. Manual recomputations match to floating tolerance.
12. **Event filters?** Mechanics PASS: pre-signal checks, pending-order rechecks, no adds, and force-exit behavior are consistent. Calendar fidelity remains limited.
13. **Costs/slippage?** Both entry/exit and both pair legs pay commission and adverse spread/slippage; shorts additionally accrue borrow cost. Cost-to-step diagnostics flag uneconomic grids.
14. **Adjusted/unadjusted prices?** Corrected. Raw fills; adjusted indicators. Archived Phase 2A/2B used adjusted fills.
15. **Parameters mechanically reasonable?** Mixed. Diagnostic OAT grids show whether density/stop/cost behavior is mechanically sparse or sensitive; no best value was promoted.
16. **Lack of edge or flawed implementation?** Prior poor results cannot be cleanly attributed because the implementation was flawed. Corrected results remain research-only and do not satisfy an independent live gate.
17. **What must be fixed before new research?** Remaining items: point-in-time event source, exchange calendar, lower-timeframe bracket ordering, explicit natural grid/breakout sub-ledgers, and an independent data vendor.
18. **Rerun Phase 2A/2B?** Yes. Complete corrected primary run sets are saved under this audit directory; acceptance must be reassessed only in an independent Phase 2D, not here.
19. **Live trading status?** NO-GO.
20. **Recommended next phase?** Freeze this corrected engine and run Phase 2D independent-vendor daily replication plus 5m/15m intrabar ordering validation, without tuning.

## Mechanical diagnostics, not optimization

```text
                   run             dimension  original_expectancy_usd  positive_variant_share campaign_range                            mechanical_diagnosis
natural_long_grid:CSCO           grid_levels                 7.138210                    1.00          15-15        consistent sign across diagnostic values
natural_long_grid:CSCO         grid_step_atr                 7.138210                    0.80          15-15 sign-sensitive; requires independent validation
natural_long_grid:CSCO        max_grid_depth                 7.138210                    1.00          15-15        consistent sign across diagnostic values
natural_long_grid:CSCO          stop_variant                 7.138210                    0.75          15-16 sign-sensitive; requires independent validation
natural_long_grid:CSCO               tp_mode                 7.138210                    1.00          16-21        consistent sign across diagnostic values
 residual_grid:JPM/XLF           beta_window                29.351400                    1.00          15-19        consistent sign across diagnostic values
 residual_grid:JPM/XLF           hedge_ratio                29.351400                    1.00          19-19        consistent sign across diagnostic values
 residual_grid:JPM/XLF               z_entry                29.351400                    1.00           6-24        consistent sign across diagnostic values
 residual_grid:JPM/XLF                z_exit                29.351400                    1.00          19-19        consistent sign across diagnostic values
 residual_grid:JPM/XLF                z_kill                29.351400                    1.00          19-20        consistent sign across diagnostic values
  stock_pair_grid:MA/V correlation_threshold               -75.958542                    0.00          10-14        consistent sign across diagnostic values
  stock_pair_grid:MA/V    stationarity_proxy               -75.958542                    0.00          14-14        consistent sign across diagnostic values
  stock_pair_grid:MA/V               z_entry               -75.958542                    0.25           8-22 sign-sensitive; requires independent validation
  stock_pair_grid:MA/V                z_exit               -75.958542                    0.00          14-14        consistent sign across diagnostic values
  stock_pair_grid:MA/V                z_kill               -75.958542                    0.00          14-14        consistent sign across diagnostic values
```

No variant in this table is designated “best” or an edge. A sign change across adjacent values is evidence of fragility, not permission to select the favorable value.

## Integrity checks

- P&L reconciliation rows: 4,271; failures: 0; maximum absolute discrepancy: 2.910e-11 USD.
- Invalid allowed-map transitions: 0; exposure/state issues: 0.
- Corrected natural grid levels outside their entry range: 0.
- Corrected fills admitted inside the configured event window: 0.
- Corrected campaigns crossing a relevant blocked event: 0.

## Reliability boundary

This audit validates mechanics, not profitability. Even a corrected run with a high PF or positive expectancy is not a Phase 2C edge finding. The data and rules were inspected after prior results, the sample is vendor-revisable, and no independent holdout/vendor replication has occurred.
