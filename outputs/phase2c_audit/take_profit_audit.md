# Take-profit and closing logic audit

## Verdict: PASS

- Natural long grid: every submitted layer stores the shared three campaign TP references. Baseline realizes one-third at the range midpoint, half the remainder near the upper range, and all remaining inventory at the range high. Accounting is average-cost and campaign-level, not FIFO/LIFO leg matching.
- Residual stock/ETF: both legs close in the same decision batch when residual z returns to 0.8, 0.5, and 0.0 stages (sign-adjusted). There is no unrelated stock-price TP.
- Stock pairs: both legs close simultaneously and atomically by spread-z condition. No one-legged historical close was found.
- Time stops generate at close and execute next open. All entry and exit fills pay costs. `cost_model_audit.csv` identifies cases where expected TP capture is not safely wider than costs.

```text
  family exit_category  campaigns        pnl_usd    mean_pnl
 natural end_of_sample         17     457.253222   26.897248
 natural          kill        374 -112947.176226 -301.997797
 natural   take_profit          9    4896.961466  544.106830
 natural     time_stop        835  118009.330324  141.328539
    pair breakout_exit          9    -812.650770  -90.294530
    pair end_of_sample          1    -627.190132 -627.190132
    pair          kill         96   -9292.614536  -96.798068
    pair   take_profit          2    1369.150464  684.575232
    pair     time_stop         82    1522.335435   18.565066
residual breakout_exit         35   -5450.327342 -155.723638
residual          kill        209  -26551.901087 -127.042589
residual   take_profit          4    1403.295601  350.823900
residual     time_stop        318    7535.466729   23.696436
```
