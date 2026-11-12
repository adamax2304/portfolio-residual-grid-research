from types import SimpleNamespace

import pandas as pd
import pytest

from residual_grid_research.backtest import BacktestEngine, resolve_barrier_touch
from residual_grid_research.models import OrderIntent, Side
from residual_grid_research.strategies.state_machine import StrategyStateMachine


class OneShotStrategy:
    name = "one_shot"
    symbol = "A"

    def __init__(self):
        self.sent = False
        self.machine = StrategyStateMachine(self.name, self.symbol)

    @property
    def decisions(self):
        return self.machine.decisions

    def prepare(self, data):
        return data["A"].copy()

    def on_bar(self, timestamp, portfolio):
        if self.sent:
            return []
        self.sent = True
        return [OrderIntent("A", Side.BUY, 1000, "test", self.name, "group")]


def test_orders_fill_at_next_bar_open(config):
    index = pd.bdate_range("2025-01-02", periods=4)
    frame = pd.DataFrame(
        {"open": [10, 20, 30, 40], "high": [11, 21, 31, 41], "low": [9, 19, 29, 39], "close": [10, 20, 30, 40], "volume": [1_000_000] * 4},
        index=index,
    )
    result = BacktestEngine(config).run(OneShotStrategy(), {"A": frame})
    assert pd.Timestamp(result.fills[0].timestamp) == index[1]
    assert result.fills[0].price > 20  # buy pays spread/slippage
    assert sum(campaign["pnl_usd"] for campaign in result.campaigns) == pytest.approx(
        result.metrics["ending_equity"] - result.metrics["starting_capital"]
    )


def test_trade_start_allows_warmup_but_blocks_pre_oos_orders(config):
    index = pd.bdate_range("2025-01-02", periods=5)
    frame = pd.DataFrame(
        {"open": [10, 20, 30, 40, 50], "high": [11, 21, 31, 41, 51], "low": [9, 19, 29, 39, 49], "close": [10, 20, 30, 40, 50], "volume": [1_000_000] * 5},
        index=index,
    )
    result = BacktestEngine(config).run(
        OneShotStrategy(), {"A": frame}, trade_start=index[2]
    )
    assert pd.Timestamp(result.fills[0].timestamp) == index[3]
    assert result.campaigns
    assert result.campaigns[0]["closed"] is True


def test_fill_is_never_outside_candle(config):
    index = pd.bdate_range("2025-01-02", periods=3)
    frame = pd.DataFrame(
        {"open": [10, 20, 30], "high": [10, 20, 30], "low": [10, 20, 30], "close": [10, 20, 30], "volume": [1_000_000] * 3},
        index=index,
    )
    result = BacktestEngine(config).run(OneShotStrategy(), {"A": frame})
    assert result.fills[0].price == 20
    assert result.campaigns[0]["closed"] is True


def test_adverse_first_same_bar_resolution():
    bar = {"high": 110, "low": 90}
    assert resolve_barrier_touch(bar, stop=95, target=105, direction=1) == "stop"
    assert resolve_barrier_touch(bar, stop=95, target=105, direction=1, mode="tp_first") == "target"
