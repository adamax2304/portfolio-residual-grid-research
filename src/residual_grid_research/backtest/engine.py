from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
import pandas as pd

from residual_grid_research.models import (
    BacktestResult,
    Decision,
    Fill,
    OrderIntent,
    OrderType,
    Position,
    Side,
    StrategyState,
)
from residual_grid_research.risk import RiskManager
from .metrics import calculate_metrics


def resolve_barrier_touch(
    bar: pd.Series | dict,
    *,
    stop: float,
    target: float,
    direction: int,
    mode: str = "adverse_first",
) -> str | None:
    """Resolve an OHLC bar touching stop and target without unknowable tick ordering."""
    if direction not in {-1, 1}:
        raise ValueError("direction must be -1 or 1")
    high, low = float(bar["high"]), float(bar["low"])
    stop_hit = low <= stop if direction > 0 else high >= stop
    target_hit = high >= target if direction > 0 else low <= target
    if stop_hit and target_hit:
        if mode not in {"adverse_first", "tp_first"}:
            raise ValueError("mode must be adverse_first or tp_first")
        return "stop" if mode == "adverse_first" else "target"
    if stop_hit:
        return "stop"
    if target_hit:
        return "target"
    return None


@dataclass
class _Account:
    cash: float
    positions: dict[str, Position]
    prices: dict[str, float]
    equity: float
    active_group: str | None = None
    campaign_start_equity: float | None = None


class BacktestEngine:
    """Chronological next-bar-open simulator with costs on every fill."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.risk = RiskManager(config)
        self.costs = config["costs"]
        self.starting_capital = float(config["project"]["starting_capital_usd"])

    def run(
        self,
        strategy,
        data: dict[str, pd.DataFrame],
        *,
        trade_start: pd.Timestamp | str | None = None,
    ) -> BacktestResult:
        required = list(dict.fromkeys(getattr(strategy, "required_symbols", data.keys())))
        scoped_data = {symbol: data[symbol] for symbol in required if symbol in data}
        if scoped_data:
            data = scoped_data
        prepared = strategy.prepare(data)
        if prepared.empty:
            raise ValueError("Strategy produced no aligned feature rows")
        timeline = prepared.index.sort_values().unique()
        trade_start_at = pd.Timestamp(trade_start) if trade_start is not None else None
        if trade_start_at is not None and getattr(timeline, "tz", None) is not None and trade_start_at.tzinfo is None:
            trade_start_at = trade_start_at.tz_localize(timeline.tz)
        account = _Account(self.starting_capital, {}, {}, self.starting_capital)
        pending: list[OrderIntent] = []
        fills: list[Fill] = []
        equity_values: list[float] = []
        equity_times: list[pd.Timestamp] = []
        exposure_rows: list[dict[str, float]] = []
        order_audit: list[dict] = []
        warnings: list[str] = []
        financing_cost = 0.0
        financing_by_group: dict[str, float] = {}
        previous_time: pd.Timestamp | None = None
        current_day = None
        current_week = None
        day_start_equity = self.starting_capital
        week_start_equity = self.starting_capital

        for timestamp in timeline:
            timestamp = pd.Timestamp(timestamp)
            day_key = timestamp.date()
            iso = timestamp.isocalendar()
            week_key = (int(iso.year), int(iso.week))
            if day_key != current_day:
                current_day = day_key
                day_start_equity = account.equity
            if week_key != current_week:
                current_week = week_key
                week_start_equity = account.equity
            if previous_time is not None:
                days = max(0.0, (timestamp - previous_time).total_seconds() / 86400)
                charge = self._financing_charge(account, days)
                account.cash -= charge
                financing_cost += charge
                if account.active_group is not None:
                    financing_by_group[account.active_group] = financing_by_group.get(account.active_group, 0.0) + charge
            open_prices = self._prices_at(data, timestamp, "open", account.prices)
            account.prices = open_prices
            positions_before_open = any(not position.is_flat for position in account.positions.values())

            # Resting protective stops are evaluated before queued discretionary
            # orders. This guarantees adverse-first ordering when a stop and a
            # take-profit/add are both reachable in the same candle.
            protective = self._protective_orders(strategy, timestamp, account, data)
            if protective:
                protected_groups = {intent.group_id for intent in protective}
                kept: list[OrderIntent] = []
                for intent in pending:
                    if intent.group_id in protected_groups and not intent.reduce_only:
                        order_audit.append(self._unfilled_audit(intent, timestamp, data, strategy, "cancelled by protective stop"))
                    else:
                        kept.append(intent)
                pending = kept
                for intent in protective:
                    reference = open_prices.get(intent.symbol)
                    if reference is None:
                        continue
                    fill = self._execute(
                        intent, timestamp, float(reference), account,
                        bar=self._bar_at(data, intent.symbol, timestamp),
                        state_before=str(intent.metadata.get("state_before_protection", strategy.machine.state.value)),
                        state_after=strategy.machine.state.value,
                    )
                    if fill is not None:
                        fills.append(fill)
                        order_audit.append(self._fill_audit(fill))
            if pending:
                still_pending: list[OrderIntent] = []
                for intent in pending:
                    reference = open_prices.get(intent.symbol)
                    if reference is None or not np.isfinite(reference) or reference <= 0:
                        still_pending.append(intent)
                        continue
                    view = SimpleNamespace(cash=account.cash, equity=self._equity(account), positions=account.positions, prices=account.prices)
                    valid, invalid_reason = strategy.pending_order_valid(timestamp, intent, view) if hasattr(strategy, "pending_order_valid") else (True, "valid")
                    if not valid:
                        order_audit.append(self._unfilled_audit(intent, timestamp, data, strategy, invalid_reason))
                        continue
                    bar = self._bar_at(data, intent.symbol, timestamp)
                    state_before = strategy.machine.state.value
                    fill = self._execute(
                        intent, timestamp, float(reference), account, bar=bar,
                        state_before=state_before, state_after=strategy.machine.state.value,
                    )
                    if fill is not None:
                        fills.append(fill)
                        order_audit.append(self._fill_audit(fill))
                    elif str(intent.time_in_force).upper() == "GTC":
                        still_pending.append(intent)
                    else:
                        order_audit.append(self._unfilled_audit(intent, timestamp, data, strategy, "price did not reach order"))
                pending = still_pending

            # A newly filled entry can be stopped later in the same bar. With no
            # lower-timeframe path available, this adverse sequence is assumed.
            if not positions_before_open and any(not position.is_flat for position in account.positions.values()):
                protective = self._protective_orders(strategy, timestamp, account, data)
                for intent in protective:
                    reference = open_prices.get(intent.symbol)
                    if reference is None:
                        continue
                    fill = self._execute(
                        intent, timestamp, float(reference), account,
                        bar=self._bar_at(data, intent.symbol, timestamp),
                        state_before=str(intent.metadata.get("state_before_protection", strategy.machine.state.value)),
                        state_after=strategy.machine.state.value,
                    )
                    if fill is not None:
                        fills.append(fill)
                        order_audit.append(self._fill_audit(fill))
            account.prices = self._prices_at(data, timestamp, "close", account.prices)
            account.equity = self._equity(account)
            kill_reason = None
            if account.equity <= day_start_equity * (1 - float(self.config["risk"]["max_daily_loss_pct"])):
                kill_reason = "daily loss kill-switch"
            elif account.equity <= week_start_equity * (1 - float(self.config["risk"]["max_weekly_loss_pct"])):
                kill_reason = "weekly loss kill-switch"
            if (
                kill_reason is None
                and account.active_group is not None
                and account.campaign_start_equity is not None
            ):
                risk_budget = self.starting_capital * float(self.config["risk"]["max_risk_per_trade_pct"])
                mae_limit = risk_budget * float(self.config["risk"].get("max_campaign_mae_r", 1.0))
                if account.equity - account.campaign_start_equity <= -mae_limit:
                    kill_reason = "campaign maximum adverse excursion stop"
            trading_enabled = trade_start_at is None or timestamp >= trade_start_at
            if not trading_enabled:
                pass
            elif kill_reason and any(not p.is_flat for p in account.positions.values()):
                pending.extend(self._liquidation_intents(account, strategy.name, timestamp, kill_reason))
                if strategy.machine.state not in {StrategyState.KILL, StrategyState.COOLDOWN}:
                    try:
                        strategy.machine.transition(timestamp, StrategyState.KILL, kill_reason)
                    except ValueError:
                        pass
            else:
                view = SimpleNamespace(
                    cash=account.cash,
                    equity=account.equity,
                    positions=account.positions,
                    prices=account.prices,
                )
                intents = strategy.on_bar(timestamp, view)
                approved, rejected = self.risk.approve_batch(
                    intents,
                    equity=max(account.equity, 1.0),
                    prices=account.prices,
                    positions=account.positions,
                )
                pending.extend(approved)
                for intent, reason in rejected:
                    warnings.append(f"{timestamp}: rejected {intent.symbol} order: {reason}")
                    order_audit.append(self._unfilled_audit(intent, timestamp, data, strategy, f"risk rejected: {reason}"))
            account.equity = self._equity(account)
            view = SimpleNamespace(
                cash=account.cash,
                equity=account.equity,
                positions=account.positions,
                prices=account.prices,
            )
            gross = sum(
                abs(position.quantity * account.prices.get(symbol, position.average_price))
                for symbol, position in account.positions.items()
            )
            strategy_exposure = strategy.exposure_snapshot(timestamp, view) if hasattr(strategy, "exposure_snapshot") else {}
            exposure_rows.append({
                "gross_leverage": float(gross / account.equity) if account.equity > 0 else 0.0,
                "net_beta_exposure": float(strategy_exposure.get("net_beta_exposure", 0.0)),
            })
            equity_times.append(timestamp)
            equity_values.append(account.equity)
            previous_time = timestamp

        if pending:
            warnings.append(f"{len(pending)} next-bar order(s) remained unfilled at end of sample")
        if any(not p.is_flat for p in account.positions.values()):
            last_time = pd.Timestamp(timeline[-1])
            for intent in self._liquidation_intents(account, strategy.name, last_time, "end-of-sample liquidation"):
                reference = account.prices[intent.symbol]
                bar = self._bar_at(data, intent.symbol, last_time)
                fill = self._execute(intent, last_time, reference, account, bar=bar, force_complete=True)
                if fill:
                    fills.append(fill)
                    order_audit.append(self._fill_audit(fill))
            equity_values[-1] = self._equity(account)
        equity_curve = pd.Series(equity_values, index=pd.DatetimeIndex(equity_times), name="equity")
        exposure_curve = pd.DataFrame(exposure_rows, index=pd.DatetimeIndex(equity_times))
        campaigns = self._campaign_statistics(
            fills, data, equity_curve, financing_by_group, list(strategy.decisions)
        )
        subledgers = [
            {
                "campaign_id": campaign["group_id"],
                "ledger": ledger,
                "realized_pnl_usd": campaign[pnl_column],
                "campaign_pnl_usd": campaign["pnl_usd"],
                "reconciled": abs(
                    campaign["grid_pnl_usd"]
                    + campaign["breakout_pnl_usd"]
                    - campaign["pnl_usd"]
                ) < 1e-8,
            }
            for campaign in campaigns
            for ledger, pnl_column in (
                ("grid_ledger", "grid_pnl_usd"),
                ("breakout_ledger", "breakout_pnl_usd"),
            )
        ]
        metrics = calculate_metrics(
            equity_curve,
            fills,
            strategy.decisions,
            starting_capital=self.starting_capital,
            financing_cost=financing_cost,
            campaigns=campaigns,
            exposure_curve=exposure_curve,
        )
        return BacktestResult(
            getattr(strategy, "run_name", strategy.name),
            equity_curve,
            fills,
            list(strategy.decisions),
            metrics,
            warnings,
            campaigns,
            exposure_curve,
            order_audit,
            subledgers,
        )

    @staticmethod
    def _prices_at(
        data: dict[str, pd.DataFrame], timestamp: pd.Timestamp, column: str, previous: dict[str, float]
    ) -> dict[str, float]:
        prices = dict(previous)
        for symbol, frame in data.items():
            if timestamp in frame.index and column in frame:
                value = frame.at[timestamp, column]
                if pd.notna(value):
                    prices[symbol] = float(value)
        return prices

    @staticmethod
    def _protective_orders(strategy, timestamp: pd.Timestamp, account: _Account, data: dict[str, pd.DataFrame]) -> list[OrderIntent]:
        if not hasattr(strategy, "protective_orders_at_bar"):
            return []
        view = SimpleNamespace(
            cash=account.cash,
            equity=BacktestEngine._equity(account),
            positions=account.positions,
            prices=account.prices,
        )
        bars = {
            symbol: frame.loc[timestamp]
            for symbol, frame in data.items()
            if timestamp in frame.index
        }
        return strategy.protective_orders_at_bar(timestamp, view, bars)

    @staticmethod
    def _fill_audit(fill: Fill) -> dict:
        return {
            "campaign_id": fill.group_id,
            "timestamp": fill.timestamp,
            "symbol": fill.symbol,
            "state_before": fill.state_before,
            "order_type": fill.order_type.value,
            "requested_price": fill.requested_price,
            "candle_open": fill.candle_open,
            "candle_high": fill.candle_high,
            "candle_low": fill.candle_low,
            "candle_close": fill.candle_close,
            "fill_price": fill.price,
            "fill_reason": fill.fill_reason,
            "state_after": fill.state_after,
            "cost": fill.commission + fill.friction_cost,
            "spread_cost": fill.spread_cost,
            "slippage": fill.slippage_cost,
            "realized_pnl": fill.realized_pnl,
            "unrealized_pnl": fill.unrealized_pnl,
            "status": "FILLED",
            "strategy_reason": fill.reason,
        }

    @staticmethod
    def _unfilled_audit(
        intent: OrderIntent,
        timestamp: pd.Timestamp,
        data: dict[str, pd.DataFrame],
        strategy,
        reason: str,
    ) -> dict:
        bar = BacktestEngine._bar_at(data, intent.symbol, timestamp)
        value = lambda key: float(bar[key]) if bar is not None and key in bar and pd.notna(bar[key]) else None
        return {
            "campaign_id": intent.group_id,
            "timestamp": timestamp,
            "symbol": intent.symbol,
            "state_before": strategy.machine.state.value,
            "order_type": intent.order_type.value,
            "requested_price": intent.requested_price,
            "candle_open": value("open"),
            "candle_high": value("high"),
            "candle_low": value("low"),
            "candle_close": value("close"),
            "fill_price": None,
            "fill_reason": reason,
            "state_after": strategy.machine.state.value,
            "cost": 0.0,
            "spread_cost": 0.0,
            "slippage": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "status": "CANCELLED" if "cancel" in reason or "invalid" in reason or "rejected" in reason else "NOT_FILLED",
            "strategy_reason": intent.reason,
        }

    def _execute(
        self,
        intent: OrderIntent,
        timestamp: pd.Timestamp,
        reference_price: float,
        account: _Account,
        *,
        bar: pd.Series | None = None,
        force_complete: bool = False,
        state_before: str = "",
        state_after: str = "",
    ) -> Fill | None:
        position = account.positions.setdefault(intent.symbol, Position(intent.symbol))
        order_type = intent.order_type if isinstance(intent.order_type, OrderType) else OrderType(str(intent.order_type).upper())
        requested = float(intent.requested_price) if intent.requested_price is not None else None
        candle_open = float(bar["open"]) if bar is not None and pd.notna(bar.get("open")) else reference_price
        candle_high = float(bar["high"]) if bar is not None and pd.notna(bar.get("high")) else reference_price
        candle_low = float(bar["low"]) if bar is not None and pd.notna(bar.get("low")) else reference_price
        candle_close = float(bar["close"]) if bar is not None and pd.notna(bar.get("close")) else reference_price
        side_sign = 1 if intent.side == Side.BUY else -1
        fill_reason = "next-bar market open"
        fill_reference = reference_price
        if not force_complete and order_type == OrderType.LIMIT:
            if requested is None:
                raise ValueError("LIMIT order requires requested_price")
            touched = candle_low <= requested if side_sign > 0 else candle_high >= requested
            if not touched:
                return None
            fill_reference = min(candle_open, requested) if side_sign > 0 else max(candle_open, requested)
            fill_reason = "limit touched" if candle_open != fill_reference else "favorable gap through limit"
        elif not force_complete and order_type == OrderType.STOP:
            if requested is None:
                raise ValueError("STOP order requires requested_price")
            touched = candle_high >= requested if side_sign > 0 else candle_low <= requested
            if not touched:
                return None
            fill_reference = max(candle_open, requested) if side_sign > 0 else min(candle_open, requested)
            fill_reason = "stop touched" if candle_open == requested or (
                side_sign > 0 and candle_open < requested
            ) or (side_sign < 0 and candle_open > requested) else "gap through stop"
        ratio = 1.0 if force_complete else float(self.costs["partial_fill_ratio"])
        quantity = intent.notional_usd / max(fill_reference, 1e-12) * ratio
        if intent.reduce_only:
            if position.is_flat:
                return None
            desired_sign = -1 if position.quantity > 0 else 1
            if (intent.side == Side.BUY and desired_sign < 0) or (intent.side == Side.SELL and desired_sign > 0):
                return None
            if bool(intent.metadata.get("close_all")):
                quantity = abs(position.quantity)
            elif "close_fraction" in intent.metadata:
                quantity = abs(position.quantity) * float(intent.metadata["close_fraction"]) * ratio
            else:
                quantity = min(quantity, abs(position.quantity))
        if quantity <= 1e-12:
            return None
        spread_bps = float(self.costs["spread_bps"]) / 2
        slippage_bps = float(self.costs["slippage_bps"])
        impact_bps = spread_bps + slippage_bps
        execution_price = fill_reference * (1 + side_sign * impact_bps / 10000)
        if order_type == OrderType.LIMIT and requested is not None:
            execution_price = min(execution_price, requested) if side_sign > 0 else max(execution_price, requested)
        execution_price = float(np.clip(execution_price, candle_low, candle_high))
        friction = abs(execution_price - fill_reference) * quantity
        spread_share = spread_bps / impact_bps if impact_bps else 0.0
        spread_cost = friction * spread_share
        slippage_cost = friction - spread_cost
        commission = float(self.costs["commission_per_fill_usd"])
        signed_quantity = side_sign * quantity
        if not intent.reduce_only and account.active_group is None:
            account.active_group = intent.group_id
            account.campaign_start_equity = account.equity
        realized = self._update_position(position, signed_quantity, execution_price)
        account.cash -= signed_quantity * execution_price + commission
        unrealized = sum(
            item.quantity * (account.prices.get(symbol, item.average_price) - item.average_price)
            for symbol, item in account.positions.items()
        )
        fill_metadata = dict(intent.metadata)
        fill_metadata.setdefault(
            "subledger",
            "breakout_ledger" if "breakout" in intent.reason.lower() else "grid_ledger",
        )
        fill = Fill(
            timestamp=timestamp.to_pydatetime(),
            symbol=intent.symbol,
            side=intent.side,
            quantity=quantity,
            price=execution_price,
            gross_notional=quantity * execution_price,
            commission=commission,
            friction_cost=friction,
            strategy=intent.strategy,
            group_id=intent.group_id,
            reason=intent.reason,
            realized_pnl=realized,
            metadata=fill_metadata,
            order_type=order_type,
            requested_price=requested,
            reference_price=fill_reference,
            spread_cost=spread_cost,
            slippage_cost=slippage_cost,
            fill_reason="end-of-sample liquidation" if force_complete else fill_reason,
            candle_open=candle_open,
            candle_high=candle_high,
            candle_low=candle_low,
            candle_close=candle_close,
            state_before=state_before,
            state_after=state_after,
            unrealized_pnl=float(unrealized),
        )
        if intent.reduce_only and all(item.is_flat for item in account.positions.values()):
            account.active_group = None
            account.campaign_start_equity = None
        return fill

    @staticmethod
    def _update_position(position: Position, signed_quantity: float, price: float) -> float:
        old_quantity = position.quantity
        if abs(old_quantity) < 1e-12 or np.sign(old_quantity) == np.sign(signed_quantity):
            total = abs(old_quantity) + abs(signed_quantity)
            position.average_price = (
                abs(old_quantity) * position.average_price + abs(signed_quantity) * price
            ) / total
            position.quantity = old_quantity + signed_quantity
            return 0.0
        closing = min(abs(old_quantity), abs(signed_quantity))
        realized = closing * (price - position.average_price) * np.sign(old_quantity)
        new_quantity = old_quantity + signed_quantity
        if abs(new_quantity) < 1e-12:
            position.quantity = 0.0
            position.average_price = 0.0
        elif np.sign(new_quantity) != np.sign(old_quantity):
            position.quantity = new_quantity
            position.average_price = price
        else:
            position.quantity = new_quantity
        position.realized_pnl += float(realized)
        return float(realized)

    @staticmethod
    def _equity(account: _Account) -> float:
        return float(account.cash + sum(
            position.quantity * account.prices.get(symbol, position.average_price)
            for symbol, position in account.positions.items()
        ))

    @staticmethod
    def _bar_at(
        data: dict[str, pd.DataFrame], symbol: str, timestamp: pd.Timestamp
    ) -> pd.Series | None:
        frame = data.get(symbol)
        if frame is None or timestamp not in frame.index:
            return None
        return frame.loc[timestamp]

    def _financing_charge(self, account: _Account, days: float) -> float:
        if days <= 0:
            return 0.0
        short_gross = sum(
            abs(position.quantity * account.prices.get(symbol, position.average_price))
            for symbol, position in account.positions.items() if position.quantity < 0
        )
        total_gross = sum(
            abs(position.quantity * account.prices.get(symbol, position.average_price))
            for symbol, position in account.positions.items()
        )
        return float(
            short_gross * float(self.costs["short_borrow_annual_pct"]) * days / 365
            + total_gross * float(self.costs["overnight_holding_annual_pct"]) * days / 365
        )

    @staticmethod
    def _liquidation_intents(
        account: _Account, strategy_name: str, timestamp: pd.Timestamp, reason: str
    ) -> list[OrderIntent]:
        result: list[OrderIntent] = []
        group_id = account.active_group or f"risk:{timestamp.isoformat()}"
        for symbol, position in account.positions.items():
            if position.is_flat:
                continue
            price = account.prices.get(symbol, position.average_price)
            result.append(OrderIntent(
                symbol=symbol,
                side=Side.SELL if position.quantity > 0 else Side.BUY,
                notional_usd=abs(position.quantity * price),
                reason=reason,
                strategy=strategy_name,
                group_id=group_id,
                reduce_only=True,
                metadata={"close_fraction": 1.0, "close_all": True},
            ))
        return result

    def _campaign_statistics(
        self,
        fills: list[Fill],
        data: dict[str, pd.DataFrame],
        equity_curve: pd.Series,
        financing_by_group: dict[str, float],
        decisions: list[Decision],
    ) -> list[dict]:
        groups: dict[str, list[Fill]] = {}
        for fill in fills:
            groups.setdefault(fill.group_id, []).append(fill)
        results: list[dict] = []
        risk_dollars = self.starting_capital * float(self.config["risk"]["max_risk_per_trade_pct"])
        for group_id, group_fills in groups.items():
            group_fills = sorted(group_fills, key=lambda fill: pd.Timestamp(fill.timestamp))
            start = pd.Timestamp(group_fills[0].timestamp)
            end = pd.Timestamp(group_fills[-1].timestamp)
            relevant_index = equity_curve.loc[start:end].index
            quantities: dict[str, float] = {}
            cashflow = 0.0
            fill_cursor = 0
            path: list[float] = []
            for timestamp in relevant_index:
                while fill_cursor < len(group_fills) and pd.Timestamp(group_fills[fill_cursor].timestamp) <= timestamp:
                    fill = group_fills[fill_cursor]
                    signed = fill.quantity if fill.side == Side.BUY else -fill.quantity
                    quantities[fill.symbol] = quantities.get(fill.symbol, 0.0) + signed
                    cashflow -= signed * fill.price + fill.commission
                    fill_cursor += 1
                market_value = 0.0
                for symbol, quantity in quantities.items():
                    frame = data.get(symbol)
                    if frame is not None and timestamp in frame.index:
                        market_value += quantity * float(frame.at[timestamp, "close"])
                path.append(cashflow + market_value)
            while fill_cursor < len(group_fills):
                fill = group_fills[fill_cursor]
                signed = fill.quantity if fill.side == Side.BUY else -fill.quantity
                quantities[fill.symbol] = quantities.get(fill.symbol, 0.0) + signed
                cashflow -= signed * fill.price + fill.commission
                fill_cursor += 1
            closed = all(abs(quantity) < 1e-8 for quantity in quantities.values())
            financing = float(financing_by_group.get(group_id, 0.0))
            pnl_before_financing = cashflow if closed else (path[-1] if path else cashflow)
            pnl = pnl_before_financing - financing
            grid_pnl, breakout_pnl, transfer_time = self._subledger_attribution(
                group_fills,
                data,
                decisions,
                start=start,
                end=end,
                campaign_pnl=float(pnl),
                financing=financing,
            )
            financed_path = [*path, pnl]
            reasons = " ".join(fill.reason.lower() for fill in group_fills)
            entry_fills = [fill for fill in group_fills if not fill.metadata.get("close_fraction") and not fill.metadata.get("close_all")]
            entry_fill = entry_fills[0] if entry_fills else group_fills[0]
            last_timestamp = pd.Timestamp(group_fills[-1].timestamp)
            exit_fills = [fill for fill in group_fills if pd.Timestamp(fill.timestamp) == last_timestamp]
            exit_reason = "; ".join(dict.fromkeys(fill.reason for fill in exit_fills))
            entry_reason = entry_fill.reason
            lower_exit = exit_reason.lower()
            if "failed breakout" in lower_exit:
                exit_category = "failed_breakout"
            elif "kill" in lower_exit or "adverse excursion" in lower_exit or "invalidation" in lower_exit:
                exit_category = "kill"
            elif "time stop" in lower_exit or "timed out" in lower_exit:
                exit_category = "time_stop"
            elif "breakout" in lower_exit:
                exit_category = "breakout_exit"
            elif "tp" in lower_exit or "target" in lower_exit or "mean reversion completed" in lower_exit:
                exit_category = "take_profit"
            elif "end-of-sample" in lower_exit:
                exit_category = "end_of_sample"
            else:
                exit_category = "other"
            if ":breakout:" in group_id or "breakout continuation" in entry_reason.lower():
                campaign_mode = "breakout_continuation"
            elif "breakout" in reasons:
                campaign_mode = "hybrid_breakout"
            else:
                campaign_mode = "grid_mean_reversion"
            direction_value = entry_fill.metadata.get("direction")
            if direction_value is None:
                direction_value = 1 if entry_fill.side == Side.BUY else -1
            direction_label = "long_residual" if int(direction_value) > 0 else "short_residual"
            if "failed breakout" in reasons:
                regime = "failed_breakout"
            elif "breakout" in reasons:
                regime = "breakout"
            elif "kill" in reasons or "warning" in reasons or "adverse excursion" in reasons:
                regime = "warning"
            else:
                regime = "range"
            results.append({
                "group_id": group_id,
                "entry_time": start,
                "exit_time": end,
                "duration_hours": (end - start).total_seconds() / 3600,
                "pnl_usd": float(pnl),
                "financing_cost_usd": financing,
                "return_on_risk": float(pnl / risk_dollars) if risk_dollars else 0.0,
                "mae_usd": float(min(financed_path, default=0.0)),
                "mfe_usd": float(max(financed_path, default=0.0)),
                "mae_r": float(min(financed_path, default=0.0) / risk_dollars) if risk_dollars else 0.0,
                "mfe_r": float(max(financed_path, default=0.0) / risk_dollars) if risk_dollars else 0.0,
                "regime": regime,
                "campaign_mode": campaign_mode,
                "direction": direction_label,
                "entry_reason": entry_reason,
                "exit_reason": exit_reason,
                "exit_category": exit_category,
                "closed": closed,
                "fill_count": len(group_fills),
                "grid_pnl_usd": grid_pnl,
                "breakout_pnl_usd": breakout_pnl,
                "subledger_transfer_time": transfer_time,
                "subledger_reconciliation_error": float(grid_pnl + breakout_pnl - pnl),
            })
        return results

    @staticmethod
    def _subledger_attribution(
        group_fills: list[Fill],
        data: dict[str, pd.DataFrame],
        decisions: list[Decision],
        *,
        start: pd.Timestamp,
        end: pd.Timestamp,
        campaign_pnl: float,
        financing: float,
    ) -> tuple[float, float, pd.Timestamp | None]:
        """Split grid/continuation P&L without changing trading mechanics.

        Relationship continuations already open a new breakout campaign. A
        natural grid carries inventory into continuation mode, so the transfer
        is marked at the close that confirmed BREAKOUT_ACTIVE. The two pieces
        always sum exactly to campaign P&L.
        """
        transitions = [
            pd.Timestamp(decision.timestamp)
            for decision in decisions
            if decision.state_to == StrategyState.BREAKOUT_ACTIVE
            and start <= pd.Timestamp(decision.timestamp) <= end
        ]
        transfer = transitions[0] if transitions else None
        entry_fills = [
            fill for fill in group_fills
            if not fill.metadata.get("close_fraction") and not fill.metadata.get("close_all")
        ]
        entry_ledger = (
            str(entry_fills[0].metadata.get("subledger", "grid_ledger"))
            if entry_fills else "grid_ledger"
        )
        if transfer is None:
            if entry_ledger == "breakout_ledger" or ":breakout:" in group_fills[0].group_id:
                return 0.0, float(campaign_pnl), None
            return float(campaign_pnl), 0.0, None

        quantities: dict[str, float] = {}
        cashflow = 0.0
        for fill in group_fills:
            if pd.Timestamp(fill.timestamp) > transfer:
                continue
            signed = fill.quantity if fill.side == Side.BUY else -fill.quantity
            quantities[fill.symbol] = quantities.get(fill.symbol, 0.0) + signed
            cashflow -= signed * fill.price + fill.commission
        market_value = 0.0
        for symbol, quantity in quantities.items():
            frame = data.get(symbol)
            if frame is None:
                continue
            prior = frame.loc[:transfer]
            if not prior.empty:
                market_value += quantity * float(prior.iloc[-1]["close"])
        duration = max((end - start).total_seconds(), 0.0)
        elapsed = max((transfer - start).total_seconds(), 0.0)
        finance_share = financing * min(elapsed / duration, 1.0) if duration else 0.0
        grid_pnl = float(cashflow + market_value - finance_share)
        breakout_pnl = float(campaign_pnl - grid_pnl)
        return grid_pnl, breakout_pnl, transfer
