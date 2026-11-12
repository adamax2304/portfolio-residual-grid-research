from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import pandas as pd

from residual_grid_research.models import Decision, OrderIntent, Position, StrategyState
from residual_grid_research.risk import RiskManager
from .state_machine import StrategyStateMachine


class PortfolioView(Protocol):
    equity: float
    positions: dict[str, Position]
    prices: dict[str, float]


@dataclass
class Campaign:
    group_id: str = ""
    direction: int = 0
    layers: int = 0
    entry_time: pd.Timestamp | None = None
    take_profit_stage: int = 0
    layer_notionals: list[float] = field(default_factory=list)
    breakout_direction: int = 0
    breakout_level: float | None = None
    breakout_peak: float = 0.0
    stop_price: float | None = None
    catastrophic_stop_price: float | None = None
    invalidation_price: float | None = None
    grid_prices: list[float] = field(default_factory=list)

    def reset(self) -> None:
        self.group_id = ""
        self.direction = 0
        self.layers = 0
        self.entry_time = None
        self.take_profit_stage = 0
        self.layer_notionals = []
        self.breakout_direction = 0
        self.breakout_level = None
        self.breakout_peak = 0.0
        self.stop_price = None
        self.catastrophic_stop_price = None
        self.invalidation_price = None
        self.grid_prices = []


class BaseStrategy:
    name = "base"

    def __init__(self, config: dict, symbol: str) -> None:
        self.config = config
        self.symbol = symbol.upper()
        self.machine = StrategyStateMachine(self.name, self.symbol)
        self.risk_manager = RiskManager(config)
        self.campaign = Campaign()
        self.prepared = pd.DataFrame()
        self.last_processed: pd.Timestamp | None = None
        self.cooldown_until: pd.Timestamp | None = None

    @property
    def decisions(self) -> list[Decision]:
        return self.machine.decisions

    @property
    def required_symbols(self) -> list[str]:
        raise NotImplementedError

    def prepare(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        raise NotImplementedError

    def on_bar(self, timestamp: pd.Timestamp, portfolio: PortfolioView) -> list[OrderIntent]:
        raise NotImplementedError

    def pending_order_valid(
        self,
        timestamp: pd.Timestamp,
        intent: OrderIntent,
        portfolio: PortfolioView,
    ) -> tuple[bool, str]:
        """Validate a previously queued order using information known before the open."""
        return True, "valid"

    def protective_orders_at_bar(
        self,
        timestamp: pd.Timestamp,
        portfolio: PortfolioView,
        bars: dict[str, pd.Series],
    ) -> list[OrderIntent]:
        """Return already-live protective orders before discretionary bar logic runs."""
        return []

    def _position_notional(self, symbol: str, portfolio: PortfolioView) -> float:
        position = portfolio.positions.get(symbol)
        return abs(position.quantity * portfolio.prices.get(symbol, position.average_price)) if position else 0.0

    def exposure_snapshot(self, timestamp: pd.Timestamp, portfolio: PortfolioView) -> dict[str, float]:
        if portfolio.equity <= 0:
            return {"net_beta_exposure": 0.0}
        net = sum(
            position.quantity * portfolio.prices.get(symbol, position.average_price)
            for symbol, position in portfolio.positions.items()
        )
        return {"net_beta_exposure": float(net / portfolio.equity)}

    def _close_order(self, symbol: str, portfolio: PortfolioView, reason: str, fraction: float = 1.0) -> OrderIntent | None:
        position = portfolio.positions.get(symbol)
        if position is None or position.is_flat:
            return None
        side = "SELL" if position.quantity > 0 else "BUY"
        from residual_grid_research.models import Side
        return OrderIntent(
            symbol=symbol,
            side=Side(side),
            notional_usd=abs(position.quantity * portfolio.prices.get(symbol, position.average_price)) * fraction,
            reason=reason,
            strategy=self.name,
            group_id=self.campaign.group_id,
            reduce_only=True,
            metadata={"close_fraction": fraction, "close_all": fraction >= 1.0},
        )

    def _finish_exit_if_flat(self, timestamp: pd.Timestamp, portfolio: PortfolioView) -> None:
        if self.machine.state in {StrategyState.GRID_EXITING, StrategyState.KILL}:
            if all(portfolio.positions.get(s) is None or portfolio.positions[s].is_flat for s in self.required_symbols):
                if self.machine.state == StrategyState.KILL:
                    self.machine.transition(timestamp, StrategyState.COOLDOWN, "kill orders completed")
                    days = int(self.config["risk"]["cooldown_days"])
                    self.cooldown_until = timestamp + pd.offsets.BDay(days)
                else:
                    self.machine.transition(timestamp, StrategyState.FLAT, "exit orders completed")
                self.campaign.reset()
        if self.machine.state == StrategyState.COOLDOWN and self.cooldown_until is not None:
            if timestamp >= self.cooldown_until:
                self.machine.transition(timestamp, StrategyState.FLAT, "cooldown completed")
        if self.machine.state == StrategyState.FLAT:
            self.machine.transition(timestamp, StrategyState.SCAN, "resume scanning")
