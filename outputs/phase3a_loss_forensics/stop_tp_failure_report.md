# Stop/TP failure analysis

## Stop classifications

| category | count |
|---|---|
| STOP_TOO_TIGHT_REVERTED_AFTER | 1245 |
| NOT_STOPPED | 1128 |
| STOP_CORRECT_PREVENTED_LARGER_LOSS | 429 |
| STRUCTURE_BREAK_CONFIRMED | 177 |
| STOP_TOO_WIDE_LARGE_LOSS | 58 |

## TP classifications

| category | count |
|---|---|
| NO_TP_EXIT | 1599 |
| TP_WAITED_TOO_LONG_AND_REVERSED | 601 |
| TP_HIT_CLEANLY | 565 |
| TP_TOO_FAR_MISSED | 184 |
| TP_TOO_CLOSE_COST_DOMINATED | 88 |

Observed stop logic status: **TOO_TIGHT**. Observed TP status: **MIXED**. Post-stop reversion uses a fixed 20-bar diagnostic horizon. It does not prove a wider stop would be profitable because capital usage and later adverse paths are not replayed. The alternative stop/TP fields are path heuristics only, never parameter selections.
