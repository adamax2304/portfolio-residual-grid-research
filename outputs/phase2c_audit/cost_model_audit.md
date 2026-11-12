# Cost, spread, and slippage audit

## Verdict: PASS

Commission is charged on each entry and exit. Spread and slippage move buys upward and sells downward and are embedded in execution P&L; both hedge legs incur them. Short borrow is charged over elapsed calendar time. Full fills are assumed at configured size, and fills never exceed candle high/low. Narrow grids with cost/expected-profit ratios near or above one are mechanically uneconomic and are diagnostic flags, not candidates.

```text
                    run entry_or_exit  fills  total_cost  median_cost_pct_step  median_cost_pct_profit
 natural_long_grid:AAPL         entry     36   43.670992              0.010177                0.002626
 natural_long_grid:AAPL          exit     18   81.924615              0.035158                0.006156
 natural_long_grid:ABBV         entry     21   15.210021              0.008434                0.002263
 natural_long_grid:ABBV          exit     12   45.177766              0.042345                0.010598
  natural_long_grid:ACN         entry     25   24.462368              0.012164                0.003721
  natural_long_grid:ACN          exit     17   47.018500              0.039288                0.013526
  natural_long_grid:AEP         entry     26   26.054893              0.010363                0.002525
  natural_long_grid:AEP          exit     17   71.314670              0.044113                0.010901
  natural_long_grid:AMT         entry     54   60.719928              0.011824                0.002568
  natural_long_grid:AMT          exit     31  110.943489              0.042365                0.009000
 natural_long_grid:AMZN         entry     39   26.850259              0.012086                0.002787
 natural_long_grid:AMZN          exit     17   61.347497              0.032330                0.007851
  natural_long_grid:APD         entry     44   50.188989              0.011128                0.002448
  natural_long_grid:APD          exit     21   94.297853              0.043089                0.010706
  natural_long_grid:AXP         entry     30   39.670976              0.012718                0.003369
  natural_long_grid:AXP          exit     18   68.248479              0.037577                0.007650
  natural_long_grid:BAC         entry     33   27.777351              0.010496                0.002199
  natural_long_grid:BAC          exit     13   56.300401              0.034918                0.006269
  natural_long_grid:BMY         entry     50   49.695956              0.009090                0.002169
  natural_long_grid:BMY          exit     29  134.102305              0.047842                0.010308
    natural_long_grid:C         entry     25   29.770815              0.010861                0.002847
    natural_long_grid:C          exit     18   57.710910              0.042085                0.008430
  natural_long_grid:CAT         entry     49   34.429099              0.009239                0.002065
  natural_long_grid:CAT          exit     22   92.026995              0.034738                0.007008
   natural_long_grid:CL         entry     49   52.230991              0.009464                0.002051
   natural_long_grid:CL          exit     27  139.565548              0.048524                0.010734
  natural_long_grid:COP         entry     48   44.839263              0.009387                0.002288
  natural_long_grid:COP          exit     27   97.563876              0.036597                0.007794
 natural_long_grid:COST         entry     32   33.878703              0.010029                0.002264
 natural_long_grid:COST          exit     17   81.550219              0.047732                0.010382
 natural_long_grid:CSCO         entry     27   39.351788              0.012300                0.002979
 natural_long_grid:CSCO          exit     17   69.541440              0.047365                0.010413
  natural_long_grid:CVX         entry     36   40.174942              0.009917                0.002158
  natural_long_grid:CVX          exit     21   88.747868              0.043292                0.009383
   natural_long_grid:DE         entry     46   48.227313              0.009953                0.001958
   natural_long_grid:DE          exit     24   95.125525              0.036842                0.008001
  natural_long_grid:DUK         entry     41   45.497872              0.009555                0.002165
  natural_long_grid:DUK          exit     22  115.594937              0.050792                0.012258
  natural_long_grid:EOG         entry     60   46.904679              0.010677                0.002432
  natural_long_grid:EOG          exit     33  116.573693              0.038744                0.008445
 natural_long_grid:EQIX         entry     36   29.528073              0.009307                0.002221
 natural_long_grid:EQIX          exit     17   70.485654              0.032107                0.009392
  natural_long_grid:FCX         entry     44   34.382756              0.011111                0.002536
  natural_long_grid:FCX          exit     23   58.118759              0.027317                0.005081
   natural_long_grid:GE         entry     33   34.133564              0.010409                0.002690
   natural_long_grid:GE          exit     18   59.439550              0.031013                0.008101
natural_long_grid:GOOGL         entry     24   18.875295              0.008875                0.002480
natural_long_grid:GOOGL          exit     14   45.115118              0.031096                0.007623
   natural_long_grid:GS         entry     44   41.854999              0.010483                0.002689
   natural_long_grid:GS          exit     21   78.856757              0.036086                0.008903
```
