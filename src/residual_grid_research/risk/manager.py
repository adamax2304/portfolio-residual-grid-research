from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from residual_grid_research.models import OrderIntent, Position


@dataclass(frozen=True, slots=True)
class RiskDecision:
    approved: bool
    reason: str
    allowed_notional: float


class RiskManager:
    """Deterministic grid-aware sizing and portfolio kill-switches."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.starting_capital = float(config["project"]["starting_capital_usd"])
        self.risk = config["risk"]
        self.costs = config["costs"]
        self.kill_history: dict[tuple[str, str], int] = {}

    def relationship_grid_notionals(
        self,
        *,
        residual_std: float,
        grid_levels: list[float],
        kill_z: float,
        equity: float,
    ) -> list[float]:
        """Solve full-stack notional so loss of every layer at kill fits risk budget."""
        if not np.isfinite(residual_std) or residual_std <= 0:
            return [0.0] * len(grid_levels)
        weights = self._layer_weights(len(grid_levels))
        weights /= weights.sum()
        adverse_moves = np.expm1(residual_std * (kill_z - np.asarray(grid_levels)))
        weighted_loss_fraction = float(np.dot(weights, adverse_moves))
        if weighted_loss_fraction <= 0:
            return [0.0] * len(grid_levels)
        risk_budget = min(equity, self.starting_capital) * float(self.risk["max_risk_per_trade_pct"])
        full_stack = risk_budget / weighted_loss_fraction
        leverage_cap = equity * float(self.risk["max_effective_leverage_start"])
        full_stack = min(full_stack, leverage_cap)
        return [float(full_stack * weight) for weight in weights]

    def price_grid_notionals(
        self,
        *,
        entry_price: float,
        stop_price: float,
        equity: float,
        layers: int = 4,
    ) -> list[float]:
        if entry_price <= 0 or stop_price <= 0:
            return [0.0] * layers
        adverse_fraction = abs(entry_price - stop_price) / entry_price
        if adverse_fraction <= 0:
            return [0.0] * layers
        weights = self._layer_weights(layers)
        weights /= weights.sum()
        risk_budget = min(equity, self.starting_capital) * float(self.risk["max_risk_per_trade_pct"])
        full_stack = min(
            risk_budget / adverse_fraction,
            equity * float(self.risk["max_effective_leverage_start"]),
        )
        return [float(full_stack * weight) for weight in weights]

    def _layer_weights(self, layers: int) -> np.ndarray:
        configured = np.asarray(self.risk["layer_weights"], dtype=float)
        if layers == len(configured):
            weights = configured
        elif layers <= 0:
            return np.asarray([], dtype=float)
        else:
            # Preserve a front-light shape for arbitrary 3/4/5-level sensitivity.
            weights = np.linspace(0.8, 1.2, layers)
        return weights / weights.sum()

    def approve(
        self,
        requested_notional: float,
        *,
        equity: float,
        prices: dict[str, float],
        positions: dict[str, Position],
        opens_new_position: bool,
    ) -> RiskDecision:
        if requested_notional < float(self.costs["minimum_order_usd"]):
            return RiskDecision(False, "below minimum order", 0.0)
        open_count = sum(not position.is_flat for position in positions.values())
        if opens_new_position and open_count >= int(self.risk["max_open_positions"]):
            return RiskDecision(False, "maximum open positions reached", 0.0)
        gross = sum(abs(position.quantity * prices.get(symbol, position.average_price)) for symbol, position in positions.items())
        headroom = max(0.0, equity * float(self.risk["max_gross_leverage"]) - gross)
        allowed = min(float(requested_notional), headroom)
        if allowed < float(self.costs["minimum_order_usd"]):
            return RiskDecision(False, "gross leverage limit", 0.0)
        return RiskDecision(True, "approved", allowed)

    def approve_batch(
        self,
        intents: list[OrderIntent],
        *,
        equity: float,
        prices: dict[str, float],
        positions: dict[str, Position],
    ) -> tuple[list[OrderIntent], list[tuple[OrderIntent, str]]]:
        """Approve a same-decision order group atomically.

        A hedged order must not be approved leg-by-leg against stale gross
        exposure. If the complete group cannot fit, every entry leg is scaled by
        the same factor; if any scaled leg is below the minimum, the group is
        rejected rather than leaving an accidental naked leg.
        """
        approved = [intent for intent in intents if intent.reduce_only and intent.notional_usd > 0]
        rejected: list[tuple[OrderIntent, str]] = []
        entries = [intent for intent in intents if not intent.reduce_only and intent.notional_usd > 0]
        if not entries:
            return approved, rejected
        current_symbols = {symbol for symbol, position in positions.items() if not position.is_flat}
        new_symbols = {intent.symbol for intent in entries if intent.symbol not in current_symbols}
        if len(current_symbols | new_symbols) > int(self.risk["max_open_positions"]):
            return approved, [(intent, "maximum open positions reached") for intent in entries]
        current_gross = sum(
            abs(position.quantity * prices.get(symbol, position.average_price))
            for symbol, position in positions.items()
        )
        headroom = max(0.0, equity * float(self.risk["max_gross_leverage"]) - current_gross)
        requested = sum(float(intent.notional_usd) for intent in entries)
        scale = min(1.0, headroom / requested) if requested > 0 else 0.0
        minimum = float(self.costs["minimum_order_usd"])
        if scale <= 0 or any(float(intent.notional_usd) * scale < minimum for intent in entries):
            return approved, [(intent, "atomic group exceeds gross leverage or minimum order") for intent in entries]
        for intent in entries:
            intent.notional_usd = float(intent.notional_usd) * scale
            approved.append(intent)
        return approved, rejected

    def portfolio_kill_reason(
        self,
        equity: float,
        equity_history: pd.Series,
        timestamp: pd.Timestamp,
    ) -> str | None:
        if equity_history.empty:
            return None
        history = equity_history.copy()
        history.index = pd.to_datetime(history.index)
        today = pd.Timestamp(timestamp).normalize()
        today_rows = history[history.index.normalize() == today]
        if len(today_rows):
            day_start = float(today_rows.iloc[0])
            if equity <= day_start * (1 - float(self.risk["max_daily_loss_pct"])):
                return "daily loss kill-switch"
        week_start = today - pd.Timedelta(days=today.weekday())
        week_rows = history[history.index.normalize() >= week_start]
        if len(week_rows):
            start_equity = float(week_rows.iloc[0])
            if equity <= start_equity * (1 - float(self.risk["max_weekly_loss_pct"])):
                return "weekly loss kill-switch"
        return None

    def register_kill(self, symbol: str, timestamp: pd.Timestamp) -> None:
        key = (symbol.upper(), pd.Timestamp(timestamp).strftime("%Y-%m"))
        self.kill_history[key] = self.kill_history.get(key, 0) + 1

    def kill_cap_reached(self, symbol: str, timestamp: pd.Timestamp) -> bool:
        key = (symbol.upper(), pd.Timestamp(timestamp).strftime("%Y-%m"))
        return self.kill_history.get(key, 0) >= int(self.risk["max_kills_per_symbol_per_month"])
