# Residual-grid failure analysis

- Campaigns: **3031**
- Net P&L: **$-250309.66**
- Profit factor: **0.368**
- Mean reversion reached during campaign: **1526/3031**
- Z-score continued adversely after entry: **1247/3031**
- Stock-leg P&L: **$-111533.63**
- Hedge-leg P&L: **$-134559.73**
- Hedge impact classification: **MIXED**

## Long versus short residual

| attribution_dimension | direction | timeframe | campaigns | trades_legs | net_pnl | average_pnl | median_pnl | win_rate | profit_factor | expectancy | max_drawdown | average_mae | average_mfe | average_cost | cost_as_pct_gross_profit | profit_concentration | loss_concentration | symbols | months | diagnostic_flags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| direction | long_residual | 15min | 483 | 838 | -48999.01455223047 | -101.44723509778565 | -59.28494780833358 | 0.2981366459627329 | 0.40479414991793994 | -101.44723509778565 | -49569.91187220619 | -200.2486577118208 | 78.36457837037985 | 97.76959790883201 | 1.4170872080812074 | 0.12312738342174116 | 0.03240335761971521 | 11 | 54 | SUFFICIENT_SAMPLE;COST_DOMINATED;STOP_DOMINATED;HEDGE_DRAG;BAD_GEOMETRY |
| direction | long_residual | 5min | 1040 | 1933 | -86968.09931557943 | -83.62317241882637 | -57.56144244026274 | 0.26826923076923076 | 0.25089966159414906 | -83.62317241882637 | -86972.2026002944 | -139.51869609982305 | 34.11305092462864 | 87.62870952734576 | 3.128669542692684 | 0.06305392997841346 | 0.012728101385936942 | 11 | 55 | SUFFICIENT_SAMPLE;COST_DOMINATED;STOP_DOMINATED;BAD_GEOMETRY |
| direction | short_residual | 15min | 523 | 955 | -46108.91868447875 | -88.16236842156549 | -63.321123231732045 | 0.33078393881453155 | 0.47520897989576827 | -88.16236842156549 | -46628.67128265389 | -199.55262434927573 | 91.7825580545914 | 100.61427125161984 | 1.2603120642241443 | 0.04802493416829277 | 0.021516990251161588 | 11 | 54 | SUFFICIENT_SAMPLE;COST_DOMINATED;STOP_DOMINATED;BAD_GEOMETRY |
| direction | short_residual | 5min | 985 | 1832 | -68233.6234389687 | -69.27271415123727 | -49.28860477015256 | 0.2781725888324873 | 0.3792645617553306 | -69.27271415123727 | -70118.55389633431 | -136.66023593915097 | 48.003220807915675 | 88.54048535668343 | 2.0919146931179387 | 0.05499581319158189 | 0.011483573612588277 | 11 | 55 | SUFFICIENT_SAMPLE;COST_DOMINATED;STOP_DOMINATED;BAD_GEOMETRY |

Dollar-neutral and no-hedge values are not promoted as strategies. Stock-only P&L is a leg decomposition; an exact dollar-neutral comparison requires a separately pre-registered replay. Z exits and kill levels are analyzed descriptively without choosing a winner.
