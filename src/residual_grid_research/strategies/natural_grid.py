from __future__ import annotations

import pandas as pd

from residual_grid_research.data.alpha_vantage import core_session, indicator_prices
from residual_grid_research.data.events import EventCalendar
from residual_grid_research.features.liquidity import liquidity_series
from residual_grid_research.features.regime import classify_regime, regime_allows_grid
from residual_grid_research.features.technical import add_technical_features
from residual_grid_research.features.statistics import rolling_relationship
from residual_grid_research.models import OrderIntent, OrderType, Side, StrategyState
from .base import BaseStrategy, PortfolioView
from .breakout import BreakoutEngine


class NaturalLongGridStrategy(BaseStrategy):
    """Unhedged long-only range grid with confirmed upward breakout continuation."""

    name = "natural_long_grid"

    def __init__(self, config: dict, symbol: str, *, events: EventCalendar | None = None) -> None:
        super().__init__(config, symbol)
        self.events = events or EventCalendar()
        self.breakout = BreakoutEngine(config)
        self.run_name = f"natural_long_grid:{self.symbol}"

    @property
    def required_symbols(self) -> list[str]:
        return [self.symbol, "SPY"]

    def prepare(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        settings = self.config["strategy"]["natural"]
        buffer_minutes = int(self.config["data"]["no_trade_window_minutes"])
        execution_source = core_session(data[self.symbol], buffer_minutes)
        source = indicator_prices(execution_source)
        frame = add_technical_features(
            source, pivot_window=int(settings["pivot_window"]),
            range_lookback=int(settings["range_lookback"]),
        )
        market = indicator_prices(core_session(data.get("SPY", data[self.symbol]), buffer_minutes))
        frame["market_regime"] = classify_regime(
            market,
            market_adx_max=float(self.config["features"]["market_adx_max"]),
            atr_expansion_max=float(self.config["features"]["market_atr_expansion_max"]),
        ).reindex(frame.index)
        if "SPY" in data and self.symbol != "SPY":
            market_relation = rolling_relationship(
                source,
                market,
                beta_window=int(self.config["features"]["beta_window"]),
                z_window=int(self.config["features"]["z_window"]),
                correlation_windows=self.config["features"]["correlation_windows"],
            )
            frame["market_beta"] = market_relation["beta"].reindex(frame.index)
        else:
            frame["market_beta"] = 1.0
        frame["dollar_volume_20"] = liquidity_series(source, self.config).reindex(frame.index)
        if "adjusted_close" in execution_source:
            frame["execution_factor"] = (
                execution_source["close"] / execution_source["adjusted_close"].replace(0, pd.NA)
            ).reindex(frame.index)
        else:
            frame["execution_factor"] = 1.0
        self.prepared = frame
        return frame

    def pending_order_valid(
        self, timestamp: pd.Timestamp, intent: OrderIntent, portfolio: PortfolioView
    ) -> tuple[bool, str]:
        if intent.reduce_only:
            return True, "exit order"
        if self.machine.state not in {StrategyState.GRID_ACTIVE, StrategyState.WARNING}:
            return False, f"entry order invalid in {self.machine.state.value}"
        event = self.events.check(
            [self.symbol], timestamp,
            earnings_before=int(self.config["events"]["earnings_before_trading_days"]),
            earnings_after=int(self.config["events"]["earnings_after_trading_days"]),
        )
        return (not event.blocked, "; ".join(event.reasons) or "event safe")

    def exposure_snapshot(self, timestamp: pd.Timestamp, portfolio: PortfolioView) -> dict[str, float]:
        position = portfolio.positions.get(self.symbol)
        if position is None or timestamp not in self.prepared.index or portfolio.equity <= 0:
            return {"net_beta_exposure": 0.0}
        beta = float(self.prepared.at[timestamp, "market_beta"])
        market_value = position.quantity * portfolio.prices.get(self.symbol, position.average_price)
        return {"net_beta_exposure": float(market_value * beta / portfolio.equity)}

    @staticmethod
    def _stop_atr(settings: dict) -> float:
        stop_variant = str(settings.get("stop_variant", "current"))
        if stop_variant == "range_low_0.5_atr":
            return 0.5
        if stop_variant == "range_low_1.0_atr":
            return 1.0
        if stop_variant == "structure_close":
            return 0.0
        return float(settings["hard_stop_atr"])

    def _cost_gate(self, row: pd.Series, settings: dict, equity: float) -> bool:
        round_trip_bps = 2 * (
            float(self.config["costs"]["spread_bps"])
            + float(self.config["costs"]["slippage_bps"])
        )
        diagnostic_multiple = settings.get("cost_aware_tp_multiple")
        if diagnostic_multiple is None:
            expected_step_bps = (
                float(settings["grid_step_atr"])
                * float(row["atr_14"])
                / float(row["close"])
                * 10000
            )
            return expected_step_bps >= round_trip_bps * float(
                self.config["costs"]["costs_safety_multiple"]
            )

        tp_mode = str(settings.get("tp_mode", "range_scaleout"))
        step_multiple = {"0.5_step": 0.5, "1.0_step": 1.0, "1.5_step": 1.5}.get(tp_mode)
        if step_multiple is None:
            target = (float(row["range_low"]) + float(row["range_high"])) / 2
            tp_distance = max(target - float(row["close"]), 0.0)
        else:
            tp_distance = step_multiple * float(settings["grid_step_atr"]) * float(row["atr_14"])
        expected_tp_bps = tp_distance / max(float(row["close"]), 1e-12) * 10000

        stop = float(row["range_low"]) - self._stop_atr(settings) * float(row["atr_14"])
        if (
            str(settings.get("stop_trigger_mode", "legacy_close_or_two_close")) == "close_confirmation"
            and settings.get("catastrophic_stop_atr") is not None
        ):
            stop = float(row["range_low"]) - float(settings["catastrophic_stop_atr"]) * float(row["atr_14"])
        notionals = self.risk_manager.price_grid_notionals(
            entry_price=float(row["close"]),
            stop_price=stop,
            equity=equity,
            layers=int(settings.get("grid_level_count", 4)),
        )
        first_notional = notionals[0] if notionals else float(self.config["costs"]["minimum_order_usd"])
        commission_bps = (
            2 * float(self.config["costs"]["commission_per_fill_usd"])
            / max(first_notional, 1e-12)
            * 10000
        )
        return expected_tp_bps >= (round_trip_bps + commission_bps) * float(diagnostic_multiple)

    def protective_orders_at_bar(
        self,
        timestamp: pd.Timestamp,
        portfolio: PortfolioView,
        bars: dict[str, pd.Series],
    ) -> list[OrderIntent]:
        if self.machine.state not in {StrategyState.GRID_ACTIVE, StrategyState.WARNING}:
            return []
        position = portfolio.positions.get(self.symbol)
        bar = bars.get(self.symbol)
        if position is None or position.is_flat or bar is None:
            return []
        settings = self.config["strategy"]["natural"]
        mode = str(settings.get("stop_trigger_mode", "legacy_close_or_two_close"))
        stop_price = (
            self.campaign.stop_price
            if mode == "intrabar"
            else self.campaign.catastrophic_stop_price
            if mode == "close_confirmation"
            else None
        )
        if stop_price is None or pd.isna(bar.get("low")) or float(bar["low"]) > float(stop_price):
            return []
        reason = "natural intrabar hard stop" if mode == "intrabar" else "natural catastrophic stop"
        state_before = self.machine.state.value
        self.machine.transition(timestamp, StrategyState.KILL, reason)
        self.risk_manager.register_kill(self.symbol, timestamp)
        order = self._close_order(self.symbol, portfolio, reason)
        if order is None:
            return []
        order.order_type = OrderType.STOP
        order.requested_price = float(stop_price)
        order.time_in_force = "GTC"
        order.metadata["state_before_protection"] = state_before
        order.metadata["stop_trigger_mode"] = mode
        return [order]

    def on_bar(self, timestamp: pd.Timestamp, portfolio: PortfolioView) -> list[OrderIntent]:
        timestamp = pd.Timestamp(timestamp)
        self._finish_exit_if_flat(timestamp, portfolio)
        if timestamp not in self.prepared.index or self.machine.state == StrategyState.COOLDOWN:
            return []
        row = self.prepared.loc[timestamp]
        required = ["close", "atr_14", "adx_14", "atr_ratio", "range_high", "range_low", "range_position", "range_width_atr"]
        if row[required].isna().any():
            return []
        settings = self.config["strategy"]["natural"]
        features = self.config["features"]
        event = self.events.check(
            [self.symbol], timestamp,
            earnings_before=int(self.config["events"]["earnings_before_trading_days"]),
            earnings_after=int(self.config["events"]["earnings_after_trading_days"]),
        )
        range_quality = (
            float(features["range_width_atr_min"]) <= float(row["range_width_atr"]) <= float(features["range_width_atr_max"])
            and float(row["atr_ratio"]) <= float(features["atr_expansion_max"])
            and (
                not bool(features.get("adx_filter_enabled", True))
                or float(row["adx_14"]) < float(features["range_adx_max"])
            )
        )
        safety_ok = not event.blocked and regime_allows_grid(str(row["market_regime"]))
        near_demand = (
            0.0 <= float(row["range_position"]) <= float(settings["lower_range_fraction"])
        )
        costs_ok = self._cost_gate(row, settings, portfolio.equity)
        liquidity_ok = (
            not bool(features.get("liquidity_gate_enabled", True))
            or float(row.get("dollar_volume_20", 0)) >= float(self.config["universe"]["min_average_daily_dollar_volume"])
        )
        sweep_cfg = self.config["strategy"].get("liquidity_sweep", {})
        sweep_mode = str(sweep_cfg.get("mode", "none"))
        sweep_ok = bool(row.get("bullish_sweep_reclaim", False))

        if self.machine.state == StrategyState.SCAN:
            if range_quality and safety_ok and liquidity_ok:
                self.machine.transition(timestamp, StrategyState.CANDIDATE, "tradable range detected")
            return []
        if self.machine.state == StrategyState.CANDIDATE:
            if not range_quality or not safety_ok:
                self.machine.transition(timestamp, StrategyState.SCAN, "range candidate invalidated")
            elif near_demand and costs_ok and (sweep_mode != "required" or sweep_ok):
                self.machine.transition(timestamp, StrategyState.ARMED, "price entered lower 35% of range")
            return []
        if self.machine.state == StrategyState.ARMED:
            if not near_demand or not safety_ok or (sweep_mode == "required" and not sweep_ok):
                self.machine.transition(timestamp, StrategyState.SCAN, "natural grid setup expired")
                return []
            stop_atr = self._stop_atr(settings)
            stop = float(row["range_low"]) - stop_atr * float(row["atr_14"])
            catastrophic_atr = settings.get("catastrophic_stop_atr")
            catastrophic_stop = (
                float(row["range_low"]) - float(catastrophic_atr) * float(row["atr_14"])
                if catastrophic_atr is not None else None
            )
            risk_stop = (
                catastrophic_stop
                if str(settings.get("stop_trigger_mode", "legacy_close_or_two_close")) == "close_confirmation"
                and catastrophic_stop is not None
                else stop
            )
            execution_factor = float(row.get("execution_factor", 1.0))
            self.campaign.group_id = f"{self.name}:{self.symbol}:{timestamp.isoformat()}"
            self.campaign.direction = 1
            self.campaign.entry_time = timestamp
            self.campaign.layer_notionals = self.risk_manager.price_grid_notionals(
                entry_price=float(row["close"]),
                stop_price=risk_stop,
                equity=portfolio.equity,
                layers=int(settings.get("grid_level_count", 4)),
            )
            if sweep_mode == "boost" and sweep_ok:
                boost = float(sweep_cfg.get("size_boost", 1.25))
                self.campaign.layer_notionals = [value * boost for value in self.campaign.layer_notionals]
            count = min(
                int(settings.get("grid_level_count", 4)),
                int(settings.get("max_grid_depth", settings.get("grid_level_count", 4))),
            )
            step_adjusted = float(settings["grid_step_atr"]) * float(row["atr_14"])
            entry_adjusted = float(row["close"])
            adjusted_levels = [entry_adjusted - layer * step_adjusted for layer in range(count)]
            adjusted_levels = [level for level in adjusted_levels if level >= float(row["range_low"])]
            self.campaign.grid_prices = [level * execution_factor for level in adjusted_levels]
            self.campaign.layer_notionals = self.campaign.layer_notionals[:len(adjusted_levels)]
            self.campaign.stop_price = stop * execution_factor
            self.campaign.catastrophic_stop_price = (
                catastrophic_stop * execution_factor if catastrophic_stop is not None else None
            )
            self.campaign.invalidation_price = float(row["range_low"]) * execution_factor
            self.campaign.layers = len(adjusted_levels)
            self.machine.transition(timestamp, StrategyState.GRID_ACTIVE, "predefined natural grid queued")
            orders = []
            tp_prices = [
                ((float(row["range_low"]) + float(row["range_high"])) / 2) * execution_factor,
                (float(row["range_high"]) - 0.5 * float(row["atr_14"])) * execution_factor,
                float(row["range_high"]) * execution_factor,
            ]
            for layer, (notional, level) in enumerate(zip(self.campaign.layer_notionals, self.campaign.grid_prices), start=1):
                orders.append(OrderIntent(
                    self.symbol,
                    Side.BUY,
                    notional,
                    f"natural grid layer {layer}",
                    self.name,
                    self.campaign.group_id,
                    metadata={
                        "direction": 1,
                        "grid_layer": layer,
                        "grid_level": level,
                        "adjusted_grid_level": entry_adjusted - (layer - 1) * step_adjusted,
                        "stop_price": self.campaign.stop_price,
                        "tp_prices": tp_prices,
                    },
                    order_type=OrderType.LIMIT,
                    requested_price=level,
                    time_in_force="GTC",
                ))
            return orders
        if self.machine.state in {StrategyState.GRID_ACTIVE, StrategyState.WARNING}:
            stop_variant = str(settings.get("stop_variant", "current"))
            stop_atr = self._stop_atr(settings)
            hard_stop = float(row["range_low"]) - stop_atr * float(row["atr_14"])
            closes_below = bool((self.prepared.loc[:timestamp, "close"].tail(2) < float(row["range_low"])).all())
            stop_mode = str(settings.get("stop_trigger_mode", "legacy_close_or_two_close"))
            if stop_mode == "intrabar":
                structure_invalid = False
            elif stop_mode == "close_confirmation":
                confirmation = max(1, int(settings.get("stop_confirmation_closes", 1)))
                recent = self.prepared.loc[:timestamp, "close"].tail(confirmation)
                structure_invalid = bool(
                    len(recent) == confirmation
                    and (recent < float(row["range_low"])).all()
                )
            else:
                structure_invalid = (
                    float(row["close"]) < hard_stop
                    if stop_variant == "structure_close"
                    else float(row["close"]) < hard_stop or closes_below
                )
            if (structure_invalid or float(row["atr_ratio"]) > float(settings["atr_kill_multiple"]) or not safety_ok):
                self.machine.transition(timestamp, StrategyState.KILL, "; ".join(event.reasons) or "natural grid invalidation")
                self.risk_manager.register_kill(self.symbol, timestamp)
                order = self._close_order(self.symbol, portfolio, "natural grid kill")
                return [order] if order else []
            if (
                self.campaign.entry_time is not None
                and len(pd.bdate_range(self.campaign.entry_time.normalize(), timestamp.normalize())) - 1
                >= int(settings["max_holding_days"])
            ):
                self.machine.transition(timestamp, StrategyState.GRID_EXITING, "natural grid time stop")
                order = self._close_order(self.symbol, portfolio, "natural grid time stop")
                return [order] if order else []
            history = self.prepared.loc[:timestamp].tail(20)
            assessment = self.breakout.assess(
                history, range_high=float(row["range_high"]), range_low=float(row["range_low"]), atr=float(row["atr_14"]),
            )
            if self.config["strategy"]["breakout"]["enabled"] and assessment.confirmed and assessment.direction > 0:
                self.machine.transition(timestamp, StrategyState.BREAKOUT_SETUP, "upward breakout confirmed", score=assessment.score)
                self.campaign.breakout_direction = 1
                self.campaign.breakout_level = float(row["range_high"])
                self.machine.transition(timestamp, StrategyState.BREAKOUT_ACTIVE, "grid converted to continuation", score=assessment.score)
                return []
            midpoint = (float(row["range_low"]) + float(row["range_high"])) / 2
            tp_mode = str(settings.get("tp_mode", "range_scaleout"))
            if tp_mode != "range_scaleout":
                position = portfolio.positions.get(self.symbol)
                if position is not None and not position.is_flat:
                    execution_factor = float(row.get("execution_factor", 1.0))
                    average_adjusted = float(position.average_price) / max(execution_factor, 1e-12)
                    multiplier = {"0.5_step": 0.5, "1.0_step": 1.0, "1.5_step": 1.5}.get(tp_mode)
                    target = midpoint if multiplier is None else average_adjusted + multiplier * float(settings["grid_step_atr"]) * float(row["atr_14"])
                    if float(row["close"]) >= target:
                        self.machine.transition(timestamp, StrategyState.GRID_EXITING, f"natural diagnostic {tp_mode} target")
                        order = self._close_order(self.symbol, portfolio, f"natural diagnostic {tp_mode} TP")
                        return [order] if order else []
                return []
            targets = [midpoint, float(row["range_high"]) - 0.5 * float(row["atr_14"]), float(row["range_high"])]
            if self.campaign.take_profit_stage < 3 and float(row["close"]) >= targets[self.campaign.take_profit_stage]:
                stage = self.campaign.take_profit_stage
                self.campaign.take_profit_stage += 1
                fraction = 1.0 if stage == 2 else 1 / (3 - stage)
                if stage == 2:
                    self.machine.transition(timestamp, StrategyState.GRID_EXITING, "natural grid target completed")
                order = self._close_order(self.symbol, portfolio, f"natural TP{stage + 1}", fraction)
                return [order] if order else []
        if self.machine.state == StrategyState.BREAKOUT_ACTIVE:
            level = self.campaign.breakout_level or float(row["range_high"])
            recent = self.prepared.loc[:timestamp].tail(20)
            failed = self.breakout.failed(recent, 1, level)
            trailing = recent["low"].shift(1).rolling(10, min_periods=3).min().iloc[-1]
            if failed or (pd.notna(trailing) and float(row["close"]) < float(trailing)) or not safety_ok:
                self.machine.transition(timestamp, StrategyState.GRID_EXITING, "breakout failed or trailing stop")
                order = self._close_order(self.symbol, portfolio, "breakout exit")
                return [order] if order else []
        return []
