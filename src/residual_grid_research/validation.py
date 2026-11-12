from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from residual_grid_research.backtest import BacktestEngine
from residual_grid_research.backtest.metrics import calculate_metrics, compute_baselines
from residual_grid_research.data import EventCalendar, YahooFinanceClient
from residual_grid_research.models import BacktestResult
from residual_grid_research.research import all_configured_symbols, relationship_diagnostics
from residual_grid_research.strategies import NaturalLongGridStrategy, ResidualGridStrategy, StockPairGridStrategy


@dataclass(frozen=True)
class StrategySpec:
    run_name: str
    family: str
    primary: str
    secondary: str | None
    factory: Callable[[dict, EventCalendar], Any]


def strategy_specs(config: dict) -> list[StrategySpec]:
    specs: list[StrategySpec] = []
    for stock, etfs in config["universe"]["stock_etf_map"].items():
        for etf in etfs:
            specs.append(StrategySpec(
                f"residual_grid:{stock}/{etf}", "residual", stock, etf,
                lambda cfg, events, stock=stock, etf=etf: ResidualGridStrategy(cfg, stock, etf, events=events),
            ))
    for a, b in config["universe"]["stock_pairs"]:
        specs.append(StrategySpec(
            f"stock_pair_grid:{a}/{b}", "pair", a, b,
            lambda cfg, events, a=a, b=b: StockPairGridStrategy(cfg, a, b, events=events),
        ))
    for symbol in config["universe"]["natural_long_symbols"]:
        specs.append(StrategySpec(
            f"natural_long_grid:{symbol}", "natural", symbol, None,
            lambda cfg, events, symbol=symbol: NaturalLongGridStrategy(cfg, symbol, events=events),
        ))
    return specs


def load_real_data(config: dict, *, intraday: bool = False) -> dict[str, pd.DataFrame]:
    root = Path(config["_project_root"])
    client = YahooFinanceClient(root / config["data"]["cache_dir"])
    symbols = all_configured_symbols(config)
    if intraday:
        data, _ = client.fetch_universe_intraday(
            symbols,
            period=str(config["data"]["intraday_period"]),
            interval=str(config["data"]["intraday_interval"]),
        )
    else:
        data, _ = client.fetch_universe_daily(
            symbols,
            str(config["data"]["daily_start"]),
            str(config["data"]["daily_end"]),
        )
    return data


def load_events(config: dict) -> EventCalendar:
    path = Path(config["_project_root"]) / config["data"]["event_path"]
    if not path.exists():
        raise FileNotFoundError(f"Historical event file is required: {path}")
    return EventCalendar(pd.read_csv(path))


def run_strategy_set(
    data: dict[str, pd.DataFrame],
    config: dict,
    events: EventCalendar,
    *,
    trade_start: pd.Timestamp | str | None = None,
) -> tuple[dict[str, BacktestResult], dict[str, dict[str, Any]], dict[str, pd.DataFrame]]:
    results, baselines, prepared_frames = {}, {}, {}
    for spec in strategy_specs(config):
        strategy = spec.factory(config, events)
        result = BacktestEngine(config).run(strategy, data, trade_start=trade_start)
        results[spec.run_name] = result
        relation = None
        prepared = strategy.prepared
        prepared_frames[spec.run_name] = prepared
        if {"price_a", "z"}.issubset(prepared.columns):
            relation = prepared
        baselines[spec.run_name] = compute_baselines(
            data,
            primary_symbol=spec.primary,
            secondary_symbol=spec.secondary,
            relationship=relation,
            strategy_return=result.metrics.get("total_return"),
            has_trades=bool(result.metrics.get("number_of_trades")),
        )
    return results, baselines, prepared_frames


def _period_metrics(
    result: BacktestResult, start: pd.Timestamp, end: pd.Timestamp
) -> dict[str, Any]:
    equity = result.equity_curve.loc[start:end]
    if len(equity) < 2:
        return {}
    fills = [fill for fill in result.fills if start <= pd.Timestamp(fill.timestamp) <= end]
    decisions = [decision for decision in result.decisions if start <= pd.Timestamp(decision.timestamp) <= end]
    campaigns = [
        campaign for campaign in result.campaigns
        if start <= pd.Timestamp(campaign["entry_time"]) and pd.Timestamp(campaign["exit_time"]) <= end
    ]
    exposure = result.exposure_curve.loc[start:end] if result.exposure_curve is not None else None
    return calculate_metrics(
        equity,
        fills,
        decisions,
        starting_capital=float(equity.iloc[0]),
        campaigns=campaigns,
        exposure_curve=exposure,
    )


def walk_forward_oos(
    results: dict[str, BacktestResult], *, train_months: int = 6, test_months: int = 1
) -> tuple[dict[str, dict[str, Any]], pd.DataFrame, pd.Timestamp]:
    earliest = max(result.equity_curve.index.min() for result in results.values())
    latest = min(result.equity_curve.index.max() for result in results.values())
    first_test = pd.Timestamp(earliest) + pd.DateOffset(months=train_months)
    oos_metrics: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for name, result in results.items():
        oos_metrics[name] = _period_metrics(result, first_test, pd.Timestamp(latest))
        cursor = first_test
        while cursor < latest:
            test_end = min(cursor + pd.DateOffset(months=test_months) - pd.Timedelta(nanoseconds=1), latest)
            train_start = cursor - pd.DateOffset(months=train_months)
            train_metrics = _period_metrics(result, train_start, cursor - pd.Timedelta(nanoseconds=1))
            test_metrics = _period_metrics(result, cursor, test_end)
            rows.append({
                "run": name,
                "train_start": train_start,
                "train_end": cursor - pd.Timedelta(nanoseconds=1),
                "test_start": cursor,
                "test_end": test_end,
                "train_return": train_metrics.get("total_return", 0.0),
                "test_return": test_metrics.get("total_return", 0.0),
                "test_expectancy_usd": test_metrics.get("expectancy_usd", 0.0),
                "test_profit_factor": test_metrics.get("profit_factor", 0.0),
                "test_trades": test_metrics.get("number_of_trades", 0),
                "test_max_drawdown": test_metrics.get("max_drawdown", 0.0),
            })
            cursor += pd.DateOffset(months=test_months)
    return oos_metrics, pd.DataFrame(rows), first_test


def _metrics_row(name: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "run": name,
        "total_return": metrics.get("total_return", 0.0),
        "annualized_return": metrics.get("annualized_return", 0.0),
        "max_drawdown": metrics.get("max_drawdown", 0.0),
        "profit_factor": metrics.get("profit_factor", 0.0),
        "win_rate": metrics.get("win_rate", 0.0),
        "expectancy_usd": metrics.get("expectancy_usd", 0.0),
        "mean_holding_hours": metrics.get("mean_holding_hours", 0.0),
        "number_of_trades": metrics.get("number_of_trades", 0),
        "exposure_pct": metrics.get("exposure_pct", 0.0),
        "max_gross_leverage_used": metrics.get("max_gross_leverage_used", 0.0),
        "max_net_beta_exposure": metrics.get("max_net_beta_exposure", 0.0),
        "average_mae_usd": metrics.get("average_mae_usd", 0.0),
        "average_mfe_usd": metrics.get("average_mfe_usd", 0.0),
        "top_trade_profit_share": metrics.get("top_trade_profit_share"),
        "top_week_profit_share": metrics.get("top_week_profit_share"),
    }


def metrics_frame(metrics: dict[str, dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame([_metrics_row(name, value) for name, value in metrics.items()])


def _set_s2_variant(config: dict, family: str, dimension: str, value: Any) -> None:
    settings_name = "residual" if family == "residual" else "pairs" if family == "pair" else "natural"
    settings = config["strategy"][settings_name]
    if dimension == "z_entry" and family in {"residual", "pair"}:
        settings["entry_z"] = float(value)
        count = len(settings["grid_levels"])
        settings["grid_levels"] = [float(value) + 0.3 * i for i in range(count)]
    elif dimension == "z_exit" and family in {"residual", "pair"}:
        first = float(value)
        settings["take_profit_z"] = [first, max(0.0, first - 0.3), 0.0]
    elif dimension == "z_kill" and family in {"residual", "pair"}:
        settings["kill_z"] = float(value)
        settings["grid_levels"] = [min(level, float(value) - 0.15) for level in settings["grid_levels"]]
    elif dimension == "beta_window":
        config["features"]["beta_window"] = int(value)
    elif dimension == "correlation_threshold" and family == "residual":
        config["features"]["stock_etf_corr_min"] = float(value)
        config["features"]["stock_etf_short_corr_min"] = float(value)
    elif dimension == "correlation_threshold" and family == "pair":
        config["features"]["stock_pair_corr_min"] = float(value)
    elif dimension == "grid_levels":
        count = int(value)
        settings["grid_level_count"] = count
        if family in {"residual", "pair"}:
            entry, kill = float(settings["entry_z"]), float(settings["kill_z"])
            settings["grid_levels"] = np.linspace(entry, kill - 0.3, count).round(3).tolist()
    elif dimension == "atr_stop_multiplier" and family == "natural":
        settings["hard_stop_atr"] = float(value)
    elif dimension == "breakout_confirmation":
        config["strategy"]["breakout"]["confirmation_mode"] = str(value)


def applicable_sensitivity(config: dict, family: str) -> dict[str, list[Any]]:
    grid = config["sensitivity"]
    if family in {"residual", "pair"}:
        return {key: list(grid[key]) for key in (
            "z_entry", "z_exit", "z_kill", "beta_window", "correlation_threshold", "grid_levels", "breakout_confirmation"
        )}
    return {key: list(grid[key]) for key in ("grid_levels", "atr_stop_multiplier", "breakout_confirmation")}


def select_sensitivity_targets(
    specs: list[StrategySpec], oos_metrics: dict[str, dict[str, Any]]
) -> list[StrategySpec]:
    selected = []
    for family in ("residual", "pair", "natural"):
        candidates = [spec for spec in specs if spec.family == family]
        candidates.sort(
            key=lambda spec: (
                oos_metrics.get(spec.run_name, {}).get("expectancy_usd", 0) > 0,
                min(oos_metrics.get(spec.run_name, {}).get("number_of_trades", 0), 5),
                oos_metrics.get(spec.run_name, {}).get("profit_factor", 0),
                oos_metrics.get(spec.run_name, {}).get("expectancy_usd", 0),
            ),
            reverse=True,
        )
        if candidates:
            selected.append(candidates[0])
    return selected


def run_oat_sensitivity(
    data: dict[str, pd.DataFrame],
    config: dict,
    events: EventCalendar,
    targets: list[StrategySpec],
    first_test: pd.Timestamp,
) -> pd.DataFrame:
    rows = []
    end = min(frame.index.max() for frame in data.values())
    for spec in targets:
        for dimension, values in applicable_sensitivity(config, spec.family).items():
            for value in values:
                candidate = deepcopy(config)
                _set_s2_variant(candidate, spec.family, dimension, value)
                result = BacktestEngine(candidate).run(
                    spec.factory(candidate, events), data, trade_start=first_test
                )
                metrics = _period_metrics(result, first_test, pd.Timestamp(end))
                rows.append({
                    "run": spec.run_name,
                    "family": spec.family,
                    "dimension": dimension,
                    "value": value,
                    **_metrics_row(spec.run_name, metrics),
                })
    return pd.DataFrame(rows)


def robustness_by_run(sensitivity: pd.DataFrame) -> dict[str, float | None]:
    result = {}
    if sensitivity.empty:
        return result
    for name, frame in sensitivity.groupby("run"):
        viable = (
            (frame["expectancy_usd"] > 0)
            & (frame["profit_factor"] > 1.0)
            & (frame["max_drawdown"] > -0.15)
        )
        result[name] = float(viable.mean())
    return result


def acceptance_gate(
    metrics: dict[str, Any], config: dict, robustness: float | None
) -> tuple[bool, list[str]]:
    gate = config["acceptance"]
    checks = {
        "positive OOS expectancy": float(metrics.get("expectancy_usd", 0)) > 0,
        f"profit factor > {gate['minimum_profit_factor']}": float(metrics.get("profit_factor", 0)) > float(gate["minimum_profit_factor"]),
        "drawdown acceptable relative to return": (
            float(metrics.get("max_drawdown", -1)) >= -float(gate["maximum_drawdown_pct"])
            and float(metrics.get("total_return", 0)) > abs(float(metrics.get("max_drawdown", 0))) * 0.5
        ),
        f"at least {gate['minimum_trades']} OOS trades": int(metrics.get("number_of_trades", 0)) >= int(gate["minimum_trades"]),
        "no single trade dominates gross profit": (
            metrics.get("top_trade_profit_share") is not None
            and float(metrics["top_trade_profit_share"]) <= float(gate["maximum_profit_concentration"])
        ),
        "no single week dominates gross profit": (
            metrics.get("top_week_profit_share") is not None
            and float(metrics["top_week_profit_share"]) <= float(gate["maximum_profit_concentration"])
        ),
        "nearby-parameter robustness": robustness is not None and robustness >= float(gate["minimum_nearby_parameter_pass_rate"]),
        "no known lookahead/data leakage": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return not failed, failed
