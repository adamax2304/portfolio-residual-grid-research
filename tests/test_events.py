import pandas as pd

from residual_grid_research.data.events import EventCalendar


def test_indexed_event_calendar_blocks_expected_business_window():
    events = pd.DataFrame([
        {"symbol": "XYZ", "date": "2025-01-10", "event_type": "EARNINGS", "severity": "HIGH_IMPACT"}
    ])
    calendar = EventCalendar(events)
    assert calendar.check(["XYZ"], pd.Timestamp("2025-01-06"), earnings_before=5).blocked
    assert calendar.check(["XYZ"], pd.Timestamp("2025-01-15"), earnings_after=2).blocked is False

