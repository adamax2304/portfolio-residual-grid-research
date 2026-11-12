import pandas as pd

from residual_grid_research.data.yahoo_finance import YahooFinanceClient


def test_yahoo_normalization_preserves_adjusted_ohlcv_and_actions():
    index = pd.to_datetime(["2025-01-02", "2025-01-03"])
    frame = pd.DataFrame(
        {
            "Open": [10, 11], "High": [11, 12], "Low": [9, 10], "Close": [10.5, 11.5],
            "Volume": [100, 200], "Dividends": [0, 0.25], "Stock Splits": [0, 0],
        },
        index=index,
    )
    normalized = YahooFinanceClient._normalize(frame, intraday=False)
    assert list(normalized.columns) == ["open", "high", "low", "close", "volume", "dividends", "stock_splits"]
    assert normalized.iloc[1]["dividends"] == 0.25
