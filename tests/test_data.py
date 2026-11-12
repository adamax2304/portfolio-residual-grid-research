import pandas as pd

from residual_grid_research.data.alpha_vantage import AlphaVantageClient, core_session, regular_session


def test_daily_total_return_adjusts_all_ohlc_consistently():
    index = pd.to_datetime(["2025-01-02", "2025-01-03"])
    raw = pd.DataFrame(
        {
            "open": [100, 50], "high": [102, 52], "low": [98, 48], "close": [100, 50],
            "adjusted_close": [50, 50], "volume": [1000, 2000],
            "dividend_amount": [0, 0], "split_coefficient": [1, 2],
        }, index=index,
    )
    adjusted = AlphaVantageClient._total_return_adjust_daily(raw)
    assert adjusted.iloc[0]["open"] == 50
    assert adjusted.iloc[0]["high"] == 51
    assert adjusted.iloc[1]["close"] == 50


def test_regular_session_filter_uses_eastern_clock():
    index = pd.to_datetime(["2025-01-02 09:25", "2025-01-02 09:30", "2025-01-02 16:00", "2025-01-02 16:05"])
    frame = pd.DataFrame({"close": [1, 2, 3, 4]}, index=index)
    result = regular_session(frame)
    assert list(result["close"]) == [2, 3]
    assert str(result.index.tz) == "America/New_York"


def test_core_session_removes_intraday_open_close_buffer():
    index = pd.date_range("2025-01-02 09:30", "2025-01-02 16:00", freq="5min")
    frame = pd.DataFrame({"close": range(len(index))}, index=index)
    result = core_session(frame, 10)
    assert result.index[0].strftime("%H:%M") == "09:40"
    assert result.index[-1].strftime("%H:%M") == "15:50"
