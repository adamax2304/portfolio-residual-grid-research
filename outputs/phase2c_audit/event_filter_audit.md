# Event, earnings, dividend, and news filter audit

## Verdict: PASS_WITH_DATA_LIMITATIONS

The corrected engine applies the calendar before signal generation and again before queued entries/adds fill. Existing campaigns use one explicit policy: force exit after an event-window close signal; no new adds are allowed. Earnings apply to both relationship legs. Ex-dividend checks bind only to the actual short leg and existing positions receive a conservative two-business-day execution/holiday lead beyond the entry buffer. `skipped_setup_due_event` records candidate/armed setups returned to SCAN; informational long-leg dividend crossings remain in the CSV with `blocked=false`. Historical Yahoo earnings are retrospective rather than point-in-time, and a full NYSE holiday calendar is not yet used.

```text
            record_type  blocked  rows
          allowed_entry    False  5338
 campaign_crossed_event    False   238
 event_state_transition     True   298
skipped_setup_due_event     True   913
```
