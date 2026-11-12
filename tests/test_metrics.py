import pandas as pd

from residual_grid_research.backtest.metrics import compute_baselines


def test_no_trade_result_cannot_be_called_edge():
    index = pd.bdate_range("2024-01-01", periods=100)
    falling = pd.DataFrame({"close": [100 - i * 0.5 for i in range(100)]}, index=index)
    baselines = compute_baselines(
        {"A": falling, "SPY": falling},
        primary_symbol="A",
        strategy_return=0.0,
        has_trades=False,
    )
    assert baselines["edge_found"] is False
