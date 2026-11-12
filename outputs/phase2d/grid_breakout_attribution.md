# Grid and breakout sub-ledger validation

STATUS: **PASS (mechanics only)**

The engine now emits `grid_ledger` and `breakout_ledger` rows and reconciles their sum to `campaign_ledger`. For natural-grid inventory carried into continuation, P&L is marked at the close that confirmed `BREAKOUT_ACTIVE`; relationship continuations already start a distinct breakout campaign. Kill, time-stop, failed-breakout, and event exits retain their explicit campaign exit categories.

The included fixture proves arithmetic reconciliation only. Market attribution was not run after the data gate failed.
