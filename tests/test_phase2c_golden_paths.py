from copy import deepcopy
from types import SimpleNamespace

import pandas as pd
import pytest

from residual_grid_research.backtest import BacktestEngine, resolve_barrier_touch
from residual_grid_research.data.events import EventCalendar
from residual_grid_research.models import OrderIntent, OrderType, Position, Side, StrategyState
from residual_grid_research.strategies.breakout import BreakoutEngine
from residual_grid_research.strategies.residual_grid import ResidualGridStrategy
from residual_grid_research.strategies.pair_grid import StockPairGridStrategy
from residual_grid_research.strategies.state_machine import StrategyStateMachine


def _bars(rows):
    index = pd.bdate_range("2025-01-02", periods=len(rows))
    frame = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=index)
    frame["volume"] = 1_000_000
    return frame


def _zero_cost(config):
    candidate = deepcopy(config)
    candidate["costs"].update({
        "commission_per_fill_usd": 0.0,
        "spread_bps": 0.0,
        "slippage_bps": 0.0,
        "short_borrow_annual_pct": 0.0,
    })
    return candidate


class ScriptedStrategy:
    name = "golden_path"
    symbol = "A"

    def __init__(self, actions, *, calendar=None, event_mode="none"):
        self.actions = actions
        self.machine = StrategyStateMachine(self.name, self.symbol, state=StrategyState.GRID_ACTIVE)
        self.calendar = calendar or EventCalendar()
        self.event_mode = event_mode
        self.prepared = pd.DataFrame()

    @property
    def decisions(self):
        return self.machine.decisions

    def prepare(self, data):
        self.prepared = data["A"].copy()
        return self.prepared

    def pending_order_valid(self, timestamp, intent, portfolio):
        if intent.reduce_only:
            return True, "exit"
        if self.machine.state not in {StrategyState.GRID_ACTIVE, StrategyState.WARNING}:
            return False, "grid invalidated"
        event = self.calendar.check(["A"], timestamp, earnings_before=0, earnings_after=0)
        return (not event.blocked, "; ".join(event.reasons) or "event safe")

    def protective_orders_at_bar(self, timestamp, portfolio, bars):
        return []

    def on_bar(self, timestamp, portfolio):
        if self.event_mode == "force_exit":
            event = self.calendar.check(["A"], timestamp, earnings_before=0, earnings_after=0)
            position = portfolio.positions.get("A")
            if event.blocked and position is not None and not position.is_flat:
                self.machine.transition(timestamp, StrategyState.KILL, "event force exit")
                return [OrderIntent(
                    "A", Side.SELL, abs(position.quantity * portfolio.prices["A"]),
                    "event force exit", self.name, "g", reduce_only=True,
                    metadata={"close_all": True, "close_fraction": 1.0},
                )]
        action = self.actions.get(pd.Timestamp(timestamp))
        return action(self, portfolio) if callable(action) else list(action or [])


def _limit(level, layer):
    return OrderIntent(
        "A", Side.BUY, level * 10, f"grid layer {layer}", "golden_path", "g",
        metadata={"grid_layer": layer}, order_type=OrderType.LIMIT,
        requested_price=level, time_in_force="GTC",
    )


def test_golden_01_clean_range_oscillation(config):
    frame = _bars([
        (100, 101, 99.5, 100),
        (100, 100, 96, 97),
        (98, 101, 97.5, 100),
        (100, 100, 100, 100),
    ])
    index = frame.index

    def exits(strategy, portfolio):
        strategy.machine.transition(index[1], StrategyState.GRID_EXITING, "targets active")
        return [
            OrderIntent("A", Side.SELL, 1, "TP1", strategy.name, "g", True, {"close_fraction": 1 / 3}, OrderType.LIMIT, 100),
            OrderIntent("A", Side.SELL, 1, "TP2", strategy.name, "g", True, {"close_fraction": 1 / 2}, OrderType.LIMIT, 99),
            OrderIntent("A", Side.SELL, 1, "TP3", strategy.name, "g", True, {"close_all": True}, OrderType.LIMIT, 98),
        ]

    strategy = ScriptedStrategy({index[0]: [_limit(99, 1), _limit(98, 2), _limit(97, 3)], index[1]: exits})
    result = BacktestEngine(_zero_cost(config)).run(strategy, {"A": frame})
    entries = result.fills[:3]
    exits_filled = result.fills[3:]
    entry_cost = sum(fill.quantity * fill.price for fill in entries)
    exit_value = sum(fill.quantity * fill.price for fill in exits_filled)
    assert [fill.price for fill in entries] == [99, 98, 97]
    assert [fill.price for fill in exits_filled] == [100, 99, 98]
    assert result.campaigns[0]["pnl_usd"] == pytest.approx(exit_value - entry_cost)
    assert result.campaigns[0]["closed"] is True


def test_golden_02_partial_range_oscillation(config):
    frame = _bars([(100, 101, 99.5, 100), (100, 100, 97.5, 99), (100, 101, 99, 100), (100, 100, 100, 100)])
    index = frame.index

    def exit_all(strategy, portfolio):
        strategy.machine.transition(index[1], StrategyState.GRID_EXITING, "partial target")
        return [OrderIntent("A", Side.SELL, 1, "partial TP", strategy.name, "g", True, {"close_all": True}, OrderType.LIMIT, 100)]

    result = BacktestEngine(_zero_cost(config)).run(
        ScriptedStrategy({index[0]: [_limit(99, 1), _limit(98, 2), _limit(97, 3)], index[1]: exit_all}),
        {"A": frame},
    )
    entry_fills = [fill for fill in result.fills if not fill.reduce_only] if False else [fill for fill in result.fills if "grid layer" in fill.reason]
    assert [fill.price for fill in entry_fills] == [99, 98]
    assert not any(fill.reason == "grid layer 3" for fill in result.fills)


def test_golden_03_clean_breakdown_cancels_grid(config):
    frame = _bars([(100, 101, 99.5, 100), (100, 100, 95.5, 95.8), (94, 95, 93, 94), (94, 94, 94, 94)])
    index = frame.index

    def kill(strategy, portfolio):
        strategy.machine.transition(index[1], StrategyState.KILL, "invalidation")
        position = portfolio.positions["A"]
        return [OrderIntent("A", Side.SELL, abs(position.quantity * portfolio.prices["A"]), "kill", strategy.name, "g", True, {"close_all": True})]

    result = BacktestEngine(_zero_cost(config)).run(
        ScriptedStrategy({index[0]: [_limit(99, 1), _limit(98, 2), _limit(95, 3)], index[1]: kill}),
        {"A": frame},
    )
    assert not any(fill.reason == "grid layer 3" for fill in result.fills)
    assert any(row["status"] == "CANCELLED" and row["strategy_reason"] == "grid layer 3" for row in result.order_audit)
    assert result.campaigns[0]["closed"] is True


def test_golden_04_gap_through_stop_uses_gap_open(config):
    frame = _bars([(100, 100, 100, 100), (100, 101, 99, 100), (90, 92, 88, 89), (89, 89, 89, 89)])
    index = frame.index

    def stop(strategy, portfolio):
        return [OrderIntent("A", Side.SELL, 1, "hard stop", strategy.name, "g", True, {"close_all": True}, OrderType.STOP, 95)]

    strategy = ScriptedStrategy({
        index[0]: [OrderIntent("A", Side.BUY, 1000, "entry", "golden_path", "g")],
        index[1]: stop,
    })
    result = BacktestEngine(_zero_cost(config)).run(strategy, {"A": frame})
    stop_fill = next(fill for fill in result.fills if fill.reason == "hard stop")
    assert stop_fill.price == 90
    assert stop_fill.fill_reason == "gap through stop"


def test_golden_05_same_candle_tp_and_stop_is_adverse_first():
    assert resolve_barrier_touch({"high": 105, "low": 95}, stop=96, target=104, direction=1) == "stop"


def test_golden_06_no_fill_when_limit_is_not_touched(config):
    frame = _bars([(100, 101, 99, 100), (100, 101, 99, 100), (100, 100, 100, 100)])
    result = BacktestEngine(_zero_cost(config)).run(
        ScriptedStrategy({frame.index[0]: [_limit(98, 1)]}), {"A": frame}
    )
    assert result.fills == []
    assert any(row["status"] == "NOT_FILLED" for row in result.order_audit) is False  # GTC remains live
    assert result.warnings == ["1 next-bar order(s) remained unfilled at end of sample"]


def test_golden_07_event_exclusion_blocks_new_entry(config):
    frame = _bars([(100, 101, 99, 100), (100, 101, 99, 100), (100, 100, 100, 100)])
    calendar = EventCalendar(pd.DataFrame([{"symbol": "A", "date": frame.index[1], "event_type": "EARNINGS"}]))
    result = BacktestEngine(_zero_cost(config)).run(
        ScriptedStrategy({frame.index[0]: [OrderIntent("A", Side.BUY, 1000, "entry", "golden_path", "g")]}, calendar=calendar),
        {"A": frame},
    )
    assert result.fills == []
    assert any("earnings" in row["fill_reason"] for row in result.order_audit)


def test_golden_08_existing_position_event_force_exits_next_open(config):
    frame = _bars([(100, 100, 100, 100), (100, 101, 99, 100), (101, 102, 100, 101), (99, 100, 98, 99)])
    calendar = EventCalendar(pd.DataFrame([{"symbol": "A", "date": frame.index[2], "event_type": "EARNINGS"}]))
    result = BacktestEngine(_zero_cost(config)).run(
        ScriptedStrategy(
            {frame.index[0]: [OrderIntent("A", Side.BUY, 1000, "entry", "golden_path", "g")]},
            calendar=calendar,
            event_mode="force_exit",
        ),
        {"A": frame},
    )
    exit_fill = next(fill for fill in result.fills if fill.reason == "event force exit")
    assert pd.Timestamp(exit_fill.timestamp) == frame.index[3]
    assert result.campaigns[0]["closed"] is True


def test_golden_09_breakout_continuation_requires_confirmation(config):
    candidate = deepcopy(config)
    candidate["strategy"]["breakout"].update({"confirmation_mode": "two_closes", "minimum_score": 70, "volume_ratio": 1.5})
    history = pd.DataFrame({
        "open": [99.0, 100.4, 101.0], "high": [100.0, 101.5, 102.5], "low": [98.5, 100.1, 100.8],
        "close": [99.5, 101.0, 102.0], "volume_ratio": [1.0, 1.2, 2.0], "adx_14": [20, 23, 28],
    })
    assessment = BreakoutEngine(candidate).assess(history, range_high=100, range_low=95, atr=1)
    assert assessment.confirmed and assessment.direction == 1


def test_golden_10_breakout_fakeout_is_rejected(config):
    candidate = deepcopy(config)
    candidate["strategy"]["breakout"].update({"confirmation_mode": "two_closes", "minimum_score": 70})
    history = pd.DataFrame({
        "open": [99, 100, 100], "high": [101, 101, 102], "low": [98, 99, 99.8],
        "close": [100.6, 99.9, 101.0], "volume_ratio": [2, 2, 2], "adx_14": [25, 25, 25],
    })
    assert BreakoutEngine(candidate).assess(history, range_high=100, range_low=95, atr=1).confirmed is False


def test_golden_11_residual_mean_reversion_has_correct_legs(config):
    strategy = ResidualGridStrategy(config, "A", "B")
    timestamp = pd.Timestamp("2025-01-02")
    strategy.prepared = pd.DataFrame([{"z": -1.6, "corr_60": 0.8, "beta": 1.2, "beta_stability": 0.1, "residual_std": 0.02, "stock_close": 100}], index=[timestamp])
    strategy.machine.state = StrategyState.ARMED
    strategy._gate_and_score = lambda *args, **kwargs: (True, True, SimpleNamespace(total=80.0, passed=True), [])
    portfolio = SimpleNamespace(equity=100_000.0, positions={}, prices={"A": 100.0, "B": 50.0})
    orders = strategy.on_bar(timestamp, portfolio)
    assert orders[0].symbol == "A" and orders[0].side == Side.BUY
    assert orders[1].symbol == "B" and orders[1].side == Side.SELL
    assert orders[1].notional_usd == pytest.approx(orders[0].notional_usd * 1.2)


def test_golden_12_residual_divergence_kills_before_breakout(config):
    strategy = ResidualGridStrategy(config, "A", "B")
    timestamp = pd.Timestamp("2025-01-02")
    strategy.prepared = pd.DataFrame([{"z": -3.2, "corr_60": 0.8, "beta": 1.0, "beta_stability": 0.1, "residual_std": 0.02, "stock_close": 80}], index=[timestamp])
    strategy.machine.state = StrategyState.GRID_ACTIVE
    strategy.campaign.group_id = "g"
    strategy.campaign.direction = 1
    strategy._gate_and_score = lambda *args, **kwargs: (True, True, SimpleNamespace(total=80.0, passed=True), [])
    portfolio = SimpleNamespace(
        equity=99_000.0,
        positions={"A": Position("A", 10, 90), "B": Position("B", -8, 50)},
        prices={"A": 80.0, "B": 55.0},
    )
    orders = strategy.on_bar(timestamp, portfolio)
    assert strategy.machine.state == StrategyState.KILL
    assert strategy.decisions[-1].reason == "residual kill z reached"
    assert len(orders) == 2 and all(order.reduce_only for order in orders)


def test_relationship_event_filter_tracks_actual_short_leg(config):
    timestamp = pd.Timestamp("2025-01-10")
    calendar = EventCalendar(pd.DataFrame([{"symbol": "A", "date": timestamp, "event_type": "EX_DIVIDEND"}]))
    residual = ResidualGridStrategy(config, "A", "B", events=calendar)
    assert residual._event_check(timestamp, -1).blocked  # A is short
    assert not residual._event_check(timestamp, 1).blocked  # A is long; B is short
    pair = StockPairGridStrategy(config, "A", "B", events=calendar)
    assert not pair._event_check(timestamp, 1).blocked  # A long / B short
    assert pair._event_check(timestamp, -1).blocked  # A short / B long


def test_existing_short_dividend_exit_reserves_next_open_and_holiday_margin(config):
    event_date = pd.Timestamp("2025-01-10")
    check_date = pd.Timestamp("2025-01-06")  # four weekdays before event
    calendar = EventCalendar(pd.DataFrame([{"symbol": "A", "date": event_date, "event_type": "EX_DIVIDEND"}]))
    strategy = ResidualGridStrategy(config, "A", "B", events=calendar)
    assert not strategy._event_check(check_date, -1, existing_position=False).blocked
    assert strategy._event_check(check_date, -1, existing_position=True).blocked
