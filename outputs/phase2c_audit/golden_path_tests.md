# Phase 2C golden-path deterministic tests

These fixtures use hand-specified OHLC paths and zero costs where exact arithmetic is the subject of the test. Execution-cost direction is tested separately. The automated source is `tests/test_phase2c_golden_paths.py`.

```text
                         path                                                         input                                                           manual expectation result
   01 clean range oscillation     3 buy limits at 99/98/97; proportional exits at 100/99/98 All touched layers fill; all exposure closes; exact cash-flow P&L reconciles   PASS
 02 partial range oscillation Only 99/98 touched; 97 remains live until exit invalidates it                 Two fills only; untouched order is cancelled on GRID_EXITING   PASS
           03 clean breakdown                            Two fills, invalidation, gap lower            No new add in KILL; remaining grid cancelled; position liquidated   PASS
          04 gap through stop                            Sell stop 95; next candle opens 90                                   Fill at conservative open 90, not ideal 95   PASS
   05 same-candle TP and stop                 Long stop 96 and target 104 inside 95-105 bar                                      STOP selected by adverse-first resolver   PASS
                   06 no-fill                                   Buy limit 98; candle low 99                                                 No fill; GTC remains pending   PASS
           07 event exclusion                      Queued entry reaches known earnings date                                                  Entry cancelled before open   PASS
   08 existing-position event                                    Position open before event         Configured policy is force exit: signal on event bar, fill next open   PASS
          09 breakout success                 Two closes beyond boundary plus participation                                               Continuation confirmation true   PASS
          10 breakout fakeout                                         Break, reclaim, break           Not confirmed because the last required closes are not consecutive   PASS
   11 residual mean reversion                                              z=-1.6, beta=1.2                                         Long stock / short 1.2x ETF notional   PASS
12 residual divergence / kill                         Long residual campaign reaches z=-3.2                              KILL evaluated before breakout; both legs close   PASS
```

## Accounting convention

The production engine uses average-cost inventory consistently. Natural-grid exits are campaign-level proportional scale-outs; every entry leg carries the same three campaign TP references in metadata. The clean-range fixture therefore checks exact aggregate cash flow and average-cost realized P&L, not FIFO or LIFO lot selection.

## Fill timing contract

Signals evaluated from candle *t* close become orders after that close. Market orders first become eligible at candle *t+1* open. Resting limits/stops may fill inside *t+1* only when its OHLC range touches the requested price. Stops are processed before discretionary limits/TPs on an ambiguous candle. Full fills are the baseline (`partial_fill_ratio=1.0`).
