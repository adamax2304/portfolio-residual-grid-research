from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"


class StrategyState(str, Enum):
    SCAN = "SCAN"
    CANDIDATE = "CANDIDATE"
    ARMED = "ARMED"
    GRID_ACTIVE = "GRID_ACTIVE"
    WARNING = "WARNING"
    GRID_EXITING = "GRID_EXITING"
    BREAKOUT_SETUP = "BREAKOUT_SETUP"
    BREAKOUT_ACTIVE = "BREAKOUT_ACTIVE"
    KILL = "KILL"
    COOLDOWN = "COOLDOWN"
    FLAT = "FLAT"


@dataclass(slots=True)
class OrderIntent:
    symbol: str
    side: Side
    notional_usd: float
    reason: str
    strategy: str
    group_id: str
    reduce_only: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    order_type: OrderType = OrderType.MARKET
    requested_price: float | None = None
    time_in_force: str = "NEXT_BAR"


@dataclass(slots=True)
class Fill:
    timestamp: datetime
    symbol: str
    side: Side
    quantity: float
    price: float
    gross_notional: float
    commission: float
    friction_cost: float
    strategy: str
    group_id: str
    reason: str
    realized_pnl: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    order_type: OrderType = OrderType.MARKET
    requested_price: float | None = None
    reference_price: float | None = None
    spread_cost: float = 0.0
    slippage_cost: float = 0.0
    fill_reason: str = ""
    candle_open: float | None = None
    candle_high: float | None = None
    candle_low: float | None = None
    candle_close: float | None = None
    state_before: str = ""
    state_after: str = ""
    unrealized_pnl: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["side"] = self.side.value
        result["order_type"] = self.order_type.value
        return result


@dataclass(slots=True)
class Position:
    symbol: str
    quantity: float = 0.0
    average_price: float = 0.0
    realized_pnl: float = 0.0

    @property
    def is_flat(self) -> bool:
        return abs(self.quantity) < 1e-12

    def market_value(self, price: float) -> float:
        return self.quantity * price


@dataclass(slots=True)
class Decision:
    timestamp: datetime
    strategy: str
    state_from: StrategyState
    state_to: StrategyState
    reason: str
    score: float | None = None
    symbol: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["state_from"] = self.state_from.value
        result["state_to"] = self.state_to.value
        return result


@dataclass(slots=True)
class BacktestResult:
    strategy_name: str
    equity_curve: Any
    fills: list[Fill]
    decisions: list[Decision]
    metrics: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    campaigns: list[dict[str, Any]] = field(default_factory=list)
    exposure_curve: Any = None
    order_audit: list[dict[str, Any]] = field(default_factory=list)
    subledgers: list[dict[str, Any]] = field(default_factory=list)
