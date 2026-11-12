# Phase 3A — Edge failure diagnostic report

## Executive conclusion

Phase 3A does not find a production-ready or paper-trading edge. It explains the frozen R-LITE result at campaign level, but the HF source remains insufficient for definitive market validation. The unchanged live status is **NO-GO**.

MAIN LOSS DRIVER: NO_MEAN_REVERSION
SECONDARY LOSS DRIVERS: HEDGE_DRAG, STOP_TOO_TIGHT, GRID_TOO_NARROW
RESIDUAL GRID STATUS: ABANDON
NATURAL LONG GRID STATUS: REDESIGN
STOCK PAIRS STATUS: REDESIGN
BREAKOUT CONTINUATION STATUS: ABANDON
GRID GEOMETRY STATUS: TOO_NARROW
STOP LOGIC STATUS: TOO_TIGHT
TP LOGIC STATUS: MIXED
HEDGE IMPACT: MIXED
COST IMPACT: EDGE_KILLING
CONDITIONAL EDGE FOUND: UNDERPOWERED
LIVE TRADING STATUS: NO-GO
NEXT PHASE RECOMMENDATION: Phase 3B — pre-register only the mechanically justified redesign hypotheses, freeze them, and validate on raw consolidated intraday data with point-in-time events. Do not tune on HF R-LITE.

## Answers to the research questions

1. **Where losses came from.** The dominant classified loss mode is `NO_MEAN_REVERSION`; the next modes are HEDGE_DRAG, STOP_TOO_TIGHT, GRID_TOO_NARROW. The exact campaign counts and dollars are in `counterfactual_failure_modes.csv`.
2. **Entry vs geometry vs stop/exit vs hedge/cost.** These effects are separated rather than collapsed: observed PF is residual 0.368, natural 4.401, and pairs 4.135; stop-reversion rate is 89.7%; costs are 58.0% of absolute gross campaign movement.
3. **Levels.** Frozen orders were placed according to the audited mechanics, but range validity and support proximity are mixed. Adjusted HF prices prevent a raw-price execution verdict.
4. **Regimes.** Regime tables show whether correctly placed orders still failed in trend/volatility states. Only buckets passing the full minimum-sample rule can be called a conditional candidate.
5. **Grid width.** Aggregate status is `TOO_NARROW`; see grid-step/ATR buckets for family-specific behavior.
6. **Averaging.** The dataset records the average entry after each add. Meaningful improvement is defined before inspection as >0.1 ATR.
7. **Filled legs.** Campaigns with fewer than two filled levels are explicitly marked as unable to exercise meaningful averaging.
8. **Stops.** Aggregate status is `TOO_TIGHT`. A later 20-bar reversion is evidence of timing sensitivity, not proof that a wider stop is superior.
9. **TPs.** Aggregate status is `MIXED`. Cost/TP ratios and missed favorable excursions are reported separately.
10. **Residual reversion.** `residual_failure_analysis.csv` gives z after 1/3/5/10 bars, maximum favorable/adverse z movement, and time to reversion for every residual campaign.
11. **Hedge legs.** Aggregate hedge effect is `MIXED`. Stock and hedge cashflows are shown independently; stock-only is not treated as a valid replacement strategy.
12. **Breakout.** 291 campaigns contain breakout attribution with $-6970.77 total breakout P&L. Sparse attribution remains inconclusive and cannot hide grid losses.
13. **Natural-grid scarcity.** The sequential waterfall shows progressive losses through range/ADX/regime gates and a decisive late-stage liquidity bottleneck. The code compares a $50 million **daily** liquidity threshold with the mean dollar volume of 20 **intraday bars**. This unit mismatch explains much of the scarcity and also affects residual/pair opportunity gates. Event blocking remains unavailable because R-LITE had no event history.
14. **Conditional edge.** 0 buckets pass all diagnostic eligibility rules. Status: `UNDERPOWERED`.
15. **Family worth redesigning.** Natural long grid is `REDESIGN` because signal density, support/range gating, and resting-grid geometry can be tested as pre-registered mechanics. Residual grid in its current form is `ABANDON`.
16. **Family to stop in current form.** Any family marked `ABANDON` should not receive further parameter sweeps; only a materially different, economically justified hypothesis may return.
17. **Phase 3B tests.** First correct and freeze the liquidity unit: compute ADV from completed daily sessions (or an explicitly equivalent intraday scaling) before any strategy redesign. Then pre-register at most: (a) a natural-grid support/sweep context with a density floor, (b) a residual entry delay or trend veto only if sufficient-sample buckets justify it, and (c) a hedge-ratio redesign only if hedge drag is stable across symbols/months. Use raw prices, consolidated volume, and point-in-time events.
18. **Do not test further.** Do not cherry-pick symbols/months, select the best z/stop/TP from these diagnostics, reuse HF adjusted bars as fill truth, or begin paper/live integration.

## Reliability limits

- HF R-LITE is adjusted and IEX-only after March 2022; volume/level evidence is limited.
- No point-in-time events were available, so event proximity is unavailable.
- The universe is survivorship-biased.
- Counterfactuals are explanatory path heuristics unless explicitly labeled observed leg P&L.
- The frozen engine/config digest was checked before and after the run; Phase 2D baseline parameters were not mutated.
- The 58 replays reproduce Phase 2D-R0 trade counts, fills, returns, PF, and expectancy within a 1e-9 tolerance; details are in `baseline_reproduction_check.csv`.
