# Stop and kill-switch audit

## Verdict: PASS, with daily-bar path limitations

Natural baseline is a structure/close stop at `range_low - 0.6 ATR` plus two closes below the range and an ATR-expansion kill; it signals on close and fills next open. Relationship stops are campaign-level z/correlation/beta/event kills and close both legs together. The corrected ordering blocks adds after WARNING/KILL and evaluates z-kill before breakout conversion.

Stopped baseline campaigns: 1914; mean loss among triggered: $-11.35; worst: $-2,305.93.

The alternatives below are counterfactual diagnostics only. They are not selected as new edge.

```text
                    variant  campaigns  trigger_pct  later_revert_pct  median_stop_atr
average_entry_minus_1.5_atr       1235     0.828340          0.144130         1.500000
         intrabar_hard_stop       1235     0.338462          0.036437         4.286634
    last_grid_minus_0.5_atr       1235     0.572470          0.127935         3.251840
    range_low_minus_0.5_atr       1235     0.358704          0.042105         4.186634
    range_low_minus_1.0_atr       1235     0.251012          0.012955         4.686634
       structure_close_only       1235     0.395951          0.052632         3.686634
     two_close_confirmation       1235     0.295547          0.016194         3.686634
```
