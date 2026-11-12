from __future__ import annotations

import math

import numpy as np
import pandas as pd

from residual_grid_research.data.alpha_vantage import core_session, indicator_prices
from residual_grid_research.data.events import EventBlock, EventCalendar
from residual_grid_research.features.regime import classify_regime, regime_allows_grid
from residual_grid_research.features.liquidity import liquidity_series
from residual_grid_research.features.scoring import score_candidate
from residual_grid_research.features.statistics import mean_reversion_diagnostics, rolling_relationship
from residual_grid_research.features.technical import add_technical_features
from residual_grid_research.models import OrderIntent, Side, StrategyState
from .base import BaseStrategy, PortfolioView
from .breakout import BreakoutEngine


class ResidualGridStrategy(BaseStrategy):
    """Stock-to-ETF residual grid with optional short/hedge and breakout conversion."""

    name = "residual_grid"

    def __init__(
        self,
        config: dict,
        stock: str,
        etf: str,
        *,
        events: EventCalendar | None = None,
        allow_short_stock: bool | None = None,
        hedge_with_etf: bool | None = None,
    ) -> None:
        super().__init__(config, stock)
        self.stock = stock.upper()
        self.etf = etf.upper()
        settings = config["strategy"]["residual"]
        self.allow_short_stock = settings["allow_short_stock"] if allow_short_stock is None else allow_short_stock
        self.hedge_with_etf = settings["hedge_with_etf"] if hedge_with_etf is None else hedge_with_etf
        self.events = events or EventCalendar()
        self.breakout = BreakoutEngine(config)
        self.diagnostics: dict = {}
        self.run_name = f"residual_grid:{self.stock}/{self.etf}"

    @property
    def required_symbols(self) -> list[str]:
        symbols = [self.stock, self.etf]
        if "SPY" not in symbols:
            symbols.append("SPY")
        return symbols

    def prepare(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        if self.stock not in data or self.etf not in data:
            raise KeyError(f"Data must contain {self.stock} and {self.etf}")
        cfg = self.config["features"]
        buffer_minutes = int(self.config["data"]["no_trade_window_minutes"])
        stock_data = indicator_prices(core_session(data[self.stock], buffer_minutes))
        etf_data = indicator_prices(core_session(data[self.etf], buffer_minutes))
        relation = rolling_relationship(
            stock_data,
            etf_data,
            beta_window=int(cfg["beta_window"]),
            z_window=int(cfg["z_window"]),
            correlation_windows=cfg["correlation_windows"],
        )
        technical = add_technical_features(stock_data)
        columns = [
            "open", "high", "low", "close", "volume", "atr_14", "adx_14", "atr_ratio",
            "range_high", "range_low", "range_width_atr", "range_position", "volume_ratio",
            "bullish_sweep_reclaim", "bearish_sweep_reclaim", "true_range_expansion",
        ]
        relation = relation.join(technical[[c for c in columns if c in technical]].add_prefix("stock_"), how="inner")
        benchmark = indicator_prices(core_session(data.get("SPY", data[self.etf]), buffer_minutes))
        relation["market_regime"] = classify_regime(
            benchmark,
            market_adx_max=float(cfg["market_adx_max"]),
            atr_expansion_max=float(cfg["market_atr_expansion_max"]),
        ).reindex(relation.index)
        relation["dollar_volume_20"] = liquidity_series(stock_data, self.config).reindex(relation.index)
        self.prepared = relation
        self.diagnostics = mean_reversion_diagnostics(
            relation,
            entry_z=float(self.config["strategy"]["residual"]["entry_z"]),
            kill_z=float(self.config["strategy"]["residual"]["kill_z"]),
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
            # A close-generated exit cannot fill before the next session. Add a
            # second lead day to remain conservative around exchange holidays,
            # which numpy's weekday calendar does not know about.
            dividend_buffer += 2
        kwargs = dict(
            earnings_before=int(self.config["events"]["earnings_before_trading_days"]),
            earnings_after=int(self.config["events"]["earnings_after_trading_days"]),
            ex_dividend_buffer=dividend_buffer,
        )
        base = self.events.check([self.stock, self.etf], timestamp, is_short=False, **kwargs)
        short_symbol = self.stock if direction < 0 else self.etf if direction > 0 and self.hedge_with_etf else None
        short = self.events.check([short_symbol], timestamp, is_short=True, **kwargs) if short_symbol else EventBlock(False, [])
        reasons = list(dict.fromkeys([*base.reasons, *short.reasons]))
        return EventBlock(bool(reasons), reasons)

    def _gate_and_score(
        self, timestamp: pd.Timestamp, row: pd.Series, direction: int, *, existing_position: bool = False
    ):
        features = self.config["features"]
        event = self._event_check(timestamp, direction, existing_position=existing_position)
        near_structure = bool(row["stock_range_position"] <= 0.40) if direction > 0 else bool(row["stock_range_position"] >= 0.60)
        liquidity_ok = (
            not bool(features.get("liquidity_gate_enabled", True))
            or float(row.get("dollar_volume_20", 0)) >= float(self.config["universe"]["min_average_daily_dollar_volume"])
        )
        residual_move = abs(float(row.get("residual_std", 0))) * float(row["stock_close"])
        cost_floor = float(row["stock_close"]) * (
            float(self.config["costs"]["spread_bps"]) + float(self.config["costs"]["slippage_bps"])
        ) / 10000 * float(self.config["costs"]["costs_safety_multiple"])
        score = score_candidate(
            correlation=float(row["corr_60"]),
            beta_stability=float(row["beta_stability"]),
            half_life_bars=self.diagnostics.get("half_life_bars"),
            crossings_per_year=float(self.diagnostics.get("crossings_per_year") or 0),
            z_abs=abs(float(row["z"])),
            near_structure=near_structure,
            event_safe=not event.blocked,
            liquidity_ok=liquidity_ok,
            costs_ok=residual_move > cost_floor,
            regime_ok=regime_allows_grid(str(row["market_regime"])),
            threshold=float(features["candidate_score_min"]),
        )
        corr_min = float(features["stock_etf_corr_min"] if direction > 0 else features["stock_etf_short_corr_min"])
        relationship_ok = (
            float(row["corr_60"]) >= corr_min
            and float(row["beta"]) > 0
            and float(row["beta_stability"]) <= float(features["beta_stability_max"])
        )
        hard_safe = not event.blocked and regime_allows_grid(str(row["market_regime"]))
        if bool(features.get("adx_filter_enabled", False)):
            hard_safe = hard_safe and float(row.get("stock_adx_14", np.inf)) < float(features["range_adx_max"])
        sweep_cfg = self.config["strategy"].get("liquidity_sweep", {})
        sweep_mode = str(sweep_cfg.get("mode", "none"))
        sweep_ok = bool(
            row.get("stock_bullish_sweep_reclaim", False)
            if direction > 0 else row.get("stock_bearish_sweep_reclaim", False)
        )
        if sweep_mode == "required":
            relationship_ok = relationship_ok and sweep_ok
        return relationship_ok, hard_safe, score, event.reasons

    def _campaign_orders(self, direction: int, notional: float, row: pd.Series, reason: str) -> list[OrderIntent]:
        orders = [OrderIntent(
            self.stock, Side.BUY if direction > 0 else Side.SELL, notional, reason,
            self.name, self.campaign.group_id,
            metadata={"direction": direction, "z": float(row["z"])},
        )]
        if self.hedge_with_etf:
            hedge_mode = str(self.config["strategy"]["residual"].get("hedge_ratio_mode", "beta_neutral"))
            hedge_notional = notional if hedge_mode == "dollar_neutral" else notional * max(0.0, float(row["beta"]))
            orders.append(OrderIntent(
                self.etf, Side.SELL if direction > 0 else Side.BUY, hedge_notional,
                f"beta hedge: {reason}", self.name, self.campaign.group_id,
                metadata={"beta": float(row["beta"]), "direction": direction},
            ))
        return orders

    def _close_all(self, portfolio: PortfolioView, reason: str, fraction: float = 1.0) -> list[OrderIntent]:
        return [order for symbol in (self.stock, self.etf) if (order := self._close_order(symbol, portfolio, reason, fraction))]

    def exposure_snapshot(self, timestamp: pd.Timestamp, portfolio: PortfolioView) -> dict[str, float]:
        if timestamp not in self.prepared.index or portfolio.equity <= 0:
            return super().exposure_snapshot(timestamp, portfolio)
        beta = float(self.prepared.at[timestamp, "beta"])
        stock = portfolio.positions.get(self.stock)
        etf = portfolio.positions.get(self.etf)
        stock_mv = stock.quantity * portfolio.prices.get(self.stock, stock.average_price) if stock else 0.0
        etf_mv = etf.quantity * portfolio.prices.get(self.etf, etf.average_price) if etf else 0.0
        return {"net_beta_exposure": float((stock_mv * beta + etf_mv) / portfolio.equity)}

    def on_bar(self, timestamp: pd.Timestamp, portfolio: PortfolioView) -> list[OrderIntent]:
        timestamp = pd.Timestamp(timestamp)
        self._finish_exit_if_flat(timestamp, portfolio)
        if timestamp not in self.prepared.index or self.machine.state == StrategyState.COOLDOWN:
            return []
        row = self.prepared.loc[timestamp]
        required = ["z", "corr_60", "beta", "beta_stability", "residual_std", "stock_close"]
        if row[required].isna().any():
            return []
        settings = self.config["strategy"]["residual"]
        z = float(row["z"])
        direction = 1 if z <= -float(settings["entry_z"]) else -1 if z >= float(settings["entry_z"]) else 0
        if direction < 0 and not self.allow_short_stock:
            direction = 0
        active_direction = self.campaign.direction if self.machine.state in {
            StrategyState.GRID_ACTIVE,
            StrategyState.WARNING,
            StrategyState.BREAKOUT_SETUP,
            StrategyState.BREAKOUT_ACTIVE,
        } else direction
        active_state = self.machine.state in {
            StrategyState.GRID_ACTIVE,
            StrategyState.WARNING,
            StrategyState.BREAKOUT_SETUP,
            StrategyState.BREAKOUT_ACTIVE,
        }
        relationship_ok, hard_safe, score, event_reasons = self._gate_and_score(
            timestamp, row, active_direction or 1, existing_position=active_state
        )

        if self.machine.state == StrategyState.BREAKOUT_SETUP:
            flat = all(portfolio.positions.get(symbol) is None or portfolio.positions[symbol].is_flat for symbol in (self.stock, self.etf))
            if flat and hard_safe:
                breakout_direction = self.campaign.breakout_direction
                self.campaign.group_id = f"{self.name}:breakout:{self.stock}:{timestamp.isoformat()}"
                self.campaign.direction = breakout_direction
                self.campaign.entry_time = timestamp
                self.campaign.breakout_peak = abs(z)
                self.machine.transition(timestamp, StrategyState.BREAKOUT_ACTIVE, "residual breakout continuation entered")
                notional = self.campaign.layer_notionals[0] if self.campaign.layer_notionals else portfolio.equity * 0.10
                return self._campaign_orders(breakout_direction, notional, row, "residual breakout continuation")
            if not hard_safe:
                self.machine.transition(timestamp, StrategyState.KILL, "breakout safety gate failed")
            return []
        if self.machine.state == StrategyState.BREAKOUT_ACTIVE:
            progress = z * self.campaign.breakout_direction
            self.campaign.breakout_peak = max(self.campaign.breakout_peak, progress)
            failed = progress < float(settings["grid_levels"][-1])
            trailing = progress <= self.campaign.breakout_peak - 0.6
            timed_out = self.campaign.entry_time is not None and len(pd.bdate_range(self.campaign.entry_time.normalize(), timestamp.normalize())) - 1 >= int(settings["max_holding_days"])
            if failed or trailing or timed_out or not hard_safe:
                self.machine.transition(timestamp, StrategyState.GRID_EXITING, "residual breakout exit")
                return self._close_all(portfolio, "residual breakout exit")
            return []

        if self.machine.state == StrategyState.SCAN:
            if relationship_ok and hard_safe:
                self.machine.transition(timestamp, StrategyState.CANDIDATE, "relationship and safety gates passed", score=score.total)
            return []
        if self.machine.state == StrategyState.CANDIDATE:
            if not relationship_ok or not hard_safe:
                self.machine.transition(timestamp, StrategyState.SCAN, "candidate gate failed")
            elif direction and score.passed and not self.risk_manager.kill_cap_reached(self.stock, timestamp):
                self.machine.transition(timestamp, StrategyState.ARMED, "entry zone and candidate score confirmed", score=score.total)
            return []
        if self.machine.state == StrategyState.ARMED:
            if not direction or not score.passed or not hard_safe:
                self.machine.transition(timestamp, StrategyState.SCAN, "armed setup expired")
                return []
            self.campaign.group_id = f"{self.name}:{self.stock}:{timestamp.isoformat()}"
            self.campaign.direction = direction
            self.campaign.entry_time = timestamp
            self.campaign.layer_notionals = self.risk_manager.relationship_grid_notionals(
                residual_std=float(row["residual_std"]),
                grid_levels=[float(v) for v in settings["grid_levels"]],
                kill_z=float(settings["kill_z"]),
                equity=portfolio.equity,
            )
            sweep_cfg = self.config["strategy"].get("liquidity_sweep", {})
            direction_sweep = bool(
                row.get("stock_bullish_sweep_reclaim", False)
                if direction > 0 else row.get("stock_bearish_sweep_reclaim", False)
            )
            if str(sweep_cfg.get("mode", "none")) == "boost" and direction_sweep:
                boost = float(sweep_cfg.get("size_boost", 1.25))
                self.campaign.layer_notionals = [value * boost for value in self.campaign.layer_notionals]
            self.campaign.layers = 1
            self.machine.transition(timestamp, StrategyState.GRID_ACTIVE, "first residual grid layer queued", score=score.total)
            return self._campaign_orders(direction, self.campaign.layer_notionals[0], row, "residual grid layer 1")

        if self.machine.state in {StrategyState.GRID_ACTIVE, StrategyState.WARNING}:
            adverse_z = -z if self.campaign.direction > 0 else z
            if not hard_safe or event_reasons or float(row["corr_60"]) < float(self.config["features"]["correlation_kill"]):
                self.machine.transition(timestamp, StrategyState.KILL, "; ".join(event_reasons) or "relationship/regime invalidation")
                self.risk_manager.register_kill(self.stock, timestamp)
                return self._close_all(portfolio, "residual kill")
            if adverse_z >= float(settings["kill_z"]):
                self.machine.transition(timestamp, StrategyState.KILL, "residual kill z reached")
                self.risk_manager.register_kill(self.stock, timestamp)
                return self._close_all(portfolio, "residual kill z")
            breakout_cfg = self.config["strategy"]["breakout"]
            breakout_mode = str(breakout_cfg.get("confirmation_mode", "closes"))
            breakout_closes = 1 if breakout_mode == "one_close" else 2 if breakout_mode in {"two_closes", "retest"} else int(breakout_cfg["confirmation_closes"])
            recent_z = self.prepared.loc[:timestamp, "z"].tail(breakout_closes)
            retest_ok = breakout_mode != "retest" or (
                len(recent_z) == 2
                and abs(float(recent_z.iloc[-1])) <= abs(float(recent_z.iloc[-2]))
            )
            participation_ok = (
                float(row.get("stock_volume_ratio", 0.0)) >= float(breakout_cfg["volume_ratio"])
                or float(row.get("stock_true_range_expansion", 0.0)) >= 1.25
            )
            break_distance_ok = abs(z) >= (
                float(settings["grid_levels"][-1]) + float(breakout_cfg["atr_buffer"])
            )
            breakout_score = (
                (30.0 if break_distance_ok else 0.0)
                + (25.0 if len(recent_z) == breakout_closes else 0.0)
                + (20.0 if participation_ok else 0.0)
                + (15.0 if float(row["corr_60"]) >= float(self.config["features"]["stock_etf_corr_min"]) else 0.0)
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
                and float(row["corr_60"]) >= float(self.config["features"]["stock_etf_corr_min"])
            )
            if breakout_confirmed:
                self.machine.transition(
                    timestamp, StrategyState.BREAKOUT_SETUP,
                    "persistent residual breakout confirmed with participation",
                    score=breakout_score,
                )
                self.campaign.breakout_direction = 1 if z > 0 else -1
                self.campaign.breakout_level = float(settings["grid_levels"][-1])
                return self._close_all(portfolio, "convert residual grid to breakout")
            if self.campaign.entry_time is not None and len(pd.bdate_range(self.campaign.entry_time.normalize(), timestamp.normalize())) - 1 >= int(settings["max_holding_days"]):
                self.machine.transition(timestamp, StrategyState.GRID_EXITING, "time stop")
                return self._close_all(portfolio, "residual time stop")
            while self.campaign.layers < len(settings["grid_levels"]) and adverse_z >= float(settings["grid_levels"][self.campaign.layers]):
                layer = self.campaign.layers
                self.campaign.layers += 1
                if layer == 3 and not bool(row["stock_range_position"] <= 0.25 if self.campaign.direction > 0 else row["stock_range_position"] >= 0.75):
                    break
                return self._campaign_orders(self.campaign.direction, self.campaign.layer_notionals[layer], row, f"residual grid layer {layer + 1}")
            targets = [float(v) for v in settings["take_profit_z"]]
            progress = z if self.campaign.direction > 0 else -z
            target_values = [-targets[0], -targets[1], -targets[2]]
            if self.campaign.take_profit_stage < 3 and progress >= target_values[self.campaign.take_profit_stage]:
                stage = self.campaign.take_profit_stage
                self.campaign.take_profit_stage += 1
                fraction = 1.0 if stage == 2 else (1 / (3 - stage))
                if stage == 2:
                    self.machine.transition(timestamp, StrategyState.GRID_EXITING, "residual mean reversion completed")
                return self._close_all(portfolio, f"residual TP{stage + 1}", fraction)
            if adverse_z >= float(settings["grid_levels"][-1]) and self.machine.state == StrategyState.GRID_ACTIVE:
                self.machine.transition(timestamp, StrategyState.WARNING, "fully loaded grid under pressure")
            elif adverse_z < float(settings["grid_levels"][-2]) and self.machine.state == StrategyState.WARNING:
                self.machine.transition(timestamp, StrategyState.GRID_ACTIVE, "pressure eased")
        return []
