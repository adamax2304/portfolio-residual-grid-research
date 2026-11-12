# Phase 3B — Liquidity Gate Fix, Frozen Redesign Hypotheses, and OOS Revalidation

## Scope and evidence status

This is a frozen, diagnostic redesign on **LIMITED HF R-LITE data**. Bars are adjusted, post-2022 data are IEX-only, and point-in-time event history is unavailable. Breakout remained disabled; residual was run once only as H7 confirmation. Live and paper trading remain NO-GO.

## Hypothesis results

| variant | hypothesis | strategy_family | campaign_count | net_pnl | profit_factor | expectancy | win_rate | max_drawdown | best_campaign_contribution | best_month_contribution | positive_symbol_share | positive_month_share | timeframe_consistency | profit_factor_2x_cost | research_gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H4_COST5 | H4 | natural_long_grid | 932 | 18,508.5372 | 1.0518 | 19.8589 | 0.4796 | -33,721.7613 | 0.2627 | 0.6684 | 0.5455 | 0.6000 | MIXED | 0.9619 | False |
| H3_INTRABAR | H3 | natural_long_grid | 65 | 960.6336 | 1.0501 | 14.7790 | 0.4154 | -11,290.1575 | 1.9041 | 2.7231 | 0.5000 | 0.6000 | MIXED | 0.9855 | False |
| H4_COST3 | H4 | natural_long_grid | 1416 | 21,353.8892 | 1.0393 | 15.0804 | 0.4979 | -36,114.4836 | 0.3585 | 0.7026 | 0.6364 | 0.6000 | MIXED | 0.9419 | False |
| H2_STEP08_TP10_DEPTH3_RANGE1 | H2 | natural_long_grid | 410 | 2,585.1159 | 1.0326 | 6.3052 | 0.8122 | -10,384.4767 | 1.0545 | 1.1846 | 0.6364 | 0.5366 | MIXED | 0.9395 | False |
| H2_STEP12_TP15_DEPTH7_STRUCTURE | H2 | natural_long_grid | 907 | 1,972.1990 | 1.0231 | 2.1744 | 0.5325 | -9,201.7887 | 0.8069 | 1.3205 | 0.6364 | 0.5636 | MIXED | 0.8957 | False |
| H1_CORRECTED_BASELINE | H1 | natural_long_grid | 64 | 373.8286 | 1.0128 | 5.8411 | 0.5312 | -18,061.8325 | 6.8860 | 23.3578 | 0.5000 | 0.6500 | MIXED | 0.9673 | False |
| H3_CLOSE2 | H3 | natural_long_grid | 62 | 183.1447 | 1.0107 | 2.9539 | 0.5645 | -8,596.1988 | 7.9020 | 15.1458 | 0.5000 | 0.6500 | MIXED | 0.9687 | False |
| H2_STEP10_TP10_DEPTH5_RANGE1 | H2 | natural_long_grid | 720 | -165.9198 | 0.9980 | -0.2304 | 0.7917 | -11,466.0085 | nan | nan | 0.5455 | 0.6154 | MIXED | 0.8923 | False |
| H4_COST8 | H4 | natural_long_grid | 423 | -18,474.7230 | 0.9025 | -43.6755 | 0.4397 | -26,612.1247 | nan | nan | 0.5455 | 0.5283 | CONSISTENT | 0.8391 | False |
| H3_CLOSE1 | H3 | natural_long_grid | 66 | -912.0519 | 0.9016 | -13.8190 | 0.3939 | -5,016.0991 | nan | nan | 0.5000 | 0.6500 | CONSISTENT | 0.8294 | False |
| H5_CORRECTED_BASELINE | H5 | stock_pair_grid | 355 | -26,118.7784 | 0.4710 | -73.5740 | 0.3887 | -26,860.2886 | nan | nan | 0.1429 | 0.2581 | CONSISTENT | 0.1669 | False |
| H6_TIME10 | H6 | stock_pair_grid | 355 | -26,118.7784 | 0.4710 | -73.5740 | 0.3887 | -26,860.2886 | nan | nan | 0.1429 | 0.2581 | CONSISTENT | 0.1669 | False |
| H6_TIME3 | H6 | stock_pair_grid | 355 | -26,118.7784 | 0.4710 | -73.5740 | 0.3887 | -26,860.2886 | nan | nan | 0.1429 | 0.2581 | CONSISTENT | 0.1669 | False |
| H6_TIME5 | H6 | stock_pair_grid | 355 | -26,118.7784 | 0.4710 | -73.5740 | 0.3887 | -26,860.2886 | nan | nan | 0.1429 | 0.2581 | CONSISTENT | 0.1669 | False |
| H6_EXIT05 | H6 | stock_pair_grid | 376 | -26,804.5018 | 0.4624 | -71.2886 | 0.4043 | -27,441.9799 | nan | nan | 0.1429 | 0.1613 | CONSISTENT | 0.1562 | False |
| H6_EXIT00 | H6 | stock_pair_grid | 359 | -27,058.3419 | 0.4530 | -75.3714 | 0.3872 | -27,998.3411 | nan | nan | 0.1429 | 0.2581 | CONSISTENT | 0.1543 | False |
| H6_EXIT02 | H6 | stock_pair_grid | 367 | -27,099.8614 | 0.4503 | -73.8416 | 0.3869 | -27,939.4180 | nan | nan | 0.1429 | 0.1935 | CONSISTENT | 0.1520 | False |
| H7_RESIDUAL_CONFIRMATION | H7 | residual_grid | 2945 | -252,760.2438 | 0.4038 | -85.8269 | 0.3080 | -252,760.2438 | nan | nan | 0.0909 | 0.0182 | CONSISTENT | 0.1653 | False |

## Required answers

1. **Liquidity density:** YES. Corrected ADV increased eligible bars where the prior unit mismatch had suppressed them.
2. **Natural testability:** yes.
3. **Pair testability:** yes. The H5 corrected baseline produced 355 campaigns, PF 0.471, and expectancy $-73.57; H6 exits did not repair it.
4. **Residual confirmation:** PF 0.404, expectancy $-85.83; status remains ABANDON.
5. **Prior no-trade diagnosis:** the liquidity unit bug was the main density bottleneck for natural and pair campaigns (2→64 and 4→355), but it did not explain their economics.
6. **Wider geometry:** the preregistered H2 variants span PF 0.998–1.033; all fail the research and 2×-cost gates, so geometry is MIXED rather than an edge.
7. **Stop mechanics:** intrabar PF is 1.050; neither 1-close nor 2-close confirmation improves both PF and expectancy. The diagnostic conclusion is MIXED, not a stop upgrade.
8. **Cost-aware TP:** H4 spans PF 0.903–1.052; k=3/5 remain below 1.15 and fail 2× costs, while k=8 loses money. It changes density but does not establish edge.
9. **Statistical sufficiency:** 0 variants pass the preregistered research gate; no positive result is promoted.
10. **Stability:** 0 variants are positive on both 5m and 15m, and none passes the complete robustness gate.
11. **Phase 3C:** no hypothesis advances. Higher-quality raw consolidated intraday data and point-in-time events are required before another controlled redesign.
12. **Abandon:** residual current form, breakout current form, and stock-pair H5/H6 current mechanics are abandoned. Natural grid remains redesign-only, not an edge candidate.
13. **Live/paper:** none is eligible.

## Expected conclusion format

LIQUIDITY GATE FIX: **PASS**
SIGNAL DENSITY IMPROVED: **YES**
NATURAL LONG GRID STATUS: **REDESIGN_CONTINUE**
STOCK PAIRS STATUS: **ABANDON**
RESIDUAL GRID STATUS: **ABANDON**
BREAKOUT CONTINUATION STATUS: **ABANDON**
GRID GEOMETRY STATUS: **MIXED**
STOP LOGIC STATUS: **MIXED**
COST IMPACT: **EDGE_KILLING**
CONDITIONAL EDGE FOUND: **NO**
LIVE TRADING STATUS: **NO-GO**
NEXT PHASE RECOMMENDATION: **No Phase 3C promotion; retain NO-GO and acquire raw consolidated intraday plus point-in-time events before further redesign.**

## Manual replays

| replay | file | variant | pair | timeframe | net_pnl |
|---|---|---|---|---|---|
| best_natural_after_fix | manual_replays\best_natural_after_fix.md | H4_COST3 | KO | 15min | 7,656.1369 |
| worst_natural_after_fix | manual_replays\worst_natural_after_fix.md | H4_COST8 | CSCO | 15min | -10,051.2654 |
| typical_natural_winner | manual_replays\typical_natural_winner.md | H1_CORRECTED_BASELINE | AAPL | 15min | 249.9183 |
| typical_natural_loser | manual_replays\typical_natural_loser.md | H4_COST8 | AAPL | 5min | -435.5681 |
| natural_stopped_then_reverted | manual_replays\natural_stopped_then_reverted.md | H1_CORRECTED_BASELINE | AAPL | 15min | 836.8728 |
| natural_stop_saved | manual_replays\natural_stop_saved.md | H1_CORRECTED_BASELINE | AAPL | 15min | -1,646.5741 |
| natural_tp_too_close | manual_replays\natural_tp_too_close.md | H4_COST3 | AAPL | 5min | -707.2225 |
| natural_grid_too_narrow | manual_replays\natural_grid_too_narrow.md | H1_CORRECTED_BASELINE | AAPL | 15min | 1,320.1897 |
| best_stock_pair | manual_replays\best_stock_pair.md | H5_CORRECTED_BASELINE | MA/V | 15min | 1,884.3822 |
| worst_stock_pair | manual_replays\worst_stock_pair.md | H6_EXIT05 | JPM/BAC | 15min | -2,769.2876 |
| typical_stock_pair | manual_replays\typical_stock_pair.md | H6_EXIT02 | MA/V | 15min | -32.9689 |
| residual_continued_failure | manual_replays\residual_continued_failure.md | H7_RESIDUAL_CONFIRMATION | AAPL/XLK | 15min | -2,702.4626 |
