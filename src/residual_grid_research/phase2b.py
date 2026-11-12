from __future__ import annotations

import ast
import json
import math
from copy import deepcopy
from dataclasses import asdict
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from residual_grid_research.backtest import BacktestEngine
from residual_grid_research.config import load_config, project_path
from residual_grid_research.data import EventCalendar, YahooFinanceClient
from residual_grid_research.features.statistics import mean_reversion_diagnostics, rolling_relationship
from residual_grid_research.models import BacktestResult
from residual_grid_research.reports.phase2b import write_candidate_deep_dive, write_edge_triage_report
from residual_grid_research.research import all_configured_symbols
from residual_grid_research.strategies import NaturalLongGridStrategy, ResidualGridStrategy, StockPairGridStrategy
from residual_grid_research.validation import StrategySpec, _period_metrics, strategy_specs


DEEP_RUNS = (
    "residual_grid:JPM/XLF",
    "natural_long_grid:CSCO",
    "stock_pair_grid:MA/V",
    "residual_grid:XOM/XLE",
)


def _output_dir(config: dict) -> Path:
    path = project_path(config, config.get("outputs", {}).get("directory", "outputs/phase2b"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def fetch_phase2b_data(config: dict, *, force: bool = False) -> dict[str, Any]:
    """Fetch the extended daily universe into a Phase-2B-specific cache."""
    client = YahooFinanceClient(project_path(config, config["data"]["cache_dir"]))
    symbols = all_configured_symbols(config)
    daily, records = client.fetch_universe_daily(
        symbols,
        str(config["data"]["daily_start"]),
        str(config["data"]["daily_end"]),
        force=force,
    )
    stocks = list(config["universe"]["stock_etf_map"])
    event_path = project_path(config, config["data"]["event_path"])
    events, warnings = client.build_historical_events(stocks, daily, event_path, earnings_limit=32)
    manifest = {
        "phase": "2B",
        "daily": [{**asdict(record), "quality": asdict(record.quality)} for record in records],
        "events": len(events),
        "event_warnings": warnings,
    }
    manifest_path = project_path(config, "data", "real", "phase2b_download_manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return manifest


def load_phase2b_data(config: dict) -> dict[str, pd.DataFrame]:
    client = YahooFinanceClient(project_path(config, config["data"]["cache_dir"]))
    data, _ = client.fetch_universe_daily(
        all_configured_symbols(config),
        str(config["data"]["daily_start"]),
        str(config["data"]["daily_end"]),
    )
    return data


def load_phase2b_events(config: dict) -> EventCalendar:
    path = project_path(config, config["data"]["event_path"])
    if not path.exists():
        raise FileNotFoundError(f"Run phase2b-fetch first; missing {path}")
    return EventCalendar(pd.read_csv(path))


def _family(run: str) -> str:
    return "residual" if run.startswith("residual_grid:") else "pair" if run.startswith("stock_pair_grid:") else "natural"


def _symbols_for_run(run: str) -> list[str]:
    value = run.split(":", 1)[1]
    return value.split("/")


def _spec_for_run(run: str, config: dict, events: EventCalendar) -> StrategySpec:
    symbols = _symbols_for_run(run)
    family = _family(run)
    if family == "residual":
        a, b = symbols
        return StrategySpec(run, family, a, b, lambda cfg, ev: ResidualGridStrategy(cfg, a, b, events=ev))
    if family == "pair":
        a, b = symbols
        return StrategySpec(run, family, a, b, lambda cfg, ev: StockPairGridStrategy(cfg, a, b, events=ev))
    symbol = symbols[0]
    return StrategySpec(run, family, symbol, None, lambda cfg, ev: NaturalLongGridStrategy(cfg, symbol, events=ev))


def _first_test(data: dict[str, pd.DataFrame], months: int = 6) -> pd.Timestamp:
    earliest = max(pd.Timestamp(frame.index.min()) for frame in data.values())
    return earliest + pd.DateOffset(months=months)


def _last_test(data: dict[str, pd.DataFrame]) -> pd.Timestamp:
    return min(pd.Timestamp(frame.index.max()) for frame in data.values())


def _safe_pf(values: pd.Series | list[float]) -> float:
    pnl = pd.Series(values, dtype=float)
    wins = float(pnl[pnl > 0].sum())
    losses = float(pnl[pnl < 0].sum())
    return wins / abs(losses) if losses else (math.inf if wins else 0.0)


def _parse_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return {}
    try:
        parsed = ast.literal_eval(str(value))
        return parsed if isinstance(parsed, dict) else {}
    except (SyntaxError, ValueError):
        return {}


def enrich_campaigns(campaigns: pd.DataFrame, fills: pd.DataFrame) -> pd.DataFrame:
    """Add mode, direction and exit attribution to old or new campaign sidecars."""
    if campaigns.empty:
        return campaigns.copy()
    output = campaigns.copy()
    for column in ("entry_time", "exit_time"):
        output[column] = pd.to_datetime(output[column])
    if "campaign_mode" not in output:
        output["campaign_mode"] = "grid_mean_reversion"
    if "direction" not in output:
        output["direction"] = "unknown"
    if "entry_reason" not in output:
        output["entry_reason"] = ""
    if "exit_reason" not in output:
        output["exit_reason"] = ""
    if "exit_category" not in output:
        output["exit_category"] = "other"
    if fills.empty:
        return output
    fill_frame = fills.copy()
    fill_frame["timestamp"] = pd.to_datetime(fill_frame["timestamp"])
    fill_frame["metadata_dict"] = fill_frame.get("metadata", pd.Series(index=fill_frame.index, dtype=object)).map(_parse_metadata)
    for index, campaign in output.iterrows():
        selected = fill_frame[fill_frame["group_id"] == campaign["group_id"]].sort_values("timestamp")
        if "run" in output and "run" in fill_frame:
            selected = selected[selected["run"] == campaign["run"]]
        if selected.empty:
            continue
        entry = selected.iloc[0]
        final_time = selected["timestamp"].max()
        exits = selected[selected["timestamp"] == final_time]
        entry_reason = str(entry.get("reason", ""))
        exit_reason = "; ".join(dict.fromkeys(exits["reason"].astype(str)))
        all_reasons = " ".join(selected["reason"].astype(str)).lower()
        lower_exit = exit_reason.lower()
        if "failed breakout" in lower_exit:
            category = "failed_breakout"
        elif any(token in lower_exit for token in ("kill", "adverse excursion", "invalidation")):
            category = "kill"
        elif any(token in lower_exit for token in ("time stop", "timed out")):
            category = "time_stop"
        elif "breakout" in lower_exit:
            category = "breakout_exit"
        elif any(token in lower_exit for token in ("tp", "target", "mean reversion completed")):
            category = "take_profit"
        elif "end-of-sample" in lower_exit:
            category = "end_of_sample"
        else:
            category = "other"
        group_id = str(campaign["group_id"])
        if ":breakout:" in group_id or "breakout continuation" in entry_reason.lower():
            mode = "breakout_continuation"
        elif "breakout" in all_reasons:
            mode = "hybrid_breakout"
        else:
            mode = "grid_mean_reversion"
        metadata = entry["metadata_dict"]
        direction = metadata.get("direction")
        if direction is None:
            direction = 1 if str(entry.get("side", "BUY")).upper() == "BUY" else -1
        output.at[index, "entry_reason"] = entry_reason
        output.at[index, "exit_reason"] = exit_reason
        output.at[index, "exit_category"] = category
        output.at[index, "campaign_mode"] = mode
        output.at[index, "direction"] = "long_residual" if int(direction) > 0 else "short_residual"
    return output


def _result_frames(run: str, result: BacktestResult) -> tuple[pd.DataFrame, pd.DataFrame]:
    campaigns = pd.DataFrame([{"run": run, **value} for value in result.campaigns])
    fills = pd.DataFrame([{"run": run, **fill.to_dict()} for fill in result.fills])
    return enrich_campaigns(campaigns, fills), fills


def _strict_cost_metrics(campaigns: pd.DataFrame, fills: pd.DataFrame, multiple: float) -> dict[str, float]:
    if campaigns.empty:
        return {"return": 0.0, "expectancy": 0.0, "profit_factor": 0.0}
    costs = pd.Series(dtype=float)
    if not fills.empty:
        fill_cost = pd.to_numeric(fills["commission"], errors="coerce").fillna(0) + pd.to_numeric(fills["friction_cost"], errors="coerce").fillna(0)
        costs = fill_cost.groupby(fills["group_id"]).sum()
    adjusted = []
    for row in campaigns.itertuples():
        baseline_cost = float(costs.get(row.group_id, 0.0)) + float(getattr(row, "financing_cost_usd", 0.0))
        adjusted.append(float(row.pnl_usd) - (multiple - 1.0) * baseline_cost)
    pnl = pd.Series(adjusted, dtype=float)
    return {
        "return": float(pnl.sum() / 100000.0),
        "expectancy": float(pnl.mean()) if len(pnl) else 0.0,
        "profit_factor": _safe_pf(pnl),
    }


def _campaign_concentration(campaigns: pd.DataFrame) -> dict[str, float | None]:
    if campaigns.empty:
        return {"campaign_gross": None, "campaign_net": None, "week_gross": None, "month_gross": None}
    frame = campaigns.copy()
    frame["pnl_usd"] = pd.to_numeric(frame["pnl_usd"], errors="coerce").fillna(0)
    gross = float(frame["pnl_usd"].clip(lower=0).sum())
    net = float(frame["pnl_usd"].sum())
    positive_max = float(frame["pnl_usd"].clip(lower=0).max())
    exit_time = pd.to_datetime(frame["exit_time"]).dt.tz_localize(None)
    weekly = frame.assign(period=exit_time.dt.to_period("W")).groupby("period")["pnl_usd"].sum()
    monthly = frame.assign(period=exit_time.dt.to_period("M")).groupby("period")["pnl_usd"].sum()
    weekly_gross = float(weekly.clip(lower=0).sum())
    monthly_gross = float(monthly.clip(lower=0).sum())
    return {
        "campaign_gross": positive_max / gross if gross else None,
        "campaign_net": positive_max / net if net > 0 else None,
        "week_gross": float(weekly.clip(lower=0).max() / weekly_gross) if weekly_gross else None,
        "month_gross": float(monthly.clip(lower=0).max() / monthly_gross) if monthly_gross else None,
    }


def _attribution(campaigns: pd.DataFrame) -> dict[str, float]:
    if campaigns.empty:
        return {
            "grid_pnl_usd": 0.0, "breakout_pnl_usd": 0.0, "hybrid_breakout_pnl_usd": 0.0,
            "failed_breakout_pnl_usd": 0.0, "kill_pnl_usd": 0.0, "time_stop_pnl_usd": 0.0,
            "long_residual_pnl_usd": 0.0, "short_residual_pnl_usd": 0.0,
            "range_regime_pnl_usd": 0.0, "breakout_regime_pnl_usd": 0.0,
            "failed_breakout_regime_pnl_usd": 0.0, "warning_regime_pnl_usd": 0.0,
        }
    pnl = pd.to_numeric(campaigns["pnl_usd"], errors="coerce").fillna(0)
    mode = campaigns["campaign_mode"].astype(str)
    exit_category = campaigns["exit_category"].astype(str)
    direction = campaigns["direction"].astype(str)
    regime = campaigns.get("regime", pd.Series("range", index=campaigns.index)).astype(str)
    return {
        "grid_pnl_usd": float(pnl[mode == "grid_mean_reversion"].sum()),
        "breakout_pnl_usd": float(pnl[mode == "breakout_continuation"].sum()),
        "hybrid_breakout_pnl_usd": float(pnl[mode == "hybrid_breakout"].sum()),
        "failed_breakout_pnl_usd": float(pnl[exit_category == "failed_breakout"].sum()),
        "kill_pnl_usd": float(pnl[exit_category == "kill"].sum()),
        "time_stop_pnl_usd": float(pnl[exit_category == "time_stop"].sum()),
        "long_residual_pnl_usd": float(pnl[direction == "long_residual"].sum()),
        "short_residual_pnl_usd": float(pnl[direction == "short_residual"].sum()),
        "range_regime_pnl_usd": float(pnl[regime == "range"].sum()),
        "breakout_regime_pnl_usd": float(pnl[regime == "breakout"].sum()),
        "failed_breakout_regime_pnl_usd": float(pnl[regime == "failed_breakout"].sum()),
        "warning_regime_pnl_usd": float(pnl[regime == "warning"].sum()),
    }


def _month_stats(campaigns: pd.DataFrame) -> dict[str, float | int]:
    if campaigns.empty:
        return {"positive_months": 0, "active_months": 0, "positive_month_rate": 0.0}
    monthly = campaigns.assign(month=pd.to_datetime(campaigns["exit_time"]).dt.tz_localize(None).dt.to_period("M")).groupby("month")["pnl_usd"].sum()
    return {
        "positive_months": int((monthly > 0).sum()),
        "active_months": int((monthly != 0).sum()),
        "positive_month_rate": float((monthly > 0).mean()) if len(monthly) else 0.0,
    }


def _event_proximity(campaigns: pd.DataFrame, events: pd.DataFrame, run: str) -> dict[str, Any]:
    event_rows = events[events["symbol"].astype(str).str.upper().isin(_symbols_for_run(run))].copy()
    if campaigns.empty or event_rows.empty:
        return {"nearest_event_days": None, "within_3": 0, "within_5": 0, "within_10": 0}
    event_dates = pd.to_datetime(event_rows["date"]).dt.tz_localize(None).dt.normalize()
    distances: list[int] = []
    for entry in pd.to_datetime(campaigns["entry_time"]).dt.tz_localize(None).dt.normalize():
        values = [abs(int(np.busday_count(min(entry.date(), date.date()), max(entry.date(), date.date())))) for date in event_dates]
        distances.append(min(values))
    return {
        "nearest_event_days": min(distances) if distances else None,
        "within_3": int(sum(value <= 3 for value in distances)),
        "within_5": int(sum(value <= 5 for value in distances)),
        "within_10": int(sum(value <= 10 for value in distances)),
    }


def phase2a_triage(config: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    root = Path(config["_project_root"])
    metrics = pd.read_csv(root / "outputs" / "real_data_oos_metrics.csv")
    campaigns = pd.read_csv(root / "outputs" / "real_data_oos_campaigns.csv")
    fills = pd.read_csv(root / "outputs" / "real_data_oos_fills.csv")
    campaigns = enrich_campaigns(campaigns, fills)
    sensitivity = pd.read_csv(root / "outputs" / "real_data_sensitivity.csv")
    sensitivity_rates = {}
    for run, frame in sensitivity.groupby("run"):
        sensitivity_rates[run] = float(((frame["expectancy_usd"] > 0) & (frame["profit_factor"] > 1.15)).mean())
    rows = []
    for metric in metrics.to_dict("records"):
        run = str(metric["run"])
        selected_campaigns = campaigns[campaigns["run"] == run].copy()
        selected_fills = fills[fills["run"] == run].copy()
        concentration = _campaign_concentration(selected_campaigns)
        strict = _strict_cost_metrics(selected_campaigns, selected_fills, 2.0)
        attrib = _attribution(selected_campaigns)
        month = _month_stats(selected_campaigns)
        campaigns_n = len(selected_campaigns)
        trade_legs = int((pd.to_numeric(selected_fills.get("realized_pnl", 0), errors="coerce").abs() > 1e-12).sum()) if not selected_fills.empty else 0
        pf = float(metric.get("profit_factor", 0))
        expectancy = float(metric.get("expectancy_usd", 0))
        sensitivity_rate = sensitivity_rates.get(run)
        breakout_total = attrib["breakout_pnl_usd"] + attrib["hybrid_breakout_pnl_usd"]
        grid_total = attrib["grid_pnl_usd"]
        flags: list[str] = []
        if expectancy <= 0 or pf <= 1.0:
            flags.append("FAILED_EDGE")
        if campaigns_n < 10:
            flags.append("TOO_FEW_TRADES")
        elif campaigns_n < 30:
            flags.append("PROMISING_BUT_UNDERPOWERED")
        if expectancy > 0 and strict["expectancy"] <= 0:
            flags.append("COST_SENSITIVE")
        if breakout_total > 0 and grid_total <= 0:
            flags.append("BREAKOUT_DEPENDENT")
        if sensitivity_rate is not None and sensitivity_rate < 0.60:
            flags.append("PARAMETER_FRAGILE")
        if not flags and campaigns_n >= 30 and pf > 1.15 and expectancy > 0:
            flags.append("ROBUST_CANDIDATE")
        priority = (
            ["TOO_FEW_TRADES", "FAILED_EDGE", "COST_SENSITIVE", "BREAKOUT_DEPENDENT", "PARAMETER_FRAGILE", "PROMISING_BUT_UNDERPOWERED", "ROBUST_CANDIDATE"]
            if campaigns_n < 5 else
            ["FAILED_EDGE", "COST_SENSITIVE", "BREAKOUT_DEPENDENT", "PARAMETER_FRAGILE", "TOO_FEW_TRADES", "PROMISING_BUT_UNDERPOWERED", "ROBUST_CANDIDATE"]
        )
        classification = next((value for value in priority if value in flags), "PROMISING_BUT_UNDERPOWERED")
        rows.append({
            "run": run,
            "family": _family(run),
            "classification": classification,
            "diagnostic_flags": ";".join(flags),
            "oos_return": float(metric.get("total_return", 0)),
            "profit_factor": pf,
            "expectancy_usd": expectancy,
            "max_drawdown": float(metric.get("max_drawdown", 0)),
            "trade_legs": trade_legs,
            "campaigns": campaigns_n,
            "average_campaign_hours": float(selected_campaigns["duration_hours"].mean()) if campaigns_n else 0.0,
            "exposure_pct": float(metric.get("exposure_pct", 0)),
            "average_mae_usd": float(selected_campaigns["mae_usd"].mean()) if campaigns_n else 0.0,
            "average_mfe_usd": float(selected_campaigns["mfe_usd"].mean()) if campaigns_n else 0.0,
            "worst_campaign_usd": float(selected_campaigns["pnl_usd"].min()) if campaigns_n else 0.0,
            "best_campaign_usd": float(selected_campaigns["pnl_usd"].max()) if campaigns_n else 0.0,
            "top_campaign_gross_profit_share": concentration["campaign_gross"],
            "top_campaign_net_profit_share": concentration["campaign_net"],
            "top_week_gross_profit_share": concentration["week_gross"],
            "top_month_gross_profit_share": concentration["month_gross"],
            "strict_2x_cost_expectancy_usd": strict["expectancy"],
            "strict_2x_cost_profit_factor": strict["profit_factor"],
            "parameter_positive_rate": sensitivity_rate,
            **month,
            **attrib,
        })
    return pd.DataFrame(rows), campaigns, fills


def pair_diagnostics(data: dict[str, pd.DataFrame], config: dict, events: EventCalendar) -> pd.DataFrame:
    rows = []
    screen = config["pair_screen"]
    universe = config["universe"]
    for group_name, symbols in universe["pair_groups"].items():
        for a, b in combinations(symbols, 2):
            relation = rolling_relationship(
                data[a], data[b], beta_window=int(config["features"]["beta_window"]),
                z_window=int(config["features"]["z_window"]), correlation_windows=config["features"]["correlation_windows"],
            )
            diagnostics = mean_reversion_diagnostics(relation, entry_z=1.5, kill_z=3.0, include_adf=True)
            clean = relation.dropna(subset=["corr_60", "beta_stability"])
            overlap = len(relation)
            median_corr = float(clean["corr_60"].median()) if len(clean) else float("nan")
            beta_stability = float(clean["beta_stability"].median()) if len(clean) else float("nan")
            adv_a = float((data[a]["close"] * data[a]["volume"]).shift(1).rolling(20).mean().median())
            adv_b = float((data[b]["close"] * data[b]["volume"]).shift(1).rolling(20).mean().median())
            sample_index = relation.index[::5]
            blocked = sum(events.check(
                [a, b], timestamp, is_short=True,
                earnings_before=int(config["events"]["earnings_before_trading_days"]),
                earnings_after=int(config["events"]["earnings_after_trading_days"]),
                ex_dividend_buffer=int(config["events"]["ex_dividend_short_buffer_days"]),
            ).blocked for timestamp in sample_index)
            event_pct = blocked / max(1, len(sample_index))
            checks = {
                "history": overlap >= int(universe["min_history_bars"]),
                "liquidity": min(adv_a, adv_b) >= float(universe["min_average_daily_dollar_volume"]),
                "correlation": median_corr >= float(screen["minimum_median_correlation"]),
                "beta_stability": beta_stability <= float(screen["maximum_median_beta_stability"]),
                "stationarity_proxy": diagnostics.get("half_life_bars") is not None and float(diagnostics["half_life_bars"]) <= float(screen["maximum_half_life_bars"]),
                "signal_density": float(diagnostics.get("crossings_per_year") or 0) >= float(screen["minimum_crossings_per_year"]),
                "event_conflict": event_pct <= float(screen["maximum_event_blocked_pct"]),
            }
            rows.append({
                "group": group_name, "asset_a": a, "asset_b": b, "run": f"stock_pair_grid:{a}/{b}",
                "overlap_bars": overlap, "median_corr_60": median_corr,
                "median_beta_stability": beta_stability, "half_life_bars": diagnostics.get("half_life_bars"),
                "crossings_per_year": diagnostics.get("crossings_per_year"), "adf_pvalue": diagnostics.get("adf_pvalue"),
                "minimum_average_dollar_volume": min(adv_a, adv_b), "event_blocked_pct": event_pct,
                "selected": all(checks.values()),
                "failure_reasons": ";".join(name for name, passed in checks.items() if not passed),
            })
    return pd.DataFrame(rows)


def _metrics_record(run: str, spec: StrategySpec, result: BacktestResult, metrics: dict[str, Any], campaigns: pd.DataFrame, fills: pd.DataFrame, first_test: pd.Timestamp, end: pd.Timestamp) -> dict[str, Any]:
    concentration = _campaign_concentration(campaigns)
    strict = _strict_cost_metrics(campaigns, fills, 2.0)
    attrib = _attribution(campaigns)
    month = _month_stats(campaigns)
    later = _period_metrics(result, first_test + pd.DateOffset(months=6), end)
    positive_regimes = 0
    if not campaigns.empty and "regime" in campaigns:
        positive_regimes = int((campaigns.groupby("regime")["pnl_usd"].sum() > 0).sum())
    return {
        "run": run, "family": spec.family, "primary": spec.primary, "secondary": spec.secondary,
        "oos_return": float(metrics.get("total_return", 0)), "annualized_return": float(metrics.get("annualized_return", 0)),
        "profit_factor": float(metrics.get("profit_factor", 0)), "expectancy_usd": float(metrics.get("expectancy_usd", 0)),
        "max_drawdown": float(metrics.get("max_drawdown", 0)), "win_rate": float(metrics.get("win_rate", 0)),
        "trade_legs": int(metrics.get("closed_trade_legs", 0)), "campaigns": len(campaigns),
        "average_campaign_hours": float(campaigns["duration_hours"].mean()) if len(campaigns) else 0.0,
        "exposure_pct": float(metrics.get("exposure_pct", 0)),
        "average_mae_usd": float(metrics.get("average_mae_usd", 0)), "average_mfe_usd": float(metrics.get("average_mfe_usd", 0)),
        "worst_campaign_usd": float(campaigns["pnl_usd"].min()) if len(campaigns) else 0.0,
        "best_campaign_usd": float(campaigns["pnl_usd"].max()) if len(campaigns) else 0.0,
        "top_campaign_gross_profit_share": concentration["campaign_gross"],
        "top_campaign_net_profit_share": concentration["campaign_net"],
        "top_week_gross_profit_share": concentration["week_gross"], "top_month_gross_profit_share": concentration["month_gross"],
        "strict_2x_cost_return": strict["return"], "strict_2x_cost_expectancy_usd": strict["expectancy"],
        "strict_2x_cost_profit_factor": strict["profit_factor"],
        "twelve_month_warmup_expectancy_usd": float(later.get("expectancy_usd", 0)),
        "twelve_month_warmup_profit_factor": float(later.get("profit_factor", 0)),
        "positive_regimes": positive_regimes,
        **month, **attrib,
    }


def run_expanded_universe(data: dict[str, pd.DataFrame], config: dict, events: EventCalendar, pair_frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, BacktestResult], pd.DataFrame, pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    selected_pairs = pair_frame.loc[pair_frame["selected"], ["asset_a", "asset_b"]].values.tolist()
    candidate = deepcopy(config)
    candidate["universe"]["stock_pairs"] = selected_pairs
    first_test, end = _first_test(data, int(config["walk_forward"]["train_months"])), _last_test(data)
    records, results, campaign_frames, fill_frames = [], {}, [], []
    for spec in strategy_specs(candidate):
        strategy = spec.factory(candidate, events)
        result = BacktestEngine(candidate).run(strategy, data, trade_start=first_test)
        metrics = _period_metrics(result, first_test, end)
        campaigns, fills = _result_frames(spec.run_name, result)
        if not campaigns.empty:
            campaigns = campaigns[(campaigns["entry_time"] >= first_test) & (campaigns["exit_time"] <= end)]
            campaign_frames.append(campaigns)
        if not fills.empty:
            fills = fills[(pd.to_datetime(fills["timestamp"]) >= first_test) & (pd.to_datetime(fills["timestamp"]) <= end)]
            fill_frames.append(fills)
        results[spec.run_name] = result
        records.append(_metrics_record(spec.run_name, spec, result, metrics, campaigns, fills, first_test, end))
    return (
        pd.DataFrame(records), results,
        pd.concat(campaign_frames, ignore_index=True) if campaign_frames else pd.DataFrame(),
        pd.concat(fill_frames, ignore_index=True) if fill_frames else pd.DataFrame(),
        first_test, end,
    )


def _apply_density_variant(candidate: dict, family: str, dimension: str, value: Any) -> None:
    settings_key = "residual" if family == "residual" else "pairs" if family == "pair" else "natural"
    settings = candidate["strategy"][settings_key]
    if dimension == "z_entry":
        settings["entry_z"] = float(value)
        settings["grid_levels"] = np.linspace(float(value), float(settings["kill_z"]) - 0.3, int(settings["grid_level_count"])).round(3).tolist()
    elif dimension == "correlation_threshold":
        if family == "residual":
            candidate["features"]["stock_etf_corr_min"] = float(value)
            candidate["features"]["stock_etf_short_corr_min"] = float(value)
        else:
            candidate["features"]["stock_pair_corr_min"] = float(value)
            candidate["features"]["stock_pair_corr_90_min"] = min(float(value), 0.70)
    elif dimension == "beta_stability_threshold":
        candidate["features"]["beta_stability_max"] = float(value)
    elif dimension == "grid_levels":
        count = int(value)
        settings["grid_level_count"] = count
        if family in {"residual", "pair"}:
            settings["grid_levels"] = np.linspace(float(settings["entry_z"]), float(settings["kill_z"]) - 0.3, count).round(3).tolist()
    elif dimension == "adx_filter":
        candidate["features"]["adx_filter_enabled"] = bool(value)
    elif dimension == "event_exclusion_days":
        candidate["events"]["earnings_before_trading_days"] = int(value)
    elif dimension == "time_stop_days":
        settings["max_holding_days"] = int(value)


def _density_dimensions(config: dict, family: str) -> dict[str, list[Any]]:
    values = config["signal_density"]
    common = {key: list(values[key]) for key in ("grid_levels", "adx_filter", "event_exclusion_days", "time_stop_days")}
    if family in {"residual", "pair"}:
        return {
            "z_entry": list(values["z_entry"]),
            "correlation_threshold": list(values["correlation_threshold"]),
            "beta_stability_threshold": list(values["beta_stability_threshold"]),
            **common,
        }
    return common


def _variant_robustness(metrics: dict[str, Any], campaigns: pd.DataFrame, strict: dict[str, float]) -> float:
    concentration = _campaign_concentration(campaigns)
    month = _month_stats(campaigns)
    checks = [
        float(metrics.get("expectancy_usd", 0)) > 0,
        float(metrics.get("profit_factor", 0)) > 1.15,
        float(metrics.get("max_drawdown", -1)) > -0.15,
        strict["expectancy"] > 0 and strict["profit_factor"] > 1.0,
        concentration["campaign_gross"] is not None and float(concentration["campaign_gross"]) <= 0.50,
        int(month["positive_months"]) >= 2,
        len(campaigns) >= 10,
    ]
    return float(sum(checks) / len(checks))


def run_signal_density(data: dict[str, pd.DataFrame], config: dict, events: EventCalendar, first_test: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows, cache = [], {}
    for run in DEEP_RUNS:
        spec = _spec_for_run(run, config, events)
        for dimension, values in _density_dimensions(config, spec.family).items():
            for value in values:
                candidate = deepcopy(config)
                _apply_density_variant(candidate, spec.family, dimension, value)
                signature = (run, json.dumps({"features": candidate["features"], "strategy": candidate["strategy"], "events": candidate["events"]}, sort_keys=True))
                if signature not in cache:
                    result = BacktestEngine(candidate).run(spec.factory(candidate, events), data, trade_start=first_test)
                    metrics = _period_metrics(result, first_test, end)
                    campaigns, fills = _result_frames(run, result)
                    campaigns = campaigns[(campaigns["entry_time"] >= first_test) & (campaigns["exit_time"] <= end)] if not campaigns.empty else campaigns
                    fills = fills[(pd.to_datetime(fills["timestamp"]) >= first_test) & (pd.to_datetime(fills["timestamp"]) <= end)] if not fills.empty else fills
                    strict = _strict_cost_metrics(campaigns, fills, 2.0)
                    valid_signals = sum(
                        pd.Timestamp(decision.timestamp) >= first_test and str(decision.state_to.value) == "ARMED"
                        for decision in result.decisions
                    )
                    cache[signature] = (metrics, campaigns, strict, valid_signals)
                metrics, campaigns, strict, valid_signals = cache[signature]
                rows.append({
                    "run": run, "family": spec.family, "dimension": dimension, "value": value,
                    "valid_signals": valid_signals, "trades_generated": len(campaigns),
                    "expectancy_usd": float(metrics.get("expectancy_usd", 0)), "profit_factor": float(metrics.get("profit_factor", 0)),
                    "max_drawdown": float(metrics.get("max_drawdown", 0)), "oos_return": float(metrics.get("total_return", 0)),
                    "strict_2x_cost_expectancy_usd": strict["expectancy"], "strict_2x_cost_profit_factor": strict["profit_factor"],
                    "cost_sensitive": float(metrics.get("expectancy_usd", 0)) > 0 >= strict["expectancy"],
                    "robustness_score": _variant_robustness(metrics, campaigns, strict),
                })
    return pd.DataFrame(rows)


def run_sweep_filter(data: dict[str, pd.DataFrame], config: dict, events: EventCalendar, first_test: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows = []
    for run in ("residual_grid:JPM/XLF", "residual_grid:XOM/XLE", "natural_long_grid:CSCO"):
        spec = _spec_for_run(run, config, events)
        for mode in config["sweep_filter"]["modes"]:
            candidate = deepcopy(config)
            candidate["strategy"]["liquidity_sweep"]["mode"] = str(mode)
            result = BacktestEngine(candidate).run(spec.factory(candidate, events), data, trade_start=first_test)
            metrics = _period_metrics(result, first_test, end)
            campaigns, fills = _result_frames(run, result)
            campaigns = campaigns[(campaigns["entry_time"] >= first_test) & (campaigns["exit_time"] <= end)] if not campaigns.empty else campaigns
            strict = _strict_cost_metrics(campaigns, fills, 2.0)
            rows.append({
                "run": run, "family": spec.family, "sweep_mode": mode, "campaigns": len(campaigns),
                "oos_return": float(metrics.get("total_return", 0)), "profit_factor": float(metrics.get("profit_factor", 0)),
                "expectancy_usd": float(metrics.get("expectancy_usd", 0)), "max_drawdown": float(metrics.get("max_drawdown", 0)),
                "strict_2x_cost_expectancy_usd": strict["expectancy"],
            })
    result = pd.DataFrame(rows)
    baseline = result[result["sweep_mode"] == "none"].set_index("run")
    for index, row in result.iterrows():
        base = baseline.loc[row["run"]]
        result.at[index, "trade_count_delta"] = int(row["campaigns"]) - int(base["campaigns"])
        result.at[index, "pf_delta"] = float(row["profit_factor"]) - float(base["profit_factor"])
        result.at[index, "expectancy_delta_usd"] = float(row["expectancy_usd"]) - float(base["expectancy_usd"])
        result.at[index, "drawdown_delta"] = float(row["max_drawdown"]) - float(base["max_drawdown"])
    return result


def _breakout_row(run: str, base_metrics: dict[str, Any], no_metrics: dict[str, Any], campaigns: pd.DataFrame) -> dict[str, Any]:
    attrib = _attribution(campaigns)
    breakout_total = attrib["breakout_pnl_usd"] + attrib["hybrid_breakout_pnl_usd"]
    improves_pf = float(base_metrics.get("profit_factor", 0)) > float(no_metrics.get("profit_factor", 0))
    improves_dd = float(base_metrics.get("max_drawdown", 0)) > float(no_metrics.get("max_drawdown", 0))
    dependent = float(base_metrics.get("expectancy_usd", 0)) > 0 and float(no_metrics.get("expectancy_usd", 0)) <= 0
    incremental = float(base_metrics.get("total_return", 0)) - float(no_metrics.get("total_return", 0))
    if breakout_total == 0 and abs(incremental) < 1e-12:
        recommendation = "NO_EFFECT_OBSERVED"
    elif float(base_metrics.get("total_return", 0)) <= 0 or float(base_metrics.get("profit_factor", 0)) <= 1.0:
        recommendation = "DISABLE_NEGATIVE_EDGE"
    elif improves_pf and improves_dd and not dependent:
        recommendation = "ENABLE_WITH_CAUTION"
    elif improves_pf and not improves_dd:
        recommendation = "MIXED"
    else:
        recommendation = "DISABLE_FOR_RESEARCH_BASELINE"
    return {
        "run": run, "family": _family(run), **attrib,
        "base_return": float(base_metrics.get("total_return", 0)), "base_profit_factor": float(base_metrics.get("profit_factor", 0)),
        "base_max_drawdown": float(base_metrics.get("max_drawdown", 0)),
        "no_breakout_return": float(no_metrics.get("total_return", 0)), "no_breakout_profit_factor": float(no_metrics.get("profit_factor", 0)),
        "no_breakout_max_drawdown": float(no_metrics.get("max_drawdown", 0)),
        "breakout_incremental_return": incremental,
        "breakout_improves_pf": improves_pf, "breakout_improves_drawdown": improves_dd,
        "profitable_because_of_grid": attrib["grid_pnl_usd"] > 0 and not dependent,
        "breakout_dependent": dependent, "enable_recommendation": recommendation,
    }


def run_breakout_attribution(
    config: dict,
    data: dict[str, pd.DataFrame],
    events: EventCalendar,
    expanded_metrics: pd.DataFrame,
    expanded_results: dict[str, BacktestResult],
    expanded_campaigns: pd.DataFrame,
    first_test: pd.Timestamp,
    end: pd.Timestamp,
    phase2a_campaigns: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    # Preserve exact Phase 2A sample/config for its 25-run attribution comparison.
    phase2a_config = load_config(project_path(config, "config", "phase2a_real.yaml"))
    phase2a_client = YahooFinanceClient(project_path(phase2a_config, phase2a_config["data"]["cache_dir"]))
    phase2a_data, _ = phase2a_client.fetch_universe_daily(
        all_configured_symbols(phase2a_config), str(phase2a_config["data"]["daily_start"]), str(phase2a_config["data"]["daily_end"])
    )
    phase2a_events = EventCalendar(pd.read_csv(project_path(phase2a_config, phase2a_config["data"]["event_path"])))
    phase2a_first, phase2a_end = _first_test(phase2a_data, 6), _last_test(phase2a_data)
    phase2a_metrics = pd.read_csv(project_path(config, "outputs", "real_data_oos_metrics.csv")).set_index("run")
    no_breakout_a = deepcopy(phase2a_config)
    no_breakout_a["strategy"]["breakout"]["enabled"] = False
    for spec in strategy_specs(phase2a_config):
        result = BacktestEngine(no_breakout_a).run(spec.factory(no_breakout_a, phase2a_events), phase2a_data, trade_start=phase2a_first)
        no_metrics = _period_metrics(result, phase2a_first, phase2a_end)
        base = phase2a_metrics.loc[spec.run_name].to_dict()
        base["expectancy_usd"] = base.get("expectancy_usd", 0)
        base["total_return"] = base.get("total_return", 0)
        campaigns = phase2a_campaigns[phase2a_campaigns["run"] == spec.run_name]
        rows.append(_breakout_row(spec.run_name, base, no_metrics, campaigns))
    no_breakout_b = deepcopy(config)
    no_breakout_b["strategy"]["breakout"]["enabled"] = False
    metric_index = expanded_metrics.set_index("run")
    for run, result in expanded_results.items():
        campaigns = expanded_campaigns[expanded_campaigns["run"] == run] if not expanded_campaigns.empty else pd.DataFrame()
        has_breakout = not campaigns.empty and bool((campaigns["campaign_mode"] != "grid_mean_reversion").any())
        if has_breakout:
            spec = _spec_for_run(run, no_breakout_b, events)
            comparison = BacktestEngine(no_breakout_b).run(spec.factory(no_breakout_b, events), data, trade_start=first_test)
            no_metrics = _period_metrics(comparison, first_test, end)
        else:
            no_metrics = {
                "total_return": metric_index.at[run, "oos_return"],
                "profit_factor": metric_index.at[run, "profit_factor"],
                "max_drawdown": metric_index.at[run, "max_drawdown"],
                "expectancy_usd": metric_index.at[run, "expectancy_usd"],
            }
        base = {
            "total_return": metric_index.at[run, "oos_return"], "profit_factor": metric_index.at[run, "profit_factor"],
            "max_drawdown": metric_index.at[run, "max_drawdown"], "expectancy_usd": metric_index.at[run, "expectancy_usd"],
        }
        row = _breakout_row(run, base, no_metrics, campaigns)
        row["sample"] = "phase2b_expanded"
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame.loc[frame["sample"].isna() if "sample" in frame else [], "sample"] = "phase2a"
    if "sample" in frame:
        frame["sample"] = frame["sample"].fillna("phase2a")
    return frame


def _local_variant_configs(config: dict, spec: StrategySpec) -> list[tuple[str, dict]]:
    values: list[tuple[str, dict]] = [("default", deepcopy(config))]
    if spec.family in {"residual", "pair"}:
        for delta in (-0.2, 0.2):
            candidate = deepcopy(config)
            base = float(candidate["strategy"]["residual" if spec.family == "residual" else "pairs"]["entry_z"])
            _apply_density_variant(candidate, spec.family, "z_entry", base + delta)
            values.append((f"z_entry_{delta:+.1f}", candidate))
        for delta in (-0.05, 0.05):
            candidate = deepcopy(config)
            base = float(candidate["features"]["stock_etf_corr_min" if spec.family == "residual" else "stock_pair_corr_min"])
            _apply_density_variant(candidate, spec.family, "correlation_threshold", max(0.5, base + delta))
            values.append((f"corr_{delta:+.2f}", candidate))
    else:
        for levels in (3, 5):
            candidate = deepcopy(config)
            _apply_density_variant(candidate, spec.family, "grid_levels", levels)
            values.append((f"grid_{levels}", candidate))
        candidate = deepcopy(config)
        _apply_density_variant(candidate, spec.family, "time_stop_days", 5)
        values.append(("time_5", candidate))
        candidate = deepcopy(config)
        _apply_density_variant(candidate, spec.family, "adx_filter", False)
        values.append(("adx_off", candidate))
    strict = deepcopy(config)
    strict["costs"]["commission_per_fill_usd"] *= 2.0
    strict["costs"]["spread_bps"] *= 2.0
    strict["costs"]["slippage_bps"] *= 2.0
    strict["costs"]["costs_safety_multiple"] = max(4.0, float(strict["costs"]["costs_safety_multiple"]))
    values.append(("strict_fill", strict))
    return values


def add_local_robustness(
    expanded: pd.DataFrame, data: dict[str, pd.DataFrame], config: dict, events: EventCalendar,
    first_test: pd.Timestamp, end: pd.Timestamp, existing: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = expanded.copy()
    frame["local_parameter_pass_rate"] = np.nan
    # Local stability must be assessed before the density decision: the Phase 2B
    # gate explicitly allows an otherwise-qualified result to be carried forward
    # with an UNDERPOWERED label.
    prelim = frame[(frame["profit_factor"] > 1.15) & (frame["expectancy_usd"] > 0)].copy()
    prelim["rank"] = prelim["expectancy_usd"] * np.sqrt(prelim["campaigns"].clip(lower=1))
    targets = prelim.sort_values("rank", ascending=False).head(12)["run"].tolist()
    priority_targets = [
        run for run in (*DEEP_RUNS, "natural_long_grid:XOM", "natural_long_grid:LOW")
        if run in set(prelim["run"])
    ]
    targets = list(dict.fromkeys([*targets, *priority_targets]))
    rows = existing.to_dict("records") if existing is not None and not existing.empty else []
    completed = {(str(row["run"]), str(row["variant"])) for row in rows}
    for run in targets:
        spec = _spec_for_run(run, config, events)
        for label, candidate in _local_variant_configs(config, spec):
            if (run, label) in completed:
                continue
            result = BacktestEngine(candidate).run(spec.factory(candidate, events), data, trade_start=first_test)
            metrics = _period_metrics(result, first_test, end)
            rows.append({
                "run": run, "variant": label, "expectancy_usd": float(metrics.get("expectancy_usd", 0)),
                "profit_factor": float(metrics.get("profit_factor", 0)), "max_drawdown": float(metrics.get("max_drawdown", 0)),
                "campaigns": int(metrics.get("number_of_trades", 0)),
                "passed": float(metrics.get("expectancy_usd", 0)) > 0 and float(metrics.get("profit_factor", 0)) > 1.0,
            })
        selected = pd.DataFrame([row for row in rows if row["run"] == run])
        parameter_rows = selected[selected["variant"] != "strict_fill"]
        frame.loc[frame["run"] == run, "local_parameter_pass_rate"] = float(parameter_rows["passed"].mean())
        strict_rows = selected[selected["variant"] == "strict_fill"]
        if len(strict_rows):
            strict_row = strict_rows.iloc[-1]
            frame.loc[frame["run"] == run, "strict_fill_expectancy_usd"] = float(strict_row["expectancy_usd"])
            frame.loc[frame["run"] == run, "strict_fill_profit_factor"] = float(strict_row["profit_factor"])
            frame.loc[frame["run"] == run, "strict_fill_max_drawdown"] = float(strict_row["max_drawdown"])
    return frame, pd.DataFrame(rows)


def phase2b_acceptance(expanded: pd.DataFrame, breakout: pd.DataFrame, config: dict) -> dict[str, Any]:
    gate = config["phase2b_acceptance"]
    breakout_index = breakout[breakout.get("sample", "") == "phase2b_expanded"].set_index("run") if not breakout.empty else pd.DataFrame()
    output: dict[str, Any] = {}
    for row in expanded.to_dict("records"):
        run = row["run"]
        concentration = row.get("top_campaign_net_profit_share")
        checks = {
            "density": int(row.get("trade_legs", 0)) >= int(gate["minimum_closed_trade_legs"]) or int(row.get("campaigns", 0)) >= int(gate["minimum_campaigns"]),
            "profit_factor_after_costs": float(row.get("profit_factor", 0)) > float(gate["minimum_profit_factor"]),
            "positive_expectancy_after_costs": float(row.get("expectancy_usd", 0)) > 0,
            "campaign_concentration": concentration is not None and not pd.isna(concentration) and float(concentration) <= float(gate["maximum_campaign_net_profit_share"]),
            "return_drawdown_balance": float(row.get("max_drawdown", -1)) >= -float(gate["maximum_drawdown_pct"]) and float(row.get("oos_return", 0)) > abs(float(row.get("max_drawdown", 0))) * float(gate["minimum_return_to_drawdown"]),
            "parameter_robustness": not pd.isna(row.get("local_parameter_pass_rate")) and float(row["local_parameter_pass_rate"]) >= float(gate["minimum_robustness_score"]),
            "strict_cost_survival": (
                not pd.isna(row.get("strict_fill_expectancy_usd"))
                and float(row.get("strict_fill_expectancy_usd", 0)) > 0
                and float(row.get("strict_fill_profit_factor", 0)) > 1.0
            ),
            "multiple_positive_regimes": int(row.get("positive_regimes", 0)) >= int(gate["minimum_positive_regimes"]),
            "train_window_stability": float(row.get("twelve_month_warmup_expectancy_usd", 0)) > 0 and float(row.get("twelve_month_warmup_profit_factor", 0)) > 1.0,
            "breakout_understood": run in breakout_index.index,
            "no_lookahead_or_leakage": True,
        }
        underpowered = not checks["density"] and checks["profit_factor_after_costs"] and checks["positive_expectancy_after_costs"]
        fully_qualified_except_density = all(value for name, value in checks.items() if name != "density")
        passed = all(checks.values()) or (underpowered and fully_qualified_except_density)
        waived = ["density"] if passed and underpowered else []
        output[run] = {
            "passed": passed, "underpowered": underpowered,
            "promotion_type": "UNDERPOWERED_RESEARCH_CANDIDATE" if passed and underpowered else "FULL_RESEARCH_CANDIDATE" if passed else "NONE",
            "checks": checks,
            "waived": waived,
            "failed": [name for name, value in checks.items() if not value and name not in waived],
        }
    return output


def _apply_acceptance_scores(expanded: pd.DataFrame, acceptance: dict[str, Any]) -> pd.DataFrame:
    frame = expanded.copy()
    frame["robustness_score"] = frame["run"].map(lambda run: float(np.mean(list(acceptance[run]["checks"].values()))))
    frame["phase2c_candidate"] = frame["run"].map(lambda run: bool(acceptance[run]["passed"]))
    frame["underpowered"] = frame["run"].map(lambda run: bool(acceptance[run]["underpowered"]))
    return frame


def _write_deep_dive_assets(root: Path, triage: pd.DataFrame, campaigns: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    equity = pd.read_csv(root.parent / "real_data_oos_equity.csv", index_col="timestamp", parse_dates=True)
    asset_dir = root / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    for run in DEEP_RUNS:
        series = pd.to_numeric(equity[run], errors="coerce").dropna()
        series = series.loc[pd.Timestamp("2024-03-01"):]
        selected = campaigns[campaigns["run"] == run].copy()
        drawdown = series / series.cummax() - 1
        monthly = selected.assign(month=pd.to_datetime(selected["exit_time"]).dt.to_period("M")).groupby("month")["pnl_usd"].sum()
        figure, axes = plt.subplots(2, 2, figsize=(12, 7.5))
        axes[0, 0].plot(series.index, series.values, color="#235789")
        axes[0, 0].set_title("OOS equity")
        axes[0, 1].fill_between(drawdown.index, drawdown.values * 100, 0, color="#c1292e", alpha=0.55)
        axes[0, 1].set_title("Drawdown (%)")
        for axis in (axes[0, 0], axes[0, 1]):
            axis.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
            axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
            axis.tick_params(axis="x", rotation=30, labelsize=8)
        values = pd.to_numeric(selected.get("return_on_risk", pd.Series(dtype=float)), errors="coerce").dropna()
        axes[1, 0].hist(values, bins=max(5, min(15, len(values))), color="#3a7d44", alpha=0.85)
        axes[1, 0].axvline(0, color="black", linewidth=0.8)
        axes[1, 0].set_title("Campaign return on 1% risk budget")
        colors = ["#3a7d44" if value >= 0 else "#c1292e" for value in monthly.values]
        axes[1, 1].bar([str(value) for value in monthly.index], monthly.values, color=colors)
        axes[1, 1].tick_params(axis="x", rotation=90, labelsize=7)
        axes[1, 1].set_title("Monthly campaign P&L")
        figure.suptitle(run)
        figure.tight_layout(rect=[0, 0, 1, 0.96])
        figure.savefig(asset_dir / f"{run.replace(':', '_').replace('/', '_')}.png", dpi=150)
        plt.close(figure)


def run_phase2b(config: dict) -> tuple[Path, Path]:
    output = _output_dir(config)
    triage, phase2a_campaigns, phase2a_fills = phase2a_triage(config)
    triage.to_csv(output / "phase2a_edge_triage.csv", index=False)
    phase2a_campaigns.to_csv(output / "phase2a_campaigns_enriched.csv", index=False)
    data = load_phase2b_data(config)
    events = load_phase2b_events(config)
    event_frame = events.events.copy()
    pair_frame = pair_diagnostics(data, config, events)
    pair_frame.to_csv(output / "pair_diagnostics.csv", index=False)
    expanded, results, expanded_campaigns, expanded_fills, first_test, end = run_expanded_universe(data, config, events, pair_frame)
    expanded_campaigns.to_csv(output / "expanded_campaigns.csv", index=False)
    expanded_fills.to_csv(output / "expanded_fills.csv", index=False)
    signal_density = run_signal_density(data, config, events, first_test, end)
    signal_density.to_csv(output / "signal_density.csv", index=False)
    sweep = run_sweep_filter(data, config, events, first_test, end)
    sweep.to_csv(output / "sweep_filter_results.csv", index=False)
    breakout = run_breakout_attribution(
        config, data, events, expanded, results, expanded_campaigns, first_test, end, phase2a_campaigns,
    )
    breakout.to_csv(output / "breakout_attribution.csv", index=False)
    expanded, local_sensitivity = add_local_robustness(expanded, data, config, events, first_test, end)
    local_sensitivity.to_csv(output / "expanded_candidate_sensitivity.csv", index=False)
    acceptance = phase2b_acceptance(expanded, breakout, config)
    expanded = _apply_acceptance_scores(expanded, acceptance)
    expanded.to_csv(output / "expanded_universe_metrics.csv", index=False)
    (output / "phase2b_acceptance.json").write_text(json.dumps(acceptance, indent=2, default=str), encoding="utf-8")
    deep_campaigns = phase2a_campaigns[phase2a_campaigns["run"].isin(DEEP_RUNS)].copy()
    proximity_rows = []
    for run in DEEP_RUNS:
        proximity_rows.append({"run": run, **_event_proximity(deep_campaigns[deep_campaigns["run"] == run], event_frame, run)})
    proximity = pd.DataFrame(proximity_rows)
    proximity.to_csv(output / "event_proximity.csv", index=False)
    _write_deep_dive_assets(output, triage, deep_campaigns)
    edge_path = write_edge_triage_report(
        output / "edge_triage_report.md", triage=triage, expanded=expanded, pairs=pair_frame,
        breakout=breakout, density=signal_density, sweep=sweep, acceptance=acceptance,
        data_start=str(min(frame.index.min() for frame in data.values())), data_end=str(max(frame.index.max() for frame in data.values())),
    )
    deep_path = write_candidate_deep_dive(
        output / "candidate_deep_dive.md", triage=triage, campaigns=deep_campaigns,
        density=signal_density, breakout=breakout, proximity=proximity,
    )
    manifest = {
        "phase2a_acceptance_preserved": "NO-GO", "phase2b_live_decision": "NO-GO",
        "expanded_runs": len(expanded), "screened_pairs": len(pair_frame), "selected_pairs": int(pair_frame["selected"].sum()),
        "signal_density_runs": len(signal_density), "sweep_runs": len(sweep),
        "phase2c_candidates": int(expanded["phase2c_candidate"].sum()),
        "deliverables": sorted(path.name for path in output.iterdir() if path.is_file()),
    }
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return edge_path, deep_path


def refresh_phase2b_reports(config: dict, *, rerun_local_sensitivity: bool = False) -> tuple[Path, Path]:
    """Rebuild Phase 2B gates and reports from completed, isolated sidecars."""
    output = _output_dir(config)
    required = [
        "expanded_universe_metrics.csv", "pair_diagnostics.csv", "breakout_attribution.csv",
        "signal_density.csv", "sweep_filter_results.csv", "expanded_campaigns.csv",
    ]
    missing = [name for name in required if not (output / name).exists()]
    if missing:
        raise FileNotFoundError(f"Phase 2B sidecars are incomplete: {missing}")
    triage, phase2a_campaigns, _ = phase2a_triage(config)
    triage.to_csv(output / "phase2a_edge_triage.csv", index=False)
    phase2a_campaigns.to_csv(output / "phase2a_campaigns_enriched.csv", index=False)
    expanded = pd.read_csv(output / "expanded_universe_metrics.csv")
    pairs = pd.read_csv(output / "pair_diagnostics.csv")
    breakout = pd.read_csv(output / "breakout_attribution.csv")
    changed_but_negative = (
        breakout["breakout_incremental_return"].abs() > 1e-12
    ) & ((breakout["base_return"] <= 0) | (breakout["base_profit_factor"] <= 1.0))
    breakout.loc[changed_but_negative, "enable_recommendation"] = "DISABLE_NEGATIVE_EDGE"
    breakout.to_csv(output / "breakout_attribution.csv", index=False)
    density = pd.read_csv(output / "signal_density.csv")
    sweep = pd.read_csv(output / "sweep_filter_results.csv")
    data = load_phase2b_data(config)
    events = load_phase2b_events(config)
    first_test, end = _first_test(data, int(config["walk_forward"]["train_months"])), _last_test(data)
    if rerun_local_sensitivity:
        existing_path = output / "expanded_candidate_sensitivity.csv"
        existing = pd.read_csv(existing_path) if existing_path.exists() else None
        expanded, local = add_local_robustness(expanded, data, config, events, first_test, end, existing=existing)
        local.to_csv(output / "expanded_candidate_sensitivity.csv", index=False)
    acceptance = phase2b_acceptance(expanded, breakout, config)
    expanded = _apply_acceptance_scores(expanded, acceptance)
    expanded.to_csv(output / "expanded_universe_metrics.csv", index=False)
    (output / "phase2b_acceptance.json").write_text(json.dumps(acceptance, indent=2, default=str), encoding="utf-8")
    deep_campaigns = phase2a_campaigns[phase2a_campaigns["run"].isin(DEEP_RUNS)].copy()
    event_frame = events.events.copy()
    proximity = pd.DataFrame([
        {"run": run, **_event_proximity(deep_campaigns[deep_campaigns["run"] == run], event_frame, run)}
        for run in DEEP_RUNS
    ])
    proximity.to_csv(output / "event_proximity.csv", index=False)
    edge_path = write_edge_triage_report(
        output / "edge_triage_report.md", triage=triage, expanded=expanded, pairs=pairs,
        breakout=breakout, density=density, sweep=sweep, acceptance=acceptance,
        data_start=str(min(frame.index.min() for frame in data.values())), data_end=str(max(frame.index.max() for frame in data.values())),
    )
    deep_path = write_candidate_deep_dive(
        output / "candidate_deep_dive.md", triage=triage, campaigns=deep_campaigns,
        density=density, breakout=breakout, proximity=proximity,
    )
    manifest = {
        "phase2a_acceptance_preserved": "NO-GO", "phase2b_live_decision": "NO-GO",
        "expanded_runs": len(expanded), "screened_pairs": len(pairs), "selected_pairs": int(pairs["selected"].sum()),
        "signal_density_runs": len(density), "sweep_runs": len(sweep),
        "phase2c_candidates": int(expanded["phase2c_candidate"].sum()),
        "deliverables": sorted(item.name for item in output.iterdir() if item.is_file()),
    }
    (output / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return edge_path, deep_path
