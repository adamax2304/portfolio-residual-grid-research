from __future__ import annotations

import numpy as np
import pandas as pd

from residual_grid_research.data.alpha_vantage import core_session, indicator_prices
from residual_grid_research.data.events import EventBlock, EventCalendar
from residual_grid_research.features.regime import classify_regime, regime_allows_grid
from residual_grid_research.features.liquidity import liquidity_series
from residual_grid_research.features.statistics import mean_reversion_diagnostics, rolling_relationship
from residual_grid_research.features.technical import add_technical_features
from residual_grid_research.models import OrderIntent, Side, StrategyState
from .base import BaseStrategy, PortfolioView


class StockPairGridStrategy(BaseStrategy):
    """Beta-hedged stock-pair grid; short borrow remains a configured placeholder."""

    name = "stock_pair_grid"

    def __init__(self, config: dict, asset_a: str, asset_b: str, *, events: EventCalendar | None = None) -> None:
        super().__init__(config, asset_a)
        self.asset_a = asset_a.upper()
        self.asset_b = asset_b.upper()
        self.events = events or EventCalendar()
        self.diagnostics: dict = {}
        self.run_name = f"stock_pair_grid:{self.asset_a}/{self.asset_b}"

    @property
    def required_symbols(self) -> list[str]:
        return [self.asset_a, self.asset_b, "SPY"]

    def prepare(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        cfg = self.config["features"]
        buffer_minutes = int(self.config["data"]["no_trade_window_minutes"])
        a_data = indicator_prices(core_session(data[self.asset_a], buffer_minutes))
        b_data = indicator_prices(core_session(data[self.asset_b], buffer_minutes))
        relation = rolling_relationship(
            a_data, b_data, beta_window=int(cfg["beta_window"]),
            z_window=int(cfg["z_window"]), correlation_windows=cfg["correlation_windows"],
        )
        market = indicator_prices(core_session(data.get("SPY", data[self.asset_b]), buffer_minutes))
        relation["market_regime"] = classify_regime(
            market, market_adx_max=float(cfg["market_adx_max"]),
            atr_expansion_max=float(cfg["market_atr_expansion_max"]),
        ).reindex(relation.index)
        for symbol, suffix in ((self.asset_a, "a"), (self.asset_b, "b")):
            source = a_data if symbol == self.asset_a else b_data
            relation[f"dollar_volume_{suffix}"] = liquidity_series(source, self.config).reindex(relation.index)
        a_technical = add_technical_features(a_data)
        relation["a_adx_14"] = a_technical["adx_14"].reindex(relation.index)
        relation["a_volume_ratio"] = a_technical["volume_ratio"].reindex(relation.index)
        relation["a_true_range_expansion"] = a_technical["true_range_expansion"].reindex(relation.index)
        self.prepared = relation
        settings = self.config["strategy"]["pairs"]
        self.diagnostics = mean_reversion_diagnostics(
            relation,
            entry_z=float(settings["entry_z"]),
            kill_z=float(settings["kill_z"]),
            include_adf=False,
        )
        return relation

    def pending_order_valid(
        self, timestamp: pd.Timestamp, intent: OrderIntent, portfolio: PortfolioView
    ) -> tuple[bool, str]:
        if intent.reduce_only:
            return True, "exit order"
        if self.machine.state not in {
            StrategyState.GRID_ACTIVE,
            StrategyState.WARNING,
            StrategyState.BREAKOUT_ACTIVE,
        }:
            return False, f"entry order invalid in {self.machine.state.value}"
        direction = int(intent.metadata.get("direction", self.campaign.direction or 1))
        event = self._event_check(timestamp, direction)
        return (not event.blocked, "; ".join(event.reasons) or "event safe")

    def _event_check(
        self, timestamp: pd.Timestamp, direction: int, *, existing_position: bool = False
    ) -> EventBlock:
        dividend_buffer = int(self.config["events"]["ex_dividend_short_buffer_days"])
        if existing_position:
            dividend_buffer += 2
        kwargs = dict(
            earnings_before=int(self.config["events"]["earnings_before_trading_days"]),
            earnings_after=int(self.config["events"]["earnings_after_trading_days"]),
            ex_dividend_buffer=dividend_buffer,
        )
        base = self.events.check([self.asset_a, self.asset_b], timestamp, is_short=False, **kwargs)
        short_symbol = self.asset_b if direction > 0 else self.asset_a
        short = self.events.check([short_symbol], timestamp, is_short=True, **kwargs)
        reasons = list(dict.fromkeys([*base.reasons, *short.reasons]))
        return EventBlock(bool(reasons), reasons)

    def _orders(self, direction: int, notional: float, beta: float, reason: str) -> list[OrderIntent]:
        # direction > 0 means long spread A / short B; direction < 0 is the reverse.
        return [
            OrderIntent(
                self.asset_a, Side.BUY if direction > 0 else Side.SELL, notional,
                reason, self.name, self.campaign.group_id,
                metadata={"direction": direction, "beta": beta},
            ),
            OrderIntent(
                self.asset_b, Side.SELL if direction > 0 else Side.BUY,
                notional * max(0.1, abs(beta)), f"hedge: {reason}", self.name,
                self.campaign.group_id,
                metadata={"direction": direction, "beta": beta},
            ),
        ]

    def _close_all(self, portfolio: PortfolioView, reason: str, fraction: float = 1.0) -> list[OrderIntent]:
        return [order for symbol in (self.asset_a, self.asset_b) if (order := self._close_order(symbol, portfolio, reason, fraction))]

    def exposure_snapshot(self, timestamp: pd.Timestamp, portfolio: PortfolioView) -> dict[str, float]:
        if timestamp not in self.prepared.index or portfolio.equity <= 0:
            return super().exposure_snapshot(timestamp, portfolio)
        beta = float(self.prepared.at[timestamp, "beta"])
        a = portfolio.positions.get(self.asset_a)
        b = portfolio.positions.get(self.asset_b)
        a_mv = a.quantity * portfolio.prices.get(self.asset_a, a.average_price) if a else 0.0
        b_mv = b.quantity * portfolio.prices.get(self.asset_b, b.average_price) if b else 0.0
        return {"net_beta_exposure": float((a_mv * beta + b_mv) / portfolio.equity)}

    def on_bar(self, timestamp: pd.Timestamp, portfolio: PortfolioView) -> list[OrderIntent]:
        timestamp = pd.Timestamp(timestamp)
        self._finish_exit_if_flat(timestamp, portfolio)
        if timestamp not in self.prepared.index or self.machine.state == StrategyState.COOLDOWN:
            return []
        row = self.prepared.loc[timestamp]
        required = ["z", "corr_60", "corr_90", "beta", "beta_stability", "residual_std"]
        if row[required].isna().any():
            return []
        settings = self.config["strategy"]["pairs"]
        features = self.config["features"]
        z = float(row["z"])
        direction = 1 if z <= -float(settings["entry_z"]) else -1 if z >= float(settings["entry_z"]) else 0
        relation_ok = (
            float(row["corr_60"]) >= float(features["stock_pair_corr_min"])
            and float(row["corr_90"]) >= float(features["stock_pair_corr_90_min"])
            and float(row["beta_stability"]) <= float(features["beta_stability_max"])
        )
        event_direction = self.campaign.direction if self.machine.state in {
            StrategyState.GRID_ACTIVE,
            StrategyState.WARNING,
            StrategyState.BREAKOUT_SETUP,
            StrategyState.BREAKOUT_ACTIVE,
        } else direction or 1
        active_state = self.machine.state in {
            StrategyState.GRID_ACTIVE,
            StrategyState.WARNING,
            StrategyState.BREAKOUT_SETUP,
            StrategyState.BREAKOUT_ACTIVE,
        }
        event = self._event_check(timestamp, event_direction, existing_position=active_state)
        safety_ok = not event.blocked and regime_allows_grid(str(row["market_regime"]))
        if bool(features.get("adx_filter_enabled", False)):
            safety_ok = safety_ok and float(row.get("a_adx_14", float("inf"))) < float(features["range_adx_max"])
        liquid = (
            not bool(features.get("liquidity_gate_enabled", True))
            or min(float(row["dollar_volume_a"]), float(row["dollar_volume_b"]))
            >= float(self.config["universe"]["min_average_daily_dollar_volume"])
        )
        stationarity_enabled = bool(settings.get("stationarity_proxy_enabled", True))
        opportunity = (
            direction != 0
            and liquid
            and (not stationarity_enabled or self.diagnostics.get("half_life_bars") is not None)
        )

        if self.machine.state == StrategyState.BREAKOUT_SETUP:
            flat = all(portfolio.positions.get(symbol) is None or portfolio.positions[symbol].is_flat for symbol in (self.asset_a, self.asset_b))
            if flat and safety_ok:
                breakout_direction = self.campaign.breakout_direction
                self.campaign.group_id = f"{self.name}:breakout:{self.asset_a}-{self.asset_b}:{timestamp.isoformat()}"
                self.campaign.direction = breakout_direction
                self.campaign.entry_time = timestamp
                self.campaign.breakout_peak = abs(z)
                self.machine.transition(timestamp, StrategyState.BREAKOUT_ACTIVE, "pair breakout continuation entered")
                notional = self.campaign.layer_notionals[0] if self.campaign.layer_notionals else portfolio.equity * 0.10
                return self._orders(breakout_direction, notional, float(row["beta"]), "pair breakout continuation")
            if not safety_ok:
                self.machine.transition(timestamp, StrategyState.KILL, "pair breakout safety gate failed")
            return []
        if self.machine.state == StrategyState.BREAKOUT_ACTIVE:
            progress = z * self.campaign.breakout_direction
            self.campaign.breakout_peak = max(self.campaign.breakout_peak, progress)
            failed = progress < float(settings["grid_levels"][-1])
            trailing = progress <= self.campaign.breakout_peak - 0.6
            timed_out = self.campaign.entry_time is not None and len(pd.bdate_range(self.campaign.entry_time.normalize(), timestamp.normalize())) - 1 >= int(settings["max_holding_days"])
            if failed or trailing or timed_out or not safety_ok:
                self.machine.transition(timestamp, StrategyState.GRID_EXITING, "pair breakout exit")
                return self._close_all(portfolio, "pair breakout exit")
            return []

        if self.machine.state == StrategyState.SCAN:
            if relation_ok and safety_ok:
                self.machine.transition(timestamp, StrategyState.CANDIDATE, "pair relationship gates passed")
            return []
        if self.machine.state == StrategyState.CANDIDATE:
            if not relation_ok or not safety_ok:
                self.machine.transition(timestamp, StrategyState.SCAN, "pair candidate invalidated")
            elif opportunity:
                self.machine.transition(timestamp, StrategyState.ARMED, "pair z opportunity armed")
            return []
        if self.machine.state == StrategyState.ARMED:
            if not opportunity or not safety_ok:
                self.machine.transition(timestamp, StrategyState.SCAN, "pair setup expired")
                return []
            self.campaign.group_id = f"{self.name}:{self.asset_a}-{self.asset_b}:{timestamp.isoformat()}"
            self.campaign.direction = direction
            self.campaign.entry_time = timestamp
            self.campaign.layer_notionals = self.risk_manager.relationship_grid_notionals(
                residual_std=float(row["residual_std"]), grid_levels=list(map(float, settings["grid_levels"])),
                kill_z=float(settings["kill_z"]), equity=portfolio.equity,
            )
            self.campaign.layers = 1
            self.machine.transition(timestamp, StrategyState.GRID_ACTIVE, "pair layer 1 queued")
            return self._orders(direction, self.campaign.layer_notionals[0], float(row["beta"]), "pair grid layer 1")
        if self.machine.state in {StrategyState.GRID_ACTIVE, StrategyState.WARNING}:
            adverse_z = -z if self.campaign.direction > 0 else z
            if not safety_ok or not relation_ok or float(row["corr_60"]) < float(features["correlation_kill"]):
                self.machine.transition(timestamp, StrategyState.KILL, "; ".join(event.reasons) or "pair relationship invalidated")
                self.risk_manager.register_kill(self.asset_a, timestamp)
                return self._close_all(portfolio, "pair kill")
            if adverse_z >= float(settings["kill_z"]):
                self.machine.transition(timestamp, StrategyState.KILL, "pair kill z reached")
                self.risk_manager.register_kill(self.asset_a, timestamp)
                return self._close_all(portfolio, "pair kill z")
            breakout_cfg = self.config["strategy"]["breakout"]
            breakout_mode = str(breakout_cfg.get("confirmation_mode", "closes"))
            breakout_closes = 1 if breakout_mode == "one_close" else 2 if breakout_mode in {"two_closes", "retest"} else int(breakout_cfg["confirmation_closes"])
            recent_z = self.prepared.loc[:timestamp, "z"].tail(breakout_closes)
            retest_ok = breakout_mode != "retest" or (
                len(recent_z) == 2
                and abs(float(recent_z.iloc[-1])) <= abs(float(recent_z.iloc[-2]))
            )
            participation_ok = (
                float(row.get("a_volume_ratio", 0.0)) >= float(breakout_cfg["volume_ratio"])
                or float(row.get("a_true_range_expansion", 0.0)) >= 1.25
            )
            break_distance_ok = abs(z) >= (
                float(settings["grid_levels"][-1]) + float(breakout_cfg["atr_buffer"])
            )
            breakout_score = (
                (30.0 if break_distance_ok else 0.0)
                + (25.0 if len(recent_z) == breakout_closes else 0.0)
                + (20.0 if participation_ok else 0.0)
                + (15.0 if relation_ok else 0.0)
                + (10.0 if retest_ok else 0.0)
            )
            breakout_confirmed = (
                bool(breakout_cfg["enabled"])
                and len(recent_z) == breakout_closes
                and bool((recent_z.abs() >= float(settings["grid_levels"][-1])).all())
                and bool((np.sign(recent_z) == np.sign(z)).all())
                and retest_ok
                and participation_ok
                and break_distance_ok
                and breakout_score >= float(breakout_cfg["minimum_score"])
                and relation_ok
            )
            if breakout_confirmed:
                self.machine.transition(
                    timestamp, StrategyState.BREAKOUT_SETUP,
                    "persistent pair breakout confirmed with participation",
                    score=breakout_score,
                )
                self.campaign.breakout_direction = 1 if z > 0 else -1
                self.campaign.breakout_level = float(settings["grid_levels"][-1])
                return self._close_all(portfolio, "convert pair grid to breakout")
            if self.campaign.entry_time is not None and len(pd.bdate_range(self.campaign.entry_time.normalize(), timestamp.normalize())) - 1 >= int(settings["max_holding_days"]):
                self.machine.transition(timestamp, StrategyState.GRID_EXITING, "pair time stop")
                return self._close_all(portfolio, "pair time stop")
            if self.campaign.layers < len(settings["grid_levels"]) and adverse_z >= float(settings["grid_levels"][self.campaign.layers]):
                layer = self.campaign.layers
                self.campaign.layers += 1
                return self._orders(self.campaign.direction, self.campaign.layer_notionals[layer], float(row["beta"]), f"pair grid layer {layer + 1}")
            simple_exit_z = settings.get("simple_exit_z")
            progress = z if self.campaign.direction > 0 else -z
            if simple_exit_z is not None and progress >= -float(simple_exit_z):
                self.machine.transition(timestamp, StrategyState.GRID_EXITING, "pair simple spread exit")
                return self._close_all(portfolio, f"pair simple z={float(simple_exit_z):g} exit")
            targets = list(map(float, settings["take_profit_z"]))
            target_values = [-targets[0], -targets[1], -targets[2]]
            if self.campaign.take_profit_stage < 3 and progress >= target_values[self.campaign.take_profit_stage]:
                stage = self.campaign.take_profit_stage
                self.campaign.take_profit_stage += 1
                fraction = 1.0 if stage == 2 else 1 / (3 - stage)
                if stage == 2:
                    self.machine.transition(timestamp, StrategyState.GRID_EXITING, "pair mean reversion completed")
                return self._close_all(portfolio, f"pair TP{stage + 1}", fraction)
            if adverse_z >= float(settings["grid_levels"][-1]) and self.machine.state == StrategyState.GRID_ACTIVE:
                self.machine.transition(timestamp, StrategyState.WARNING, "fully loaded pair under pressure")
            elif adverse_z < float(settings["grid_levels"][-2]) and self.machine.state == StrategyState.WARNING:
                self.machine.transition(timestamp, StrategyState.GRID_ACTIVE, "pair pressure eased")
        return []
