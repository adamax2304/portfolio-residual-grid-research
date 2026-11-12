# Exchange calendar validation

STATUS: **PASS**

Calendar: `XNYS` via `exchange_calendars`; all session opens/closes are stored in UTC and converted to America/New_York only for reporting.

- Christmas 2024 excluded: `True`
- 2024-07-03 early close recognized: `True` at `13:00` ET
- Next open after 2024-12-24 close: `2024-12-26 09:30:00-05:00`
- Holiday-aware session distance 2024-12-24 to 2024-12-26 equals one: `True`

This calendar is wired into event distance. Bar availability still controls actual next-bar execution; no weekday approximation is used in Phase 2D event checks.
