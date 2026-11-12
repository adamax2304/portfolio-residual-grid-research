from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from residual_grid_research.models import Decision, Fill, StrategyState


def calculate_metrics(
    equity_curve: pd.Series,
    fills: list[Fill],
    decisions: list[Decision],
    *,
    starting_capital: float,
    financing_cost: float = 0.0,
    campaigns: list[dict[str, Any]] | None = None,
    exposure_curve: pd.DataFrame | None = None,
) -> dict[str, Any]:
    if equity_curve.empty:
        return {}
    daily = equity_curve.groupby(equity_curve.index.normalize()).last()
    returns = daily.pct_change().dropna()
    total_return = float(equity_curve.iloc[-1] / starting_capital - 1)
    elapsed_days = max(1, (equity_curve.index[-1] - equity_curve.index[0]).days)
    annualized = float((1 + total_return) ** (365.25 / elapsed_days) - 1) if 1 + total_return > 0 else -1.0
    drawdown = equity_curve / equity_curve.cummax() - 1
    sharpe = float(np.sqrt(252) * returns.mean() / returns.std(ddof=1)) if len(returns) > 1 and returns.std(ddof=1) > 0 else 0.0
    downside = returns[returns < 0]
    sortino = float(np.sqrt(252) * returns.mean() / downside.std(ddof=1)) if len(downside) > 1 and downside.std(ddof=1) > 0 else 0.0
    campaigns = campaigns or []
    closed_campaigns = [campaign for campaign in campaigns if campaign.get("closed")]
    closed = [float(campaign["pnl_usd"]) for campaign in closed_campaigns]
    wins = [pnl for pnl in closed if pnl > 0]
    losses = [pnl for pnl in closed if pnl < 0]
    profit_factor = sum(wins) / abs(sum(losses)) if losses else (math.inf if wins else 0.0)
    gross_turnover = sum(fill.gross_notional for fill in fills)
    total_cost = sum(fill.commission + fill.friction_cost for fill in fills) + financing_cost
    slippage_bps = 0.0
    if fills:
        # Friction contains half-spread plus slippage. The configured engine is
        # intentionally not reconstructed here; scaling the observed component
        # gives a transparent local execution sensitivity approximation.
        slippage_bps = sum(fill.friction_cost for fill in fills)
    holding_hours = [float(campaign["duration_hours"]) for campaign in closed_campaigns]
    breakout_campaigns = [campaign for campaign in closed_campaigns if campaign.get("regime") == "breakout"]
    mean_reversion_campaigns = [campaign for campaign in closed_campaigns if campaign.get("regime") == "range"]
    slippage_sensitivity = {}
    for multiple in (0.5, 1.0, 2.0):
        adjusted_ending = float(equity_curve.iloc[-1]) + slippage_bps * (1 - multiple)
        slippage_sensitivity[f"{multiple:.1f}x"] = adjusted_ending / starting_capital - 1
    if exposure_curve is not None and not exposure_curve.empty:
        active_days = int((exposure_curve["gross_leverage"] > 1e-12).groupby(exposure_curve.index.normalize()).max().sum())
        max_gross_leverage = float(exposure_curve["gross_leverage"].max())
        max_net_beta_exposure = float(exposure_curve["net_beta_exposure"].abs().max())
    else:
        active_days = len({pd.Timestamp(fill.timestamp).normalize() for fill in fills})
        max_gross_leverage = 0.0
        max_net_beta_exposure = 0.0
    total_days = max(1, len(daily))
    kills = sum(decision.state_to == StrategyState.KILL for decision in decisions)
    best = sorted(closed, reverse=True)[:5]
    worst = sorted(closed)[:5]
    regime_performance = {}
    for regime in ("range", "warning", "breakout", "failed_breakout"):
        selected = [campaign for campaign in closed_campaigns if campaign.get("regime") == regime]
        regime_performance[regime] = {
            "trades": len(selected),
            "pnl_usd": float(sum(campaign["pnl_usd"] for campaign in selected)),
            "win_rate": float(sum(campaign["pnl_usd"] > 0 for campaign in selected) / len(selected)) if selected else None,
            "expectancy_usd": float(np.mean([campaign["pnl_usd"] for campaign in selected])) if selected else None,
        }
    gross_profits = sum(max(0.0, pnl) for pnl in closed)
    top_trade_share = max((max(0.0, pnl) for pnl in closed), default=0.0) / gross_profits if gross_profits else None
    weekly_profit: dict[str, float] = {}
    for campaign in closed_campaigns:
        exit_time = pd.Timestamp(campaign["exit_time"])
        if exit_time.tzinfo is not None:
            exit_time = exit_time.tz_localize(None)
        week = exit_time.to_period("W").start_time.date().isoformat()
        weekly_profit[week] = weekly_profit.get(week, 0.0) + float(campaign["pnl_usd"])
    gross_positive_weeks = sum(max(0.0, pnl) for pnl in weekly_profit.values())
    top_week_share = max((max(0.0, pnl) for pnl in weekly_profit.values()), default=0.0) / gross_positive_weeks if gross_positive_weeks else None
    return {
        "starting_capital": starting_capital,
        "ending_equity": float(equity_curve.iloc[-1]),
        "total_return": total_return,
        "annualized_return": annualized,
        "max_drawdown": float(drawdown.min()),
        "sharpe": sharpe,
        "sortino": sortino,
        "profit_factor": float(profit_factor),
        "win_rate": float(len(wins) / len(closed)) if closed else 0.0,
        "number_of_trades": len(closed_campaigns),
        "closed_trade_legs": sum(abs(fill.realized_pnl) > 1e-12 for fill in fills),
        "expectancy_usd": float(np.mean(closed)) if closed else 0.0,
        "expectancy_r": float(np.mean(closed) / (starting_capital * 0.01)) if closed else 0.0,
        "turnover": float(gross_turnover / starting_capital),
        "exposure_pct": float(active_days / total_days),
        "fill_count": len(fills),
        "kill_count": kills,
        "cost_drag_usd": float(total_cost),
        "financing_cost_usd": float(financing_cost),
        "max_gross_leverage_used": max_gross_leverage,
        "max_net_beta_exposure": max_net_beta_exposure,
        "average_mae_usd": float(np.mean([campaign["mae_usd"] for campaign in closed_campaigns])) if closed_campaigns else 0.0,
        "average_mfe_usd": float(np.mean([campaign["mfe_usd"] for campaign in closed_campaigns])) if closed_campaigns else 0.0,
        "worst_mae_r": float(min((campaign["mae_r"] for campaign in closed_campaigns), default=0.0)),
        "best_mfe_r": float(max((campaign["mfe_r"] for campaign in closed_campaigns), default=0.0)),
        "mean_holding_hours": float(np.mean(holding_hours)) if holding_hours else 0.0,
        "median_holding_hours": float(np.median(holding_hours)) if holding_hours else 0.0,
        "mean_reversion_success_rate": (
            sum(campaign["pnl_usd"] > 0 for campaign in mean_reversion_campaigns) / len(mean_reversion_campaigns)
            if mean_reversion_campaigns else None
        ),
        "breakout_success_rate": (
            sum(campaign["pnl_usd"] > 0 for campaign in breakout_campaigns) / len(breakout_campaigns)
            if breakout_campaigns else None
        ),
        "performance_by_regime": regime_performance,
        "top_trade_profit_share": top_trade_share,
        "top_week_profit_share": top_week_share,
        "slippage_sensitivity_return": slippage_sensitivity,
        "best_5_trade_legs_usd": best,
        "worst_5_trade_legs_usd": worst,
    }


def buy_and_hold_return(frame: pd.DataFrame) -> float:
    close = frame["close"].dropna()
    return float(close.iloc[-1] / close.iloc[0] - 1) if len(close) >= 2 else 0.0


def naive_two_level_mean_reversion(
    relationship: pd.DataFrame,
    *,
    entry_z: float = 1.4,
    add_step: float = 0.3,
    cost_bps: float = 8.0,
) -> float:
    frame = relationship[["price_a", "z"]].dropna()
    if len(frame) < 2:
        return 0.0
    cash = 1.0
    quantity = 0.0
    layers = 0
    for row in frame.itertuples():
        price = float(row.price_a)
        z = float(row.z)
        if layers == 0 and z <= -entry_z:
            spend = cash * 0.5
            quantity += spend * (1 - cost_bps / 10000) / price
            cash -= spend
            layers = 1
        elif layers == 1 and z <= -(entry_z + add_step):
            spend = cash
            quantity += spend * (1 - cost_bps / 10000) / price
            cash = 0.0
            layers = 2
        elif layers and z >= 0:
            cash += quantity * price * (1 - cost_bps / 10000)
            quantity = 0.0
            layers = 0
    ending = cash + quantity * float(frame["price_a"].iloc[-1]) * (1 - cost_bps / 10000)
    return float(ending - 1.0)


def naive_price_mean_reversion(
    frame: pd.DataFrame,
    *,
    entry_z: float = 1.4,
    add_step: float = 0.3,
    window: int = 60,
    cost_bps: float = 8.0,
) -> float:
    close = frame["close"].dropna()
    mean = close.shift(1).rolling(window, min_periods=window).mean()
    std = close.shift(1).rolling(window, min_periods=window).std(ddof=1)
    relationship = pd.DataFrame({"price_a": close, "z": (close - mean) / std.replace(0, np.nan)})
    return naive_two_level_mean_reversion(
        relationship, entry_z=entry_z, add_step=add_step, cost_bps=cost_bps
    )


def compute_baselines(
    data: dict[str, pd.DataFrame],
    *,
    primary_symbol: str,
    secondary_symbol: str | None = None,
    relationship: pd.DataFrame | None = None,
    strategy_return: float | None = None,
    has_trades: bool = True,
) -> dict[str, Any]:
    baselines = {
        "buy_and_hold": buy_and_hold_return(data[primary_symbol]),
        "secondary_buy_and_hold": buy_and_hold_return(data[secondary_symbol]) if secondary_symbol and secondary_symbol in data else None,
        "spy": buy_and_hold_return(data["SPY"]) if "SPY" in data else None,
        "naive_two_level_mean_reversion": (
            naive_two_level_mean_reversion(relationship)
            if relationship is not None
            else naive_price_mean_reversion(data[primary_symbol])
        ),
    }
    comparable = [float(baselines[key]) for key in ("buy_and_hold", "spy", "naive_two_level_mean_reversion") if baselines[key] is not None]
    baselines["edge_found"] = bool(
        has_trades
        and strategy_return is not None
        and len(comparable) == 3
        and all(strategy_return > value for value in comparable)
    )
    return baselines
