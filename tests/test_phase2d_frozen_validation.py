from __future__ import annotations

import json
import shutil
from copy import deepcopy

import pandas as pd
import pytest

from residual_grid_research.backtest import BacktestEngine, resolve_barrier_touch
from residual_grid_research.config import load_config
from residual_grid_research.data import AlphaVantageIndependentAdapter, EventCalendar, USExchangeCalendar
from residual_grid_research.data.alpha_vantage import AlphaVantageClient, indicator_prices
from residual_grid_research.models import Decision, Fill, OrderIntent, Side, StrategyState
from residual_grid_research.phase2d import (
    FrozenConfigurationError,
    FrozenEngineGuard,
    _universe,
    create_frozen_snapshot,
    diagnostic_variants,
)
from residual_grid_research.strategies.state_machine import StrategyStateMachine


ROOT = __import__("pathlib").Path(__file__).parents[1]


def phase2d_config():
    return load_config(ROOT / "config" / "phase2d_frozen.yaml")


class _Response:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


class _DualSession:
    def __init__(self):
        self.calls = []

    def get(self, _url, *, params, timeout):
        self.calls.append(dict(params))
        price = 50 if params["adjusted"] == "true" else 100
        text = (
            "timestamp,open,high,low,close,volume\n"
            f"2025-01-02 09:30:00,{price},{price + 1},{price - 1},{price},1000000\n"
        )
        return _Response(text)


def test_independent_adapter_uses_separate_raw_and_adjusted_requests(tmp_path):
    session = _DualSession()
    client = AlphaVantageClient(
        "key", cache_dir=tmp_path, requests_per_minute=1000000, session=session
    )
    frame = client.fetch_intraday_month_dual("A", "2025-01", interval="5min")
    assert frame.iloc[0]["close"] == 100
    assert frame.iloc[0]["adjusted_close"] == 50
    assert [call["adjusted"] for call in session.calls] == ["false", "true"]
    assert all(call["extended_hours"] == "false" for call in session.calls)
    features = indicator_prices(frame)
    assert features.iloc[0]["close"] == 50
    assert frame.iloc[0]["close"] == 100


def test_adapter_preflight_is_ready_with_injected_client(tmp_path):
    config = phase2d_config()
    config["data"]["cache_dir"] = str(tmp_path)
    client = AlphaVantageClient("key", cache_dir=tmp_path, session=_DualSession(), requests_per_minute=1000000)
    assert AlphaVantageIndependentAdapter(config, client=client).preflight().ready is True


def test_xnys_holiday_early_close_and_next_open():
    calendar = USExchangeCalendar(start="2024-01-01", end="2025-12-31")
    assert not calendar.is_session("2024-12-25")
    info = calendar.session_info("2024-07-03")
    assert info.early_close
    assert info.close_utc.tz_convert("America/New_York").strftime("%H:%M") == "13:00"
    next_open = calendar.next_open(pd.Timestamp("2024-12-24 16:00", tz="America/New_York"))
    assert next_open.tz_convert("America/New_York").strftime("%Y-%m-%d %H:%M") == "2024-12-26 09:30"


def test_event_distance_uses_exchange_sessions_not_weekdays():
    calendar = USExchangeCalendar(start="2024-01-01", end="2025-12-31")
    events = pd.DataFrame([
        {"symbol": "A", "date": "2024-12-26", "event_type": "EARNINGS"}
    ])
    gate = EventCalendar(events, session_calendar=calendar)
    assert calendar.trading_day_distance("2024-12-24", "2024-12-26") == 1
    assert gate.check(["A"], pd.Timestamp("2024-12-24"), earnings_before=1, earnings_after=0).blocked


class _OneRawOrder:
    name = "phase2d_raw_order"
    symbol = "A"

    def __init__(self):
        self.sent = False
        self.machine = StrategyStateMachine(self.name, self.symbol)

    @property
    def decisions(self):
        return self.machine.decisions

    def prepare(self, data):
        return indicator_prices(data["A"])

    def on_bar(self, timestamp, portfolio):
        if self.sent:
            return []
        self.sent = True
        return [OrderIntent("A", Side.BUY, 1000, "grid entry", self.name, "raw-group")]


def test_engine_executes_raw_ohlc_even_when_indicators_are_adjusted(config):
    index = pd.date_range("2025-01-02 09:30", periods=3, freq="5min", tz="America/New_York")
    frame = pd.DataFrame(
        {
            "open": [100, 101, 102], "high": [101, 102, 103], "low": [99, 100, 101],
            "close": [100, 101, 102], "volume": [1_000_000] * 3,
            "adjusted_open": [50, 50.5, 51], "adjusted_high": [50.5, 51, 51.5],
            "adjusted_low": [49.5, 50, 50.5], "adjusted_close": [50, 50.5, 51],
        }, index=index,
    )
    result = BacktestEngine(config).run(_OneRawOrder(), {"A": frame})
    assert result.fills[0].reference_price == 101
    assert result.fills[0].price > 100
    assert all(row["reconciled"] for row in result.subledgers)


def test_natural_inventory_transfer_reconciles_grid_and_breakout():
    index = pd.date_range("2025-01-02 09:30", periods=3, freq="5min", tz="America/New_York")
    data = {"A": pd.DataFrame({"close": [100, 105, 110]}, index=index)}
    fills = [
        Fill(index[0].to_pydatetime(), "A", Side.BUY, 10, 100, 1000, 0.5, 0, "natural_long_grid", "g", "natural grid layer 1", metadata={"subledger": "grid_ledger"}),
        Fill(index[2].to_pydatetime(), "A", Side.SELL, 10, 110, 1100, 0.5, 0, "natural_long_grid", "g", "breakout exit", realized_pnl=100, metadata={"close_all": True, "subledger": "breakout_ledger"}),
    ]
    decisions = [Decision(index[1].to_pydatetime(), "natural_long_grid", StrategyState.BREAKOUT_SETUP, StrategyState.BREAKOUT_ACTIVE, "grid converted to continuation", symbol="A")]
    grid, breakout, transfer = BacktestEngine._subledger_attribution(
        fills, data, decisions, start=index[0], end=index[2], campaign_pnl=99.0, financing=0.0
    )
    assert transfer == index[1]
    assert grid == pytest.approx(49.5)
    assert breakout == pytest.approx(49.5)
    assert grid + breakout == pytest.approx(99.0)


def test_same_candle_intraday_ordering_is_adverse_first():
    assert resolve_barrier_touch({"high": 106, "low": 94}, stop=95, target=105, direction=1) == "stop"


def test_frozen_universe_and_parameters_do_not_mutate():
    config = phase2d_config()
    universe = _universe(config)
    assert ["MA", "V"] in universe["stock_to_stock"]
    assert ["JPM", "XLF"] in universe["stock_to_etf"]
    assert "AAPL" in universe["natural_long"]
    guard = FrozenEngineGuard.capture(config)
    before = deepcopy(config)
    rows = diagnostic_variants(config)
    assert rows and config == before
    guard.assert_unchanged(config)
    config["strategy"]["natural"]["grid_step_atr"] = 9.9
    with pytest.raises(FrozenConfigurationError):
        guard.assert_unchanged(config)


def test_frozen_snapshot_records_commit_config_and_bugfixes(tmp_path, monkeypatch):
    root = tmp_path
    (root / "config").mkdir()
    shutil.copy(ROOT / "config" / "phase2d_frozen.yaml", root / "config" / "phase2d_frozen.yaml")
    monkeypatch.setattr("residual_grid_research.phase2d._git_commit", lambda _root: "a" * 40)
    snapshot = create_frozen_snapshot(root, root / "config" / "phase2d_frozen.yaml", root / "outputs" / "phase2d")
    assert snapshot["git_commit_hash"] == "a" * 40
    assert snapshot["phase2c_bugfix_count"] == 10
    assert snapshot["frozen_parameter_sha256"]
    universe = json.loads((root / "outputs" / "phase2d" / "frozen_universe.json").read_text())
    assert universe["frozen_before_results"] is True
