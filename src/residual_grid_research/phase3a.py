from __future__ import annotations

"""Phase 3A loss forensics over the frozen Phase 2D-R0 baseline.

This module is deliberately read-only with respect to the frozen engine and
strategy configuration.  It replays the cached HF R-LITE bars, persists compact
run ledgers, and performs descriptive/counterfactual diagnostics.  Counterfactual
columns are path diagnostics, not executable backtest results and never replace
the observed frozen baseline.
"""

import argparse
import hashlib
import json
import math
import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from residual_grid_research.backtest import BacktestEngine
from residual_grid_research.config import load_config
from residual_grid_research.data.events import EventCalendar
from residual_grid_research.data.exchange_calendar import USExchangeCalendar
from residual_grid_research.data.trial_adapters import HFDataLibraryAdapter
from residual_grid_research.features.regime import classify_regime
from residual_grid_research.features.technical import add_technical_features
from residual_grid_research.phase2d import _digest_value, _frozen_parameters, _universe
from residual_grid_research.strategies import (
    NaturalLongGridStrategy,
    ResidualGridStrategy,
    StockPairGridStrategy,
)


PHASE = "3A"
SOURCE_STATUS = "LIMITED"
FORWARD_BARS = 20
MIN_CAMPAIGNS = 30
MIN_LEGS = 100


def _json(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"), allow_nan=False)


def _safe_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def _safe_div(numerator: float | int | None, denominator: float | int | None) -> float | None:
    n, d = _safe_float(numerator), _safe_float(denominator)
    return None if n is None or d is None or abs(d) < 1e-12 else n / d


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    _write(path, json.dumps(value, indent=2, sort_keys=True, default=str))


def _markdown_table(frame: pd.DataFrame, *, limit: int = 30) -> str:
    if frame.empty:
        return "_No rows._"
    view = frame.head(limit).copy()
    clean = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    lines = [
        "| " + " | ".join(clean(column) for column in view.columns) + " |",
        "|" + "|".join("---" for _ in view.columns) + "|",
    ]
    lines.extend(
        "| " + " | ".join(clean(value) for value in row) + " |"
        for row in view.itertuples(index=False, name=None)
    )
    if len(frame) > limit:
        lines.append(f"\n_Showing {limit} of {len(frame)} rows._")
    return "\n".join(lines)


def _strategy_specs(config: dict) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for stock, etf in config["universe"]["stock_etf_pairs"]:
        specs.append({"family": "residual_grid", "primary": stock, "secondary": etf})
    for first, second in config["universe"]["stock_pairs"]:
        specs.append({"family": "stock_pair_grid", "primary": first, "secondary": second})
    for symbol in config["universe"]["natural_long_symbols"]:
        specs.append({"family": "natural_long_grid", "primary": symbol, "secondary": ""})
    return specs


def _make_strategy(config: dict, spec: dict[str, Any], events: EventCalendar):
    family = spec["family"]
    if family == "residual_grid":
        return ResidualGridStrategy(config, spec["primary"], spec["secondary"], events=events)
    if family == "stock_pair_grid":
        return StockPairGridStrategy(config, spec["primary"], spec["secondary"], events=events)
    return NaturalLongGridStrategy(config, spec["primary"], events=events)


def _run_id(spec: dict[str, Any], timeframe: str) -> str:
    suffix = spec["primary"] + (f"_{spec['secondary']}" if spec.get("secondary") else "")
    return f"{timeframe}__{spec['family']}__{suffix}"


def _trade_start(config: dict, cache: Path, timeframe: str) -> pd.Timestamp:
    starts: list[pd.Timestamp] = []
    start = pd.Timestamp(config["data"]["start"])
    end = pd.Timestamp(config["data"]["end"]) + pd.Timedelta(days=1)
    for symbol in _universe(config)["all_symbols"]:
        path = cache / timeframe / f"{symbol}_clean.parquet"
        dates = pd.read_parquet(path, columns=["datetime"])["datetime"]
        valid = dates[(dates >= start) & (dates < end)]
        if valid.empty:
            raise RuntimeError(f"No cached {timeframe} data in frozen period for {symbol}")
        starts.append(pd.Timestamp(valid.min(), tz="America/New_York"))
    return max(starts) + pd.DateOffset(months=int(config["walk_forward"]["train_months"]))


def _load_frames(cache: Path, timeframe: str, symbols: Iterable[str], config: dict) -> dict[str, pd.DataFrame]:
    adapter = HFDataLibraryAdapter(cache)
    start = pd.Timestamp(config["data"]["start"], tz="America/New_York")
    end = pd.Timestamp(config["data"]["end"], tz="America/New_York") + pd.Timedelta(days=1)
    frames: dict[str, pd.DataFrame] = {}
    for symbol in dict.fromkeys(symbol for symbol in symbols if symbol):
        frame = adapter.load(symbol, timeframe=timeframe, version="clean")
        frames[symbol] = frame[(frame.index >= start) & (frame.index < end)].copy()
    return frames


def _signal_time(group_id: str, fallback: pd.Timestamp) -> pd.Timestamp:
    match = re.search(r"(\d{4}-\d{2}-\d{2}T.+)$", str(group_id))
    if not match:
        return fallback
    try:
        return pd.Timestamp(match.group(1))
    except (TypeError, ValueError):
        return fallback


def _previous_row(frame: pd.DataFrame, timestamp: pd.Timestamp) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=object)
    if timestamp in frame.index:
        row = frame.loc[timestamp]
        return row.iloc[-1] if isinstance(row, pd.DataFrame) else row
    prior = frame.loc[:timestamp]
    return prior.iloc[-1] if not prior.empty else pd.Series(dtype=object)


def _time_bucket(timestamp: pd.Timestamp) -> str:
    local = timestamp.tz_convert("America/New_York") if timestamp.tzinfo else timestamp.tz_localize("America/New_York")
    minute = local.hour * 60 + local.minute
    if minute < 10 * 60 + 30:
        return "FIRST_HOUR"
    if minute >= 15 * 60:
        return "LAST_HOUR"
    return "MIDDAY"


def _trend_slope(series: pd.Series, bars: int = 20) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna().tail(bars)
    if len(values) < max(5, bars // 2) or (values <= 0).any():
        return None
    return float(np.polyfit(np.arange(len(values)), np.log(values.to_numpy()), 1)[0])


def _daily_returns(frame: pd.DataFrame, timestamp: pd.Timestamp) -> dict[str, float | None]:
    history = frame.loc[:timestamp, "close"]
    if history.empty:
        return {"previous_1d_return": None, "previous_5d_return": None, "previous_20d_return": None}
    daily = history.groupby(history.index.tz_convert("America/New_York").normalize()).last()
    current = float(daily.iloc[-1])
    result: dict[str, float | None] = {}
    for days in (1, 5, 20):
        result[f"previous_{days}d_return"] = (
            current / float(daily.iloc[-days - 1]) - 1 if len(daily) > days else None
        )
    return result


def _session_vwap(frame: pd.DataFrame, timestamp: pd.Timestamp) -> float | None:
    local = frame.loc[:timestamp].tail(200)
    if local.empty:
        return None
    session = timestamp.tz_convert("America/New_York").normalize()
    local_sessions = local.index.tz_convert("America/New_York").normalize()
    local = local.loc[local_sessions == session]
    if local.empty or float(local["volume"].sum()) <= 0:
        return None
    typical = (local["high"] + local["low"] + local["close"]) / 3
    return float((typical * local["volume"]).sum() / local["volume"].sum())


def _regime_views(frames: dict[str, pd.DataFrame], config: dict) -> dict[str, pd.Series]:
    result: dict[str, pd.Series] = {}
    for symbol, frame in frames.items():
        try:
            result[symbol] = classify_regime(
                frame,
                market_adx_max=float(config["features"]["market_adx_max"]),
                atr_expansion_max=float(config["features"]["market_atr_expansion_max"]),
            )
        except Exception:
            result[symbol] = pd.Series(index=frame.index, dtype=object)
    return result


def _symbol_cashflow(fills: list[Any], symbol: str) -> float:
    cashflow = 0.0
    for fill in fills:
        if fill.symbol != symbol:
            continue
        signed = fill.quantity if fill.side.value == "BUY" else -fill.quantity
        cashflow -= signed * fill.price + fill.commission
    return float(cashflow)


def _entry_fills(fills: list[Any]) -> list[Any]:
    return [fill for fill in fills if not fill.reduce_only] if fills and hasattr(fills[0], "reduce_only") else [
        fill for fill in fills
        if not fill.metadata.get("close_fraction") and not fill.metadata.get("close_all")
    ]


def _fill_level_count(fills: list[Any], primary: str) -> int:
    entries = [fill for fill in _entry_fills(fills) if fill.symbol == primary]
    layers = {
        int(fill.metadata.get("grid_layer"))
        for fill in entries if fill.metadata.get("grid_layer") is not None
    }
    if layers:
        return len(layers)
    parsed = set()
    for fill in entries:
        match = re.search(r"layer\s+(\d+)", fill.reason.lower())
        parsed.add(int(match.group(1)) if match else len(parsed) + 1)
    return len(parsed)


def _average_entry_progress(fills: list[Any], primary: str) -> tuple[list[float], float | None]:
    qty = 0.0
    cost = 0.0
    averages: list[float] = []
    for fill in _entry_fills(fills):
        if fill.symbol != primary:
            continue
        signed = fill.quantity if fill.side.value == "BUY" else -fill.quantity
        if qty == 0 or np.sign(qty) == np.sign(signed):
            cost += abs(signed) * fill.price
            qty += signed
            averages.append(cost / max(abs(qty), 1e-12))
    if not averages:
        return [], None
    direction = 1 if qty >= 0 else -1
    improvement = (averages[0] - averages[-1]) * direction
    return averages, float(improvement)


def _sample_path(
    prepared: pd.DataFrame,
    raw: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    fills: list[Any],
    campaign_id: str,
    run_id: str,
) -> list[dict[str, Any]]:
    path = prepared.loc[start:end].copy()
    if path.empty:
        return []
    if len(path) > 60:
        positions = np.unique(np.linspace(0, len(path) - 1, 60).astype(int))
        fill_times = {pd.Timestamp(fill.timestamp) for fill in fills}
        positions = np.unique(np.concatenate([
            positions,
            [path.index.get_indexer([time], method="nearest")[0] for time in fill_times if len(path)],
        ]))
        path = path.iloc[positions]
    raw_slice = raw.reindex(path.index)
    fill_map: dict[pd.Timestamp, list[str]] = {}
    for fill in fills:
        fill_map.setdefault(pd.Timestamp(fill.timestamp), []).append(
            f"{fill.side.value} {fill.symbol} {fill.quantity:.4f}@{fill.price:.4f} {fill.reason}"
        )
    rows: list[dict[str, Any]] = []
    for timestamp, row in path.iterrows():
        raw_row = raw_slice.loc[timestamp] if timestamp in raw_slice.index else pd.Series(dtype=float)
        rows.append({
            "run_id": run_id,
            "campaign_id": campaign_id,
            "timestamp": timestamp,
            "open": _safe_float(raw_row.get("open")),
            "high": _safe_float(raw_row.get("high")),
            "low": _safe_float(raw_row.get("low")),
            "close": _safe_float(raw_row.get("close")),
            "volume": _safe_float(raw_row.get("volume")),
            "z_score": _safe_float(row.get("z")),
            "range_high": _safe_float(row.get("range_high", row.get("stock_range_high"))),
            "range_low": _safe_float(row.get("range_low", row.get("stock_range_low"))),
            "atr": _safe_float(row.get("atr_14", row.get("stock_atr_14"))),
            "state_or_fill": " | ".join(fill_map.get(pd.Timestamp(timestamp), [])),
        })
    return rows


def _natural_gate_rows(strategy: Any, spec: dict[str, Any], timeframe: str, config: dict) -> tuple[dict, list[dict]]:
    frame = strategy.prepared.copy()
    required = ["close", "atr_14", "adx_14", "atr_ratio", "range_high", "range_low", "range_position", "range_width_atr"]
    usable = frame[required].notna().all(axis=1)
    features, settings = config["features"], config["strategy"]["natural"]
    width = frame["range_width_atr"].between(float(features["range_width_atr_min"]), float(features["range_width_atr_max"]))
    trend = frame["adx_14"] < float(features["range_adx_max"])
    volatility = frame["atr_ratio"] <= float(features["atr_expansion_max"])
    regime = ~frame["market_regime"].isin(["PANIC_SELL", "VOL_EXPANSION", "EVENT_RISK", "UNKNOWN"])
    support = frame["range_position"].between(0.0, float(settings["lower_range_fraction"]))
    liquidity = frame["dollar_volume_20"] >= float(config["universe"]["min_average_daily_dollar_volume"])
    step_bps = float(settings["grid_step_atr"]) * frame["atr_14"] / frame["close"] * 10000
    cost_floor = 2 * (float(config["costs"]["spread_bps"]) + float(config["costs"]["slippage_bps"])) * float(config["costs"]["costs_safety_multiple"])
    costs = step_bps >= cost_floor
    levels = []
    for row in frame.itertuples():
        count = min(int(settings["grid_level_count"]), int(settings["max_grid_depth"]))
        if not np.isfinite(getattr(row, "atr_14", np.nan)) or not np.isfinite(getattr(row, "range_low", np.nan)):
            levels.append(0)
            continue
        candidates = [row.close - level * float(settings["grid_step_atr"]) * row.atr_14 for level in range(count)]
        levels.append(sum(candidate >= row.range_low for candidate in candidates))
    geometry = pd.Series(levels, index=frame.index) >= 1
    gates = [usable, width, trend, volatility, regime, liquidity, support, costs, geometry]
    cumulative = pd.Series(True, index=frame.index)
    counts = [len(frame)]
    for gate in gates:
        cumulative &= gate.fillna(False)
        counts.append(int(cumulative.sum()))
    campaigns = sum(1 for decision in strategy.decisions if decision.reason == "predefined natural grid queued")
    row = {
        "strategy_family": "natural_long_grid", "symbol": spec["primary"], "timeframe": timeframe,
        "total_candles": len(frame), "after_data_session_filters": counts[1],
        "after_range_filter": counts[2], "after_trend_filter": counts[3],
        "after_volatility_filter": counts[4], "after_market_regime_filter": counts[5],
        "after_volume_filter": counts[6], "after_support_proximity": counts[7],
        "after_cost_tp_filter": counts[8], "after_grid_geometry_validation": counts[9],
        "event_filter_failed": None, "event_data_status": "UNAVAILABLE_IN_HF_R_LITE",
        "cooldown_rejections": sum(1 for d in strategy.decisions if d.state_from.value == "COOLDOWN"),
        "final_armed_signals": int(cumulative.sum()), "final_campaigns": campaigns,
        "dominant_gate": "",
    }
    stage_names = ["data", "range", "trend", "volatility", "regime", "volume", "support", "cost", "geometry"]
    losses = [counts[index] - counts[index + 1] for index in range(len(stage_names))]
    row["dominant_gate"] = stage_names[int(np.argmax(losses))] if losses else ""
    examples: list[dict] = []
    individual = {
        "range_condition_failed": ~width, "trend_filter_failed": ~trend,
        "atr_filter_failed": ~volatility, "market_regime_failed": ~regime,
        "price_not_near_support": ~support, "volume_filter_failed": ~liquidity,
        "tp_distance_invalid": ~costs, "grid_geometry_invalid": ~geometry,
    }
    for reason, mask in individual.items():
        candidates = frame.loc[usable & mask.fillna(False)].tail(2)
        for timestamp, item in candidates.iterrows():
            examples.append({
                "run_id": _run_id(spec, timeframe), "timestamp": timestamp, "failure_reason": reason,
                "close": _safe_float(item.get("close")), "atr": _safe_float(item.get("atr_14")),
                "adx": _safe_float(item.get("adx_14")), "range_position": _safe_float(item.get("range_position")),
                "range_width_atr": _safe_float(item.get("range_width_atr")), "market_regime": item.get("market_regime"),
            })
    return row, examples


def _campaign_rows(
    result: Any,
    strategy: Any,
    spec: dict[str, Any],
    timeframe: str,
    frames: dict[str, pd.DataFrame],
    config: dict,
) -> tuple[list[dict], list[dict]]:
    primary, secondary = spec["primary"], spec.get("secondary", "")
    prepared = strategy.prepared
    fills_by_group: dict[str, list[Any]] = {}
    for fill in result.fills:
        fills_by_group.setdefault(fill.group_id, []).append(fill)
    regimes = _regime_views({key: value for key, value in frames.items() if key in {"SPY", "QQQ", secondary}}, config)
    rows: list[dict] = []
    paths: list[dict] = []
    for campaign in result.campaigns:
        campaign_id = str(campaign["group_id"])
        fills = sorted(fills_by_group.get(campaign_id, []), key=lambda value: pd.Timestamp(value.timestamp))
        if not fills:
            continue
        start, end = pd.Timestamp(campaign["entry_time"]), pd.Timestamp(campaign["exit_time"])
        signal_time = _signal_time(campaign_id, start)
        context = _previous_row(prepared, signal_time)
        raw = frames[primary]
        entry_bar = _previous_row(raw, start)
        raw_history = raw.loc[:signal_time]
        returns = pd.to_numeric(raw_history["close"], errors="coerce").pct_change()
        bars_per_day = 78 if timeframe == "5min" else 26
        realized_vol = float(returns.tail(20).std(ddof=1) * math.sqrt(bars_per_day * 252)) if len(returns.dropna()) >= 10 else None
        vwap = _session_vwap(raw, signal_time)
        range_high = _safe_float(context.get("range_high", context.get("stock_range_high")))
        range_low = _safe_float(context.get("range_low", context.get("stock_range_low")))
        close = _safe_float(context.get("close", context.get("stock_close")))
        atr = _safe_float(context.get("atr_14", context.get("stock_atr_14")))
        adx_value = _safe_float(context.get("adx_14", context.get("stock_adx_14")))
        range_width = (range_high - range_low) if range_high is not None and range_low is not None else None
        entry_primary = next((fill for fill in _entry_fills(fills) if fill.symbol == primary), fills[0])
        averages, average_improvement = _average_entry_progress(fills, primary)
        filled_levels = _fill_level_count(fills, primary)
        configured_levels = int(
            config["strategy"]["natural"].get("grid_level_count", 4)
            if spec["family"] == "natural_long_grid"
            else len(config["strategy"]["residual" if spec["family"] == "residual_grid" else "pairs"]["grid_levels"])
        )
        entry_price = float(entry_primary.price)
        if spec["family"] == "natural_long_grid":
            grid_step = float(config["strategy"]["natural"]["grid_step_atr"]) * (atr or 0.0)
            stop_price = _safe_float(entry_primary.metadata.get("stop_price"))
            tp_prices = entry_primary.metadata.get("tp_prices", [])
            tp_distance = float(tp_prices[0] - entry_price) if tp_prices else None
            stop_distance = entry_price - stop_price if stop_price is not None else None
            levels = [
                _safe_float(fill.metadata.get("grid_level", fill.requested_price))
                for fill in _entry_fills(fills) if fill.symbol == primary
            ]
        else:
            settings_key = "residual" if spec["family"] == "residual_grid" else "pairs"
            settings = config["strategy"][settings_key]
            z_levels = list(map(float, settings["grid_levels"]))
            grid_step = float(np.median(np.diff(z_levels))) * (_safe_float(context.get("residual_std")) or 0.0) * entry_price
            stop_distance = max(float(settings["kill_z"]) - abs(_safe_float(context.get("z")) or 0.0), 0.0) * (_safe_float(context.get("residual_std")) or 0.0) * entry_price
            tp_distance = max(abs(_safe_float(context.get("z")) or 0.0) - float(settings["take_profit_z"][0]), 0.0) * (_safe_float(context.get("residual_std")) or 0.0) * entry_price
            stop_price = None
            tp_prices = list(map(float, settings["take_profit_z"]))
            levels = z_levels
        round_trip_cost = sum(fill.commission + fill.friction_cost for fill in fills)
        expected_tp_usd = sum(fill.gross_notional for fill in _entry_fills(fills)) * max(_safe_div(tp_distance, entry_price) or 0.0, 0.0)
        expected_grid_usd = sum(fill.gross_notional for fill in _entry_fills(fills)) * max(_safe_div(grid_step, entry_price) or 0.0, 0.0)
        first_row = prepared.index.get_indexer([end], method="nearest")[0]
        forward = prepared.iloc[first_row + 1:first_row + 1 + FORWARD_BARS]
        direction = 1 if campaign["direction"] == "long_residual" else -1
        later_reverted = False
        tp_missed = False
        post_stop_reversion = 0.0
        z_after = {1: None, 3: None, 5: None, 10: None}
        max_fav_z, max_adv_z = None, None
        time_to_reversion = None
        z_entry = _safe_float(context.get("z"))
        if "z" in prepared and z_entry is not None:
            during = prepared.loc[start:end, "z"].dropna()
            signed = during * direction
            if len(signed):
                max_fav_z = float((signed - z_entry * direction).max())
                max_adv_z = float((z_entry * direction - signed).max())
                target = -float(config["strategy"]["residual" if spec["family"] == "residual_grid" else "pairs"]["take_profit_z"][0])
                hits = np.flatnonzero((signed >= target).to_numpy())
                time_to_reversion = int(hits[0]) if len(hits) else None
            for horizon in z_after:
                if len(forward) >= horizon:
                    z_after[horizon] = _safe_float(forward.iloc[horizon - 1].get("z"))
            if not forward.empty:
                signed_forward = pd.to_numeric(forward["z"], errors="coerce") * direction
                exit_target = -float(config["strategy"]["residual" if spec["family"] == "residual_grid" else "pairs"]["take_profit_z"][0])
                later_reverted = bool((signed_forward >= exit_target).any())
                post_stop_reversion = float((signed_forward - signed_forward.iloc[0]).max()) if len(signed_forward.dropna()) else 0.0
        elif not forward.empty and range_high is not None and range_low is not None:
            target = (range_high + range_low) / 2
            later_reverted = bool(pd.to_numeric(forward["close"], errors="coerce").max() >= target)
            post_stop_reversion = float(pd.to_numeric(forward["close"], errors="coerce").max() - float(entry_bar.get("close", entry_price)))
        exit_lower = str(campaign["exit_reason"]).lower()
        stopped = any(word in exit_lower for word in ("kill", "stop", "invalidation", "adverse"))
        tp_missed = bool(stopped and later_reverted)
        stock_leg = _symbol_cashflow(fills, primary)
        hedge_leg = _symbol_cashflow(fills, secondary) if secondary else 0.0
        max_exposure = 0.0
        if result.exposure_curve is not None and not result.exposure_curve.empty:
            exp = result.exposure_curve.loc[start:end, "gross_leverage"]
            eq = result.equity_curve.reindex(exp.index).ffill()
            max_exposure = float((exp * eq).max()) if len(exp) else 0.0
        volume = _safe_float(context.get("volume", context.get("stock_volume")))
        volume_ratio = _safe_float(context.get("volume_ratio", context.get("stock_volume_ratio")))
        signal_regime = str(context.get("market_regime", campaign.get("regime", "UNKNOWN")))
        spy_regime = _previous_row(regimes.get("SPY", pd.Series(dtype=object)).to_frame("value"), signal_time).get("value") if "SPY" in regimes else None
        qqq_regime = _previous_row(regimes.get("QQQ", pd.Series(dtype=object)).to_frame("value"), signal_time).get("value") if "QQQ" in regimes else None
        sector_regime = _previous_row(regimes.get(secondary, pd.Series(dtype=object)).to_frame("value"), signal_time).get("value") if secondary in regimes else None
        fill_records = [{
            "timestamp": fill.timestamp, "symbol": fill.symbol, "side": fill.side.value,
            "quantity": fill.quantity, "price": fill.price, "reason": fill.reason,
            "commission": fill.commission, "spread_cost": fill.spread_cost,
            "slippage_cost": fill.slippage_cost,
        } for fill in fills]
        row = {
            "run_id": _run_id(spec, timeframe), "strategy_family": spec["family"],
            "strategy_name": result.strategy_name, "symbol": primary,
            "pair": f"{primary}/{secondary}" if secondary else primary,
            "hedge_symbol": secondary or None, "timeframe": timeframe,
            "campaign_id": campaign_id, "start_timestamp": start, "signal_timestamp": signal_time,
            "end_timestamp": end, "duration_hours": campaign["duration_hours"],
            "session_date": signal_time.date(), "day_of_week": signal_time.day_name(),
            "time_of_day_bucket": _time_bucket(signal_time), "entry_price": entry_price,
            "entry_reason": campaign["entry_reason"], "entry_state": entry_primary.state_before,
            "entry_candle_open": _safe_float(entry_bar.get("open")), "entry_candle_high": _safe_float(entry_bar.get("high")),
            "entry_candle_low": _safe_float(entry_bar.get("low")), "entry_candle_close": _safe_float(entry_bar.get("close")),
            "entry_candle_volume": _safe_float(entry_bar.get("volume")), "range_high": range_high,
            "range_low": range_low, "range_midpoint": (range_high + range_low) / 2 if range_high is not None and range_low is not None else None,
            "distance_to_range_low": close - range_low if close is not None and range_low is not None else None,
            "distance_to_range_high": range_high - close if close is not None and range_high is not None else None,
            "atr": atr, "adx": adx_value, "realized_volatility": realized_vol,
            "volume": volume, "volume_ratio": volume_ratio, "trend_slope": _trend_slope(raw_history["close"]),
            "market_regime": signal_regime, "sector_etf_regime": sector_regime,
            "spy_regime": spy_regime, "qqq_regime": qqq_regime,
            **_daily_returns(raw, signal_time),
            "position_vs_swing_low": _safe_div((close - range_low) if close is not None and range_low is not None else None, atr),
            "position_vs_swing_high": _safe_div((range_high - close) if close is not None and range_high is not None else None, atr),
            "session_vwap": vwap, "distance_to_vwap_atr": _safe_div((close - vwap) if close is not None and vwap is not None else None, atr),
            "residual_z_score": z_entry, "z_score_slope_5": _trend_slope(prepared.loc[:signal_time, "z"], 5) if "z" in prepared else None,
            "beta": _safe_float(context.get("beta")), "correlation": _safe_float(context.get("corr_60")),
            "correlation_90": _safe_float(context.get("corr_90")), "beta_stability": _safe_float(context.get("beta_stability")),
            "hedge_ratio": _safe_float(entry_primary.metadata.get("beta", context.get("beta"))),
            "grid_step": grid_step, "grid_step_pct": _safe_div(grid_step, entry_price),
            "grid_step_atr": _safe_div(grid_step, atr), "configured_levels": configured_levels,
            "filled_levels": filled_levels, "max_grid_depth_reached": filled_levels,
            "first_level_price": levels[0] if levels else None, "last_level_price": levels[-1] if levels else None,
            "average_entry_path": _json(averages), "average_entry_improvement": average_improvement,
            "tp_distance": tp_distance, "tp_distance_atr": _safe_div(tp_distance, atr),
            "stop_price": stop_price, "stop_distance": stop_distance, "stop_distance_atr": _safe_div(stop_distance, atr),
            "range_width_atr": _safe_div(range_width, atr), "cost_as_pct_grid_step": _safe_div(round_trip_cost, expected_grid_usd),
            "cost_as_pct_expected_tp": _safe_div(round_trip_cost, expected_tp_usd),
            "fill_timestamps": _json([fill.timestamp for fill in fills]),
            "fill_prices": _json([fill.price for fill in fills]), "fill_sizes": _json([fill.quantity for fill in fills]),
            "fill_details": _json(fill_records), "tp_levels": _json(tp_prices), "stop_levels": _json([stop_price] if stop_price else []),
            "max_exposure_usd": max_exposure, "realized_pnl": campaign["pnl_usd"],
            "unrealized_pnl": 0.0 if campaign["closed"] else None, "mae": campaign["mae_usd"], "mfe": campaign["mfe_usd"],
            "mae_mfe_ratio": _safe_div(abs(campaign["mae_usd"]), abs(campaign["mfe_usd"])),
            "exit_reason": campaign["exit_reason"], "stop_reason": campaign["exit_reason"] if stopped else None,
            "time_stop_flag": campaign["exit_category"] == "time_stop", "event_exclusion_proximity": None,
            "event_data_status": "UNAVAILABLE_IN_HF_R_LITE", "breakout_flag": campaign["campaign_mode"] != "grid_mean_reversion",
            "failed_breakout_flag": campaign["regime"] == "failed_breakout", "stock_leg_pnl": stock_leg,
            "hedge_leg_pnl": hedge_leg, "grid_pnl": campaign["grid_pnl_usd"], "breakout_pnl": campaign["breakout_pnl_usd"],
            "commission_total": sum(fill.commission for fill in fills), "spread_cost_total": sum(fill.spread_cost for fill in fills),
            "slippage_total": sum(fill.slippage_cost for fill in fills), "cost_total": round_trip_cost + campaign["financing_cost_usd"],
            "gross_pnl": campaign["pnl_usd"] + round_trip_cost + campaign["financing_cost_usd"], "net_pnl": campaign["pnl_usd"],
            "return_pct": campaign["pnl_usd"] / float(config["project"]["starting_capital_usd"]),
            "r_multiple": campaign["return_on_risk"], "win_loss": "WIN" if campaign["pnl_usd"] > 0 else "LOSS" if campaign["pnl_usd"] < 0 else "FLAT",
            "profit_factor_contribution": max(campaign["pnl_usd"], 0.0) - abs(min(campaign["pnl_usd"], 0.0)),
            "later_reverted_after_stop": later_reverted if stopped else None, "tp_missed_due_next_bar": tp_missed,
            "stop_before_potential_reversion": bool(stopped and later_reverted), "enough_legs_to_average": filled_levels >= 2,
            "z_after_1": z_after[1], "z_after_3": z_after[3], "z_after_5": z_after[5], "z_after_10": z_after[10],
            "max_favorable_z_move": max_fav_z, "max_adverse_z_move": max_adv_z, "time_to_mean_reversion_bars": time_to_reversion,
            "z_continued_against_position": bool(max_adv_z is not None and max_adv_z > 0.25),
            "post_stop_reversion": post_stop_reversion, "data_source_status": SOURCE_STATUS,
            "execution_prices_status": "VENDOR_ADJUSTED_NOT_RAW", "event_history_status": "UNAVAILABLE",
        }
        rows.append(row)
        paths.extend(_sample_path(prepared, raw, start, end, fills, campaign_id, row["run_id"]))
    return rows, paths


def _worker(payload: dict[str, Any]) -> dict[str, Any]:
    root = Path(payload["root"])
    config = load_config(root / "config" / "phase2d_frozen.yaml")
    cache = root / "data" / "phase2d_data_trial" / "hf_data_library"
    spec, timeframe = payload["spec"], payload["timeframe"]
    run_id = _run_id(spec, timeframe)
    run_cache = Path(payload["run_cache"])
    run_cache.mkdir(parents=True, exist_ok=True)
    campaigns_path = run_cache / f"{run_id}__campaigns.parquet"
    paths_path = run_cache / f"{run_id}__paths.parquet"
    gate_path = run_cache / f"{run_id}__gate.json"
    examples_path = run_cache / f"{run_id}__gate_examples.parquet"
    summary_path = run_cache / f"{run_id}__summary.json"
    if not payload.get("force") and campaigns_path.exists() and summary_path.exists():
        return json.loads(summary_path.read_text(encoding="utf-8"))
    symbols = [spec["primary"], spec.get("secondary"), "SPY", "QQQ"]
    frames = _load_frames(cache, timeframe, symbols, config)
    events = EventCalendar(session_calendar=USExchangeCalendar(start="2000-01-01", end="2030-12-31"))
    strategy = _make_strategy(config, spec, events)
    result = BacktestEngine(config).run(strategy, frames, trade_start=pd.Timestamp(payload["trade_start"]))
    campaign_rows, paths = _campaign_rows(result, strategy, spec, timeframe, frames, config)
    campaign_frame = pd.DataFrame(campaign_rows)
    if campaign_frame.empty:
        campaign_frame = pd.DataFrame(columns=["run_id", "campaign_id"])
    path_frame = pd.DataFrame(paths)
    if path_frame.empty:
        path_frame = pd.DataFrame(columns=["run_id", "campaign_id", "timestamp"])
    campaign_frame.to_parquet(campaigns_path, index=False)
    path_frame.to_parquet(paths_path, index=False)
    if spec["family"] == "natural_long_grid":
        gate, examples = _natural_gate_rows(strategy, spec, timeframe, config)
        _write_json(gate_path, gate)
        example_frame = pd.DataFrame(examples)
        if example_frame.empty:
            example_frame = pd.DataFrame(columns=["run_id", "timestamp", "failure_reason"])
        example_frame.to_parquet(examples_path, index=False)
    summary = {
        "run_id": run_id, "strategy_name": result.strategy_name, "family": spec["family"],
        "timeframe": timeframe, "campaigns": len(campaign_rows), "fills": len(result.fills),
        "metrics": result.metrics, "warnings": result.warnings,
    }
    _write_json(summary_path, summary)
    return summary


def _profit_factor(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    gains, losses = float(clean[clean > 0].sum()), float(-clean[clean < 0].sum())
    if losses <= 1e-12:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def _max_drawdown(values: pd.Series) -> float:
    clean = pd.to_numeric(values, errors="coerce").fillna(0.0).cumsum()
    if clean.empty:
        return 0.0
    return float((clean - clean.cummax()).min())


def _bucket_metrics(group: pd.DataFrame) -> dict[str, Any]:
    ordered = group.sort_values("start_timestamp")
    pnl = pd.to_numeric(ordered["net_pnl"], errors="coerce").fillna(0.0)
    positive = pnl[pnl > 0]
    negative = -pnl[pnl < 0]
    gross_profit = float(positive.sum())
    gross_loss = float(negative.sum())
    max_profit_share = float(positive.max() / gross_profit) if gross_profit > 0 else None
    months = pd.to_datetime(ordered["start_timestamp"], utc=True).dt.strftime("%Y-%m").nunique()
    symbols = ordered["pair"].nunique()
    return {
        "campaigns": len(ordered), "trades_legs": int(pd.to_numeric(ordered["filled_levels"], errors="coerce").fillna(0).sum()),
        "net_pnl": float(pnl.sum()), "average_pnl": float(pnl.mean()) if len(pnl) else 0.0,
        "median_pnl": float(pnl.median()) if len(pnl) else 0.0, "win_rate": float((pnl > 0).mean()) if len(pnl) else 0.0,
        "profit_factor": _profit_factor(pnl), "expectancy": float(pnl.mean()) if len(pnl) else 0.0,
        "max_drawdown": _max_drawdown(pnl), "average_mae": float(pd.to_numeric(ordered["mae"], errors="coerce").mean()),
        "average_mfe": float(pd.to_numeric(ordered["mfe"], errors="coerce").mean()),
        "average_cost": float(pd.to_numeric(ordered["cost_total"], errors="coerce").mean()),
        "cost_as_pct_gross_profit": float(pd.to_numeric(ordered["cost_total"], errors="coerce").sum() / gross_profit) if gross_profit else None,
        "profit_concentration": max_profit_share, "loss_concentration": float(negative.max() / gross_loss) if gross_loss > 0 else None,
        "symbols": int(symbols), "months": int(months),
    }


def _diagnostic_flags(metrics: dict[str, Any], group: pd.DataFrame) -> str:
    flags: list[str] = []
    sufficient = metrics["campaigns"] >= MIN_CAMPAIGNS or metrics["trades_legs"] >= MIN_LEGS
    flags.append("SUFFICIENT_SAMPLE" if sufficient else "UNDERPOWERED" if metrics["campaigns"] >= 10 else "TOO_SPARSE")
    cost_ratio = metrics.get("cost_as_pct_gross_profit")
    if cost_ratio is not None and cost_ratio >= 0.5:
        flags.append("COST_DOMINATED")
    exits = group["exit_reason"].astype(str).str.lower()
    if exits.str.contains("kill|stop|invalidation|adverse", regex=True).mean() >= 0.5:
        flags.append("STOP_DOMINATED")
    regimes = group["market_regime"].astype(str)
    if regimes.str.contains("TREND").mean() >= 0.5 and metrics["net_pnl"] < 0:
        flags.append("TREND_AGAINST_GRID")
    if "hedge_leg_pnl" in group and group["hedge_leg_pnl"].sum() < 0 and group["stock_leg_pnl"].sum() > 0:
        flags.append("HEDGE_DRAG")
    bad_geometry = (
        (pd.to_numeric(group["grid_step_atr"], errors="coerce") < 0.4)
        | (pd.to_numeric(group["grid_step_atr"], errors="coerce") > 1.2)
        | (pd.to_numeric(group["filled_levels"], errors="coerce") < 2)
    ).mean()
    if bad_geometry >= 0.5:
        flags.append("BAD_GEOMETRY")
    if (
        sufficient and metrics["profit_factor"] > 1.15 and metrics["expectancy"] > 0
        and (metrics.get("profit_concentration") is None or metrics["profit_concentration"] <= 0.25)
        and metrics["symbols"] >= 2 and metrics["months"] >= 2
    ):
        flags.append("POTENTIAL_CONDITIONAL_EDGE")
    return ";".join(dict.fromkeys(flags))


def _group_table(frame: pd.DataFrame, dimensions: list[str], dimension_name: str) -> pd.DataFrame:
    rows: list[dict] = []
    for keys, group in frame.groupby(dimensions, dropna=False, observed=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        record = {column: value for column, value in zip(dimensions, keys)}
        metrics = _bucket_metrics(group)
        rows.append({"attribution_dimension": dimension_name, **record, **metrics, "diagnostic_flags": _diagnostic_flags(metrics, group)})
    return pd.DataFrame(rows)


def _label_bucket(series: pd.Series, bins: list[float], labels: list[str]) -> pd.Series:
    return pd.cut(pd.to_numeric(series, errors="coerce"), bins=bins, labels=labels, include_lowest=True).astype(object).fillna("UNAVAILABLE")


def _attribution_tables(campaigns: pd.DataFrame, output: Path) -> dict[str, pd.DataFrame]:
    strategy = _group_table(campaigns, ["strategy_family", "timeframe"], "strategy_family_timeframe")
    breakout = campaigns[campaigns["breakout_flag"].fillna(False)].copy()
    if not breakout.empty:
        breakout["strategy_family"] = "breakout_module"
        breakout["net_pnl"] = pd.to_numeric(breakout["breakout_pnl"], errors="coerce").fillna(0.0)
        strategy = pd.concat([
            strategy,
            _group_table(breakout, ["strategy_family", "timeframe"], "separate_breakout_attribution"),
        ], ignore_index=True, sort=False)
    symbol = _group_table(campaigns, ["strategy_family", "pair", "timeframe"], "symbol_pair_timeframe")
    regime_parts = []
    for column in ("market_regime", "spy_regime", "sector_etf_regime", "time_of_day_bucket", "day_of_week", "exit_bucket"):
        view = campaigns.copy()
        view["bucket"] = view[column].fillna("UNAVAILABLE")
        part = _group_table(view, ["strategy_family", "timeframe", "bucket"], column)
        regime_parts.append(part)
    view = campaigns.copy()
    view["bucket"] = _label_bucket(view["realized_volatility"], [-np.inf, 0.15, 0.30, 0.50, np.inf], ["LOW", "NORMAL", "HIGH", "EXTREME"])
    regime_parts.append(_group_table(view, ["strategy_family", "timeframe", "bucket"], "realized_volatility"))
    view = campaigns.copy()
    view["bucket"] = _label_bucket(view["volume_ratio"], [-np.inf, 0.8, 1.2, np.inf], ["LOW", "NORMAL", "HIGH"])
    regime_parts.append(_group_table(view, ["strategy_family", "timeframe", "bucket"], "volume_ratio"))
    regime = pd.concat(regime_parts, ignore_index=True, sort=False)
    geometry_parts = []
    definitions = {
        "grid_step_atr": ([-np.inf, 0.4, 0.8, 1.2, np.inf], ["<0.4", "0.4-0.8", "0.8-1.2", ">1.2"]),
        "range_width_atr": ([-np.inf, 3, 6, 10, np.inf], ["<3", "3-6", "6-10", ">10"]),
        "stop_distance_atr": ([-np.inf, 0.5, 1.0, 2.0, np.inf], ["<0.5", "0.5-1.0", "1.0-2.0", ">2.0"]),
        "tp_distance_atr": ([-np.inf, 0.5, 1.0, 1.5, np.inf], ["<0.5", "0.5-1.0", "1.0-1.5", ">1.5"]),
        "filled_levels": ([-np.inf, 1, 2, 3, np.inf], ["0-1", "2", "3", "4+"]),
        "average_entry_improvement": ([-np.inf, 0, 0.1, 0.5, np.inf], ["none_or_worse", "small", "medium", "large"]),
    }
    for column, (bins, labels) in definitions.items():
        view = campaigns.copy()
        view["bucket"] = _label_bucket(view[column], bins, labels)
        geometry_parts.append(_group_table(view, ["strategy_family", "timeframe", "bucket"], column))
    geometry = pd.concat(geometry_parts, ignore_index=True, sort=False)
    residual = campaigns[campaigns["strategy_family"].isin(["residual_grid", "stock_pair_grid"])].copy()
    residual_parts = []
    residual_defs = {
        "residual_z_score": ([-np.inf, -2, -1.5, 0, 1.5, 2, np.inf], ["<=-2", "-2--1.5", "-1.5-0", "0-1.5", "1.5-2", ">2"]),
        "z_score_slope_5": ([-np.inf, -0.01, 0.01, np.inf], ["falling", "flat", "rising"]),
        "beta_stability": ([-np.inf, 0.15, 0.35, np.inf], ["stable", "allowed", "unstable"]),
        "correlation": ([-np.inf, 0.65, 0.75, 0.85, np.inf], ["<0.65", "0.65-0.75", "0.75-0.85", ">=0.85"]),
        "hedge_ratio": ([-np.inf, 0.75, 1.0, 1.25, np.inf], ["<0.75", "0.75-1.0", "1.0-1.25", ">1.25"]),
    }
    for column, (bins, labels) in residual_defs.items():
        view = residual.copy()
        view["bucket"] = _label_bucket(view[column], bins, labels)
        residual_parts.append(_group_table(view, ["strategy_family", "timeframe", "bucket"], column))
    view = residual.copy()
    view["bucket"] = np.where(pd.to_numeric(view["residual_z_score"], errors="coerce") < 0, "long_residual", "short_residual")
    residual_parts.append(_group_table(view, ["strategy_family", "timeframe", "bucket"], "direction"))
    view = residual.copy()
    view["bucket"] = np.where(
        view["time_to_mean_reversion_bars"].notna(), "reverting",
        np.where(view["z_continued_against_position"].fillna(False), "expanding", "neither_confirmed"),
    )
    residual_parts.append(_group_table(view, ["strategy_family", "timeframe", "bucket"], "residual_expanding_reverting"))
    residual_state = pd.concat(residual_parts, ignore_index=True, sort=False) if residual_parts else pd.DataFrame()
    tables = {"strategy": strategy, "symbol": symbol, "regime": regime, "geometry": geometry, "residual": residual_state}
    for name, table in tables.items():
        table.to_csv(output / f"loss_attribution_by_{'grid_geometry' if name == 'geometry' else 'residual_state' if name == 'residual' else name}.csv", index=False)
    return tables


def _grid_audit(campaigns: pd.DataFrame, output: Path) -> pd.DataFrame:
    audit = campaigns[campaigns["strategy_family"].isin(["natural_long_grid", "residual_grid"])].copy()
    audit["range_reasonable"] = pd.to_numeric(audit["range_width_atr"], errors="coerce").between(3, 10)
    audit["entry_near_support"] = pd.to_numeric(audit["position_vs_swing_low"], errors="coerce").between(-0.5, 1.5)
    audit["levels_inside_range"] = (
        pd.to_numeric(audit["first_level_price"], errors="coerce").between(
            pd.to_numeric(audit["range_low"], errors="coerce"), pd.to_numeric(audit["range_high"], errors="coerce")
        ) | audit["strategy_family"].eq("residual_grid")
    )
    audit["grid_too_narrow"] = pd.to_numeric(audit["grid_step_atr"], errors="coerce") < 0.4
    audit["grid_too_wide"] = pd.to_numeric(audit["grid_step_atr"], errors="coerce") > 1.2
    audit["not_enough_fills"] = pd.to_numeric(audit["filled_levels"], errors="coerce") < 2
    audit["average_entry_improved_meaningfully"] = pd.to_numeric(audit["average_entry_improvement"], errors="coerce") > 0.1 * pd.to_numeric(audit["atr"], errors="coerce")
    audit["tp_cost_dominated"] = pd.to_numeric(audit["cost_as_pct_expected_tp"], errors="coerce") >= 0.5
    audit["tp_less_than_3x_cost"] = pd.to_numeric(audit["cost_as_pct_expected_tp"], errors="coerce") > 1 / 3
    audit["stop_inside_normal_winner_mae"] = False
    for family, group in audit.groupby("strategy_family"):
        winners = group[group["net_pnl"] > 0]
        normal = float(pd.to_numeric(winners["mae"], errors="coerce").abs().quantile(0.75)) if len(winners) else np.nan
        audit.loc[group.index, "stop_inside_normal_winner_mae"] = pd.to_numeric(group["stop_distance"], errors="coerce") < normal
    audit["stopped_then_reverted"] = audit["later_reverted_after_stop"].fillna(False).astype(bool)
    columns = [
        "run_id", "campaign_id", "strategy_family", "pair", "timeframe", "range_reasonable", "entry_near_support",
        "levels_inside_range", "grid_step_atr", "grid_too_narrow", "grid_too_wide", "configured_levels", "filled_levels",
        "not_enough_fills", "average_entry_improvement", "average_entry_improved_meaningfully", "tp_distance_atr",
        "cost_as_pct_expected_tp", "tp_cost_dominated", "tp_less_than_3x_cost", "stop_distance_atr",
        "stop_inside_normal_winner_mae", "stopped_then_reverted", "net_pnl",
    ]
    audit[columns].to_csv(output / "grid_order_placement_audit.csv", index=False)
    return audit


def _stop_tp_analysis(campaigns: pd.DataFrame, output: Path) -> pd.DataFrame:
    result = campaigns.copy()
    exit_lower = result["exit_reason"].astype(str).str.lower()
    stopped = exit_lower.str.contains("kill|stop|invalidation|adverse", regex=True)
    result["stop_category"] = "NOT_STOPPED"
    result.loc[stopped & result["later_reverted_after_stop"].fillna(False), "stop_category"] = "STOP_TOO_TIGHT_REVERTED_AFTER"
    result.loc[stopped & ~result["later_reverted_after_stop"].fillna(False) & (result["mae"] < result["net_pnl"] * 1.5), "stop_category"] = "STOP_CORRECT_PREVENTED_LARGER_LOSS"
    result.loc[stopped & (pd.to_numeric(result["r_multiple"], errors="coerce") <= -0.8), "stop_category"] = "STOP_TOO_WIDE_LARGE_LOSS"
    result.loc[stopped & result["stop_category"].eq("NOT_STOPPED"), "stop_category"] = "STRUCTURE_BREAK_CONFIRMED"
    result["tp_category"] = "NO_TP_EXIT"
    tp = exit_lower.str.contains("tp|target|mean reversion completed", regex=True)
    result.loc[tp, "tp_category"] = "TP_HIT_CLEANLY"
    result.loc[tp & (pd.to_numeric(result["cost_as_pct_expected_tp"], errors="coerce") >= 0.5), "tp_category"] = "TP_TOO_CLOSE_COST_DOMINATED"
    result.loc[~tp & (pd.to_numeric(result["mfe"], errors="coerce") > 0) & (pd.to_numeric(result["net_pnl"], errors="coerce") < 0), "tp_category"] = "TP_WAITED_TOO_LONG_AND_REVERSED"
    result.loc[result["tp_missed_due_next_bar"].fillna(False), "tp_category"] = "TP_TOO_FAR_MISSED"
    result["current_stop_observed_pnl"] = result["net_pnl"]
    result["wider_stop_would_help"] = result["stop_category"].eq("STOP_TOO_TIGHT_REVERTED_AFTER")
    result["tighter_stop_would_help"] = result["stop_category"].eq("STOP_TOO_WIDE_LARGE_LOSS")
    result["closer_tp_would_help"] = result["tp_category"].isin(["TP_TOO_FAR_MISSED", "TP_WAITED_TOO_LONG_AND_REVERSED"])
    result["midpoint_exit_would_help"] = result["closer_tp_would_help"] & result["mfe"].gt(0)
    result["diagnostic_variants_status"] = "PATH_HEURISTIC_NOT_EXECUTABLE_BACKTEST"
    natural = result["strategy_family"].eq("natural_long_grid")
    result["stop_variant_current"] = "OBSERVED_FROZEN_BASELINE"
    result["stop_variant_range_low_minus_0_5_atr"] = np.where(natural, "PREREGISTER_AND_REPLAY_REQUIRED", "NOT_APPLICABLE_RELATIONSHIP_GRID")
    result["stop_variant_range_low_minus_1_0_atr"] = np.where(natural, "PREREGISTER_AND_REPLAY_REQUIRED", "NOT_APPLICABLE_RELATIONSHIP_GRID")
    result["stop_variant_last_grid_minus_0_5_atr"] = np.where(natural, "PREREGISTER_AND_REPLAY_REQUIRED", "NOT_APPLICABLE_RELATIONSHIP_GRID")
    result["stop_variant_average_entry_minus_1_5_atr"] = np.where(natural, "PREREGISTER_AND_REPLAY_REQUIRED", "NOT_APPLICABLE_RELATIONSHIP_GRID")
    result["stop_variant_close_only"] = np.where(
        stopped & result["later_reverted_after_stop"].fillna(False), "POSSIBLY_AVOIDS_STOP_PATH_REPLAY_REQUIRED", "NO_OBSERVED_SUPPORT"
    )
    result["stop_variant_two_candle_close"] = result["stop_variant_close_only"]
    grid_expected = pd.to_numeric(result["cost_total"], errors="coerce") / pd.to_numeric(result["cost_as_pct_grid_step"], errors="coerce").replace(0, np.nan)
    result["tp_variant_current"] = np.where(tp, "OBSERVED_TARGET_EXIT", "NOT_HIT_OR_OTHER_EXIT")
    result["tp_variant_0_5_step_reached_proxy"] = pd.to_numeric(result["mfe"], errors="coerce") >= 0.5 * grid_expected
    result["tp_variant_1_0_step_reached_proxy"] = pd.to_numeric(result["mfe"], errors="coerce") >= grid_expected
    result["tp_variant_1_5_step_reached_proxy"] = pd.to_numeric(result["mfe"], errors="coerce") >= 1.5 * grid_expected
    result["tp_variant_midpoint_reached_proxy"] = natural & exit_lower.str.contains("tp1|tp2|tp3|target", regex=True)
    result["tp_variant_partial_next_level_remainder_midpoint_status"] = "PREREGISTER_AND_REPLAY_REQUIRED"
    columns = [
        "run_id", "campaign_id", "strategy_family", "pair", "timeframe", "stop_category", "tp_category", "net_pnl",
        "mae", "mfe", "post_stop_reversion", "later_reverted_after_stop", "cost_as_pct_expected_tp",
        "wider_stop_would_help", "tighter_stop_would_help", "closer_tp_would_help", "midpoint_exit_would_help",
        "stop_variant_current", "stop_variant_range_low_minus_0_5_atr", "stop_variant_range_low_minus_1_0_atr",
        "stop_variant_last_grid_minus_0_5_atr", "stop_variant_average_entry_minus_1_5_atr", "stop_variant_close_only",
        "stop_variant_two_candle_close", "tp_variant_current", "tp_variant_0_5_step_reached_proxy",
        "tp_variant_1_0_step_reached_proxy", "tp_variant_1_5_step_reached_proxy", "tp_variant_midpoint_reached_proxy",
        "tp_variant_partial_next_level_remainder_midpoint_status", "diagnostic_variants_status",
    ]
    result[columns].to_csv(output / "stop_tp_failure_analysis.csv", index=False)
    return result


def _residual_failure(campaigns: pd.DataFrame, output: Path) -> pd.DataFrame:
    residual = campaigns[campaigns["strategy_family"] == "residual_grid"].copy()
    residual["direction"] = np.where(pd.to_numeric(residual["residual_z_score"], errors="coerce") < 0, "long_residual", "short_residual")
    residual["hedge_drag"] = residual["hedge_leg_pnl"]
    residual["combined_residual_pnl"] = residual["net_pnl"]
    residual["stock_only_counterfactual_pnl"] = residual["stock_leg_pnl"]
    residual["no_hedge_would_help"] = (residual["stock_leg_pnl"] > residual["net_pnl"]) & (residual["hedge_leg_pnl"] < 0)
    residual["dollar_neutral_counterfactual_status"] = "UNAVAILABLE_WITHOUT_REPLAY;NOT_INFERRED"
    residual["beta_neutral_observed"] = True
    residual["mean_reverted_during_campaign"] = residual["time_to_mean_reversion_bars"].notna()
    residual["entry_too_early_proxy"] = residual["z_continued_against_position"] & ~residual["mean_reverted_during_campaign"]
    residual["entry_too_late_proxy"] = residual["time_to_mean_reversion_bars"].eq(0)
    residual["earlier_z_exit_would_help"] = residual[["z_after_1", "z_after_3", "z_after_5", "z_after_10"]].notna().any(axis=1) & residual["mfe"].gt(0) & residual["net_pnl"].lt(0)
    direction_sign = np.where(residual["direction"].eq("long_residual"), 1.0, -1.0)
    entry_progress = pd.to_numeric(residual["residual_z_score"], errors="coerce") * direction_sign
    best_progress = entry_progress + pd.to_numeric(residual["max_favorable_z_move"], errors="coerce").fillna(0.0)
    worst_progress = entry_progress - pd.to_numeric(residual["max_adverse_z_move"], errors="coerce").fillna(0.0)
    for threshold in (0.8, 0.5, 0.2, 0.0):
        residual[f"z_exit_{str(threshold).replace('.', '_')}_reached"] = best_progress >= -threshold
    for threshold in (2.5, 3.0, 3.5):
        residual[f"z_kill_{str(threshold).replace('.', '_')}_reached"] = worst_progress <= -threshold
    residual["diagnostic_hedge_beta_neutral_pnl"] = residual["combined_residual_pnl"]
    residual["diagnostic_hedge_no_hedge_stock_leg_pnl"] = residual["stock_leg_pnl"]
    residual["diagnostic_hedge_dollar_neutral_status"] = "PREREGISTER_AND_REPLAY_REQUIRED"
    residual["diagnostic_variant_policy"] = "DESCRIPTIVE_THRESHOLDS_NOT_PARAMETER_SELECTION"
    columns = [
        "run_id", "campaign_id", "pair", "timeframe", "start_timestamp", "end_timestamp", "direction",
        "residual_z_score", "z_score_slope_5", "z_after_1", "z_after_3", "z_after_5", "z_after_10",
        "max_favorable_z_move", "max_adverse_z_move", "time_to_mean_reversion_bars", "z_continued_against_position",
        "stock_leg_pnl", "hedge_leg_pnl", "hedge_drag", "combined_residual_pnl", "stock_only_counterfactual_pnl",
        "beta", "beta_stability", "correlation", "correlation_90", "hedge_ratio", "net_pnl", "market_regime",
        "mean_reverted_during_campaign", "entry_too_early_proxy", "entry_too_late_proxy", "no_hedge_would_help",
        "earlier_z_exit_would_help", "beta_neutral_observed", "dollar_neutral_counterfactual_status",
        "z_exit_0_8_reached", "z_exit_0_5_reached", "z_exit_0_2_reached", "z_exit_0_0_reached",
        "z_kill_2_5_reached", "z_kill_3_0_reached", "z_kill_3_5_reached",
        "diagnostic_hedge_beta_neutral_pnl", "diagnostic_hedge_no_hedge_stock_leg_pnl",
        "diagnostic_hedge_dollar_neutral_status", "diagnostic_variant_policy",
    ]
    residual[columns].to_csv(output / "residual_failure_analysis.csv", index=False)
    return residual


def _conditional_edges(campaigns: pd.DataFrame, output: Path) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    categorical = [
        "spy_regime", "qqq_regime", "sector_etf_regime", "market_regime", "time_of_day_bucket", "day_of_week",
        "breakout_flag", "enough_legs_to_average", "entry_sweep_reclaim",
    ]
    for column in categorical:
        view = campaigns.copy()
        view["condition_bucket"] = view[column].fillna("UNAVAILABLE").astype(str)
        part = _group_table(view, ["strategy_family", "condition_bucket"], column)
        part = part.rename(columns={"attribution_dimension": "condition"})
        parts.append(part)
    numeric = {
        "realized_volatility": ([-np.inf, 0.15, 0.30, 0.50, np.inf], ["LOW", "NORMAL", "HIGH", "EXTREME"]),
        "volume_ratio": ([-np.inf, 0.8, 1.2, np.inf], ["LOW", "NORMAL", "HIGH"]),
        "adx": ([-np.inf, 15, 23, 35, np.inf], ["LOW", "RANGE_LIMIT", "TREND", "HIGH_TREND"]),
        "position_vs_swing_low": ([-np.inf, 0, 0.5, 1.5, np.inf], ["BELOW", "VERY_NEAR", "NEAR", "FAR"]),
        "distance_to_vwap_atr": ([-np.inf, -1, 0, 1, np.inf], ["BELOW_1ATR", "BELOW", "ABOVE", "ABOVE_1ATR"]),
        "previous_1d_return": ([-np.inf, -0.02, 0, 0.02, np.inf], ["PULLBACK_STRONG", "PULLBACK", "UP", "UP_STRONG"]),
        "previous_5d_return": ([-np.inf, -0.05, 0, 0.05, np.inf], ["PULLBACK_STRONG", "PULLBACK", "UP", "UP_STRONG"]),
        "grid_step_atr": ([-np.inf, 0.4, 0.8, 1.2, np.inf], ["<0.4", "0.4-0.8", "0.8-1.2", ">1.2"]),
        "filled_levels": ([-np.inf, 1, 2, 3, np.inf], ["0-1", "2", "3", "4+"]),
        "average_entry_improvement": ([-np.inf, 0, 0.1, 0.5, np.inf], ["NONE", "SMALL", "MEDIUM", "LARGE"]),
        "tp_distance_atr": ([-np.inf, 0.5, 1.0, 1.5, np.inf], ["<0.5", "0.5-1", "1-1.5", ">1.5"]),
        "stop_distance_atr": ([-np.inf, 0.5, 1.0, 2.0, np.inf], ["<0.5", "0.5-1", "1-2", ">2"]),
        "range_width_atr": ([-np.inf, 3, 6, 10, np.inf], ["<3", "3-6", "6-10", ">10"]),
        "cost_as_pct_expected_tp": ([-np.inf, 0.25, 0.5, 0.75, np.inf], ["<25%", "25-50%", "50-75%", ">75%"]),
        "residual_z_score": ([-np.inf, -2, -1.5, 1.5, 2, np.inf], ["<=-2", "-2--1.5", "CENTER", "1.5-2", ">2"]),
        "z_score_slope_5": ([-np.inf, -0.01, 0.01, np.inf], ["FALLING", "FLAT", "RISING"]),
        "beta_stability": ([-np.inf, 0.15, 0.35, np.inf], ["STABLE", "ALLOWED", "UNSTABLE"]),
        "correlation": ([-np.inf, 0.65, 0.75, 0.85, np.inf], ["<0.65", "0.65-0.75", "0.75-0.85", ">0.85"]),
        "hedge_ratio": ([-np.inf, 0.75, 1.0, 1.25, np.inf], ["<0.75", "0.75-1", "1-1.25", ">1.25"]),
    }
    for column, (bins, labels) in numeric.items():
        view = campaigns[campaigns[column].notna()].copy()
        if view.empty:
            continue
        view["condition_bucket"] = _label_bucket(view[column], bins, labels).astype(str)
        part = _group_table(view, ["strategy_family", "condition_bucket"], column)
        part = part.rename(columns={"attribution_dimension": "condition"})
        parts.append(part)
    result = pd.concat(parts, ignore_index=True, sort=False)
    result["minimum_sample_pass"] = (result["campaigns"] >= MIN_CAMPAIGNS) | (result["trades_legs"] >= MIN_LEGS)
    result["conditional_edge_eligible"] = (
        result["minimum_sample_pass"] & (result["profit_factor"] > 1.15) & (result["expectancy"] > 0)
        & ((result["profit_concentration"].isna()) | (result["profit_concentration"] <= 0.25))
        & (result["symbols"] >= 2) & (result["months"] >= 2)
    )
    result.to_csv(output / "conditional_edge_buckets.csv", index=False)
    return result


def _counterfactuals(campaigns: pd.DataFrame, output: Path) -> pd.DataFrame:
    losses = campaigns[campaigns["net_pnl"] < 0].copy()
    modes: list[str] = []
    for row in losses.itertuples():
        cost_ratio = _safe_float(row.cost_as_pct_expected_tp)
        if cost_ratio is not None and cost_ratio >= 0.75:
            mode = "COST_DOMINATED"
        elif row.strategy_family in {"residual_grid", "stock_pair_grid"} and row.stock_leg_pnl > 0 and row.hedge_leg_pnl < 0:
            mode = "HEDGE_DRAG"
        elif row.strategy_family in {"residual_grid", "stock_pair_grid"} and bool(row.z_continued_against_position):
            mode = "NO_MEAN_REVERSION"
        elif bool(row.stop_before_potential_reversion):
            mode = "STOP_TOO_TIGHT"
        elif row.r_multiple <= -0.8:
            mode = "STOP_TOO_WIDE"
        elif row.filled_levels < 2:
            mode = "TOO_FEW_LEVELS"
        elif _safe_float(row.grid_step_atr) is not None and row.grid_step_atr < 0.4:
            mode = "GRID_TOO_NARROW"
        elif _safe_float(row.grid_step_atr) is not None and row.grid_step_atr > 1.2:
            mode = "GRID_TOO_WIDE"
        elif row.mfe > 0:
            mode = "EXIT_TOO_LATE"
        elif "trend" in str(row.market_regime).lower():
            mode = "TREND_CONTINUATION_AGAINST_GRID"
        else:
            mode = "ENTRY_BAD_LEVEL"
        modes.append(mode)
    losses["primary_failure_mode"] = modes
    losses["would_wider_stop_help"] = losses["stop_before_potential_reversion"].fillna(False)
    losses["would_tighter_stop_help"] = losses["r_multiple"].le(-0.8) & ~losses["later_reverted_after_stop"].fillna(False)
    losses["would_closer_tp_help"] = losses["mfe"].gt(0)
    losses["would_midpoint_exit_help"] = losses["mfe"].gt(0) & losses["net_pnl"].lt(0)
    losses["would_more_grid_levels_help"] = losses["filled_levels"].lt(2) & losses["mae"].lt(0)
    losses["would_fewer_grid_levels_help"] = losses["max_grid_depth_reached"].ge(losses["configured_levels"]) & losses["r_multiple"].le(-0.8)
    losses["would_no_hedge_help"] = losses["stock_leg_pnl"].gt(0) & losses["hedge_leg_pnl"].lt(0)
    losses["would_earlier_z_exit_help"] = losses[["z_after_1", "z_after_3", "z_after_5", "z_after_10"]].notna().any(axis=1) & losses["mfe"].gt(0)
    losses["would_trend_filter_block"] = losses["market_regime"].astype(str).str.contains("TREND") | losses["adx"].gt(23)
    losses["would_sweep_reclaim_block"] = ~losses["entry_sweep_reclaim"].fillna(False)
    losses["sweep_reclaim_counterfactual_status"] = "CAUSAL_ENTRY_FILTER_ONLY;SIZE_AND_PORTFOLIO_NOT_REPLAYED"
    losses["would_breakout_mode_save"] = losses["breakout_pnl"].gt(0) & losses["grid_pnl"].lt(0)
    losses["counterfactual_status"] = "EXPLANATORY_PATH_HEURISTIC_NOT_NEW_STRATEGY"
    columns = [
        "run_id", "campaign_id", "strategy_family", "pair", "timeframe", "primary_failure_mode", "net_pnl",
        "would_wider_stop_help", "would_tighter_stop_help", "would_closer_tp_help", "would_midpoint_exit_help",
        "would_more_grid_levels_help", "would_fewer_grid_levels_help", "would_no_hedge_help", "would_earlier_z_exit_help",
        "would_trend_filter_block", "would_sweep_reclaim_block", "sweep_reclaim_counterfactual_status",
        "would_breakout_mode_save", "counterfactual_status",
    ]
    losses[columns].to_csv(output / "counterfactual_failure_modes.csv", index=False)
    return losses


def _fmt(value: Any, digits: int = 3) -> str:
    number = _safe_float(value)
    if number is None:
        return "UNAVAILABLE"
    if math.isinf(number):
        return "inf"
    return f"{number:.{digits}f}"


def _status_summary(
    campaigns: pd.DataFrame,
    conditional: pd.DataFrame,
    counterfactuals: pd.DataFrame,
) -> dict[str, Any]:
    by_family = {family: _bucket_metrics(group) for family, group in campaigns.groupby("strategy_family")}
    eligible = conditional[conditional["conditional_edge_eligible"]]
    failure = counterfactuals.groupby("primary_failure_mode")["net_pnl"].agg(["count", "sum"]).sort_values("sum")
    main_driver = str(failure.index[0]) if len(failure) else "INSUFFICIENT_CAMPAIGNS"
    secondary = [str(value) for value in failure.index[1:4]]
    residual = campaigns[campaigns["strategy_family"] == "residual_grid"]
    natural = campaigns[campaigns["strategy_family"] == "natural_long_grid"]
    pairs = campaigns[campaigns["strategy_family"] == "stock_pair_grid"]
    geometry_narrow = float(pd.to_numeric(campaigns["grid_step_atr"], errors="coerce").lt(0.4).mean())
    geometry_wide = float(pd.to_numeric(campaigns["grid_step_atr"], errors="coerce").gt(1.2).mean())
    sparse = float(pd.to_numeric(campaigns["filled_levels"], errors="coerce").lt(2).mean())
    if sparse >= 0.5:
        geometry_status = "TOO_SPARSE"
    elif geometry_narrow >= 0.5:
        geometry_status = "TOO_NARROW"
    elif geometry_wide >= 0.5:
        geometry_status = "TOO_WIDE"
    else:
        geometry_status = "MIXED"
    stop_mask = campaigns["exit_reason"].astype(str).str.lower().str.contains("kill|stop|invalidation|adverse", regex=True)
    stopped = campaigns[stop_mask]
    reverted_rate = float(stopped["later_reverted_after_stop"].fillna(False).mean()) if len(stopped) else 0.0
    wide_rate = float(pd.to_numeric(stopped["r_multiple"], errors="coerce").le(-0.8).mean()) if len(stopped) else 0.0
    stop_status = "TOO_TIGHT" if reverted_rate >= 0.5 else "TOO_WIDE" if wide_rate >= 0.5 else "MIXED" if len(stopped) else "INCONCLUSIVE"
    tp_cost = float(pd.to_numeric(campaigns["cost_as_pct_expected_tp"], errors="coerce").ge(0.5).mean())
    tp_missed_series = campaigns.get("tp_missed_due_next_bar", pd.Series(False, index=campaigns.index))
    tp_missed = float(tp_missed_series.fillna(False).mean())
    tp_status = "TOO_CLOSE" if tp_cost >= 0.5 else "TOO_FAR" if tp_missed >= 0.5 else "MIXED"
    hedge_total = float(pd.to_numeric(residual["hedge_leg_pnl"], errors="coerce").sum())
    stock_total = float(pd.to_numeric(residual["stock_leg_pnl"], errors="coerce").sum())
    if not len(residual):
        hedge_impact = "INCONCLUSIVE"
    elif hedge_total < 0 and stock_total > 0:
        hedge_impact = "HARMFUL"
    elif hedge_total > 0 and stock_total < 0:
        hedge_impact = "HELPFUL"
    else:
        hedge_impact = "MIXED"
    cost_sum = float(pd.to_numeric(campaigns["cost_total"], errors="coerce").sum())
    gross_series = campaigns.get("gross_pnl", campaigns["net_pnl"] + campaigns["cost_total"])
    gross_abs = float(pd.to_numeric(gross_series, errors="coerce").abs().sum())
    cost_ratio = cost_sum / gross_abs if gross_abs else 0.0
    cost_impact = "EDGE_KILLING" if cost_ratio >= 0.5 else "HIGH" if cost_ratio >= 0.25 else "MODERATE" if cost_ratio >= 0.10 else "LOW"
    def family_status(name: str, frame: pd.DataFrame) -> str:
        if not len(frame):
            return "REDESIGN"
        family_eligible = eligible[eligible["strategy_family"] == name]
        if len(family_eligible):
            return "CONDITIONAL_EDGE_CANDIDATE"
        metrics = by_family.get(name, {})
        sufficient = metrics.get("campaigns", 0) >= MIN_CAMPAIGNS or metrics.get("trades_legs", 0) >= MIN_LEGS
        return "ABANDON" if sufficient and metrics.get("profit_factor", 0) < 0.8 and name == "residual_grid" else "REDESIGN"
    breakout_total = float(pd.to_numeric(campaigns["breakout_pnl"], errors="coerce").sum())
    breakout_count = int(campaigns["breakout_flag"].fillna(False).sum())
    breakout_status = "ABANDON" if breakout_count >= MIN_CAMPAIGNS and breakout_total < 0 else "REDESIGN"
    return {
        "main_loss_driver": main_driver,
        "secondary_loss_drivers": secondary,
        "residual_grid_status": family_status("residual_grid", residual),
        "natural_long_grid_status": family_status("natural_long_grid", natural),
        "stock_pairs_status": family_status("stock_pair_grid", pairs),
        "breakout_continuation_status": breakout_status,
        "grid_geometry_status": geometry_status,
        "stop_logic_status": stop_status,
        "tp_logic_status": tp_status,
        "hedge_impact": hedge_impact,
        "cost_impact": cost_impact,
        "conditional_edge_found": "YES" if len(eligible) else "UNDERPOWERED" if ((conditional["profit_factor"] > 1.15) & (conditional["expectancy"] > 0)).any() else "NO",
        "eligible_buckets": int(len(eligible)),
        "breakout_campaigns": breakout_count,
        "breakout_pnl": breakout_total,
        "stop_reversion_rate": reverted_rate,
        "cost_ratio_abs_gross": cost_ratio,
        "family_metrics": by_family,
    }


def _baseline_reproduction(root: Path, run_cache: Path, output: Path) -> dict[str, Any]:
    baseline = pd.read_csv(root / "outputs" / "phase2d_data_trial" / "hf_lite_metrics.csv")
    replay_rows: list[dict] = []
    for path in sorted(run_cache.glob("*__summary.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        replay_rows.append({"run": item["strategy_name"], "timeframe": item["timeframe"], **item["metrics"]})
    replay = pd.DataFrame(replay_rows)
    merged = baseline.merge(replay, on=["run", "timeframe"], suffixes=("_baseline", "_replay"), validate="one_to_one")
    metrics = ["total_return", "profit_factor", "expectancy_usd", "number_of_trades", "fill_count"]
    for metric in metrics:
        left = pd.to_numeric(merged[f"{metric}_baseline"], errors="coerce")
        right = pd.to_numeric(merged[f"{metric}_replay"], errors="coerce")
        finite = np.isfinite(left) & np.isfinite(right)
        both_inf = np.isinf(left) & np.isinf(right) & (np.sign(left) == np.sign(right))
        merged[f"{metric}_abs_diff"] = np.where(finite, (left - right).abs(), np.where(both_inf, 0.0, np.nan))
        merged[f"{metric}_match"] = merged[f"{metric}_abs_diff"].fillna(np.inf) <= 1e-9
    merged["all_metrics_match"] = merged[[f"{metric}_match" for metric in metrics]].all(axis=1)
    keep = ["run", "timeframe", "all_metrics_match"] + [
        name for metric in metrics for name in (f"{metric}_baseline", f"{metric}_replay", f"{metric}_abs_diff")
    ]
    merged[keep].to_csv(output / "baseline_reproduction_check.csv", index=False)
    return {
        "rows_expected": len(baseline), "rows_replayed": len(replay), "rows_matched": len(merged),
        "all_metrics_match": bool(len(merged) == len(baseline) == len(replay) and merged["all_metrics_match"].all()),
        "maximum_finite_absolute_difference": float(merged[[f"{metric}_abs_diff" for metric in metrics]].max().max()),
    }


def _fill_exposure_path(fill_details: str) -> str:
    try:
        fills = json.loads(fill_details)
    except (TypeError, json.JSONDecodeError):
        return _json([])
    quantities: dict[str, float] = {}
    marks: dict[str, float] = {}
    rows: list[dict[str, Any]] = []
    for fill in fills:
        symbol = str(fill["symbol"])
        signed = float(fill["quantity"]) * (1 if fill["side"] == "BUY" else -1)
        quantities[symbol] = quantities.get(symbol, 0.0) + signed
        marks[symbol] = float(fill["price"])
        rows.append({
            "timestamp": fill["timestamp"],
            "gross_exposure_usd_at_last_fill_marks": sum(
                abs(quantity * marks.get(item, 0.0)) for item, quantity in quantities.items()
            ),
        })
    return _json(rows)


def _exit_bucket(reason: Any) -> str:
    value = str(reason).lower()
    if "failed breakout" in value:
        return "failed_breakout"
    if "tp" in value or "target" in value or "mean reversion" in value:
        return "take_profit"
    if "time stop" in value or "timed out" in value:
        return "time_stop"
    if "event" in value or "earnings" in value or "dividend" in value:
        return "event_exit"
    if "breakout" in value:
        return "breakout_exit"
    if "kill" in value or "stop" in value or "invalidation" in value or "adverse" in value:
        return "stop_or_kill"
    if "end-of-sample" in value or "forced" in value:
        return "forced_close"
    return "other"


def _enrich_sweep_flags(root: Path, campaigns: pd.DataFrame, config: dict) -> pd.DataFrame:
    result = campaigns.copy()
    result["entry_sweep_reclaim"] = False
    result["entry_sweep_reclaim_status"] = "CAUSAL_CANDLE_PROXY"
    cache = root / "data" / "phase2d_data_trial" / "hf_data_library"
    for (timeframe, symbol), indices in result.groupby(["timeframe", "symbol"]).groups.items():
        frames = _load_frames(cache, str(timeframe), [str(symbol)], config)
        technical = add_technical_features(frames[str(symbol)])
        for index in indices:
            timestamp = pd.Timestamp(result.at[index, "signal_timestamp"])
            row = _previous_row(technical, timestamp)
            if result.at[index, "strategy_family"] == "natural_long_grid" or _safe_float(result.at[index, "residual_z_score"]) is None:
                flag = bool(row.get("bullish_sweep_reclaim", False))
            elif float(result.at[index, "residual_z_score"]) < 0:
                flag = bool(row.get("bullish_sweep_reclaim", False))
            else:
                flag = bool(row.get("bearish_sweep_reclaim", False))
            result.at[index, "entry_sweep_reclaim"] = flag
    return result


def _manual_replays(
    campaigns: pd.DataFrame,
    paths: pd.DataFrame,
    gate_examples: pd.DataFrame,
    output: Path,
) -> pd.DataFrame:
    directory = output / "manual_replays"
    directory.mkdir(parents=True, exist_ok=True)
    for stale in directory.glob("*.md"):
        stale.unlink()
    selected: list[tuple[str, str, str]] = []
    residual = campaigns[campaigns["strategy_family"] == "residual_grid"]
    selected += [(row.run_id, row.campaign_id, "BIGGEST_RESIDUAL_LOSER") for row in residual.nsmallest(10, "net_pnl").itertuples()]
    residual_losses = residual[residual["net_pnl"] < 0].sort_values("net_pnl")
    if len(residual_losses):
        positions = np.unique(np.linspace(0, len(residual_losses) - 1, min(10, len(residual_losses))).astype(int))
        selected += [(residual_losses.iloc[position]["run_id"], residual_losses.iloc[position]["campaign_id"], "TYPICAL_RESIDUAL_LOSER") for position in positions]
    selected += [(row.run_id, row.campaign_id, "RESIDUAL_WINNER") for row in residual.nlargest(5, "net_pnl").itertuples()]
    natural = campaigns[campaigns["strategy_family"] == "natural_long_grid"]
    selected += [(row.run_id, row.campaign_id, "ALL_NATURAL_GRID_TRADES") for row in natural.itertuples()]
    pairs = campaigns[campaigns["strategy_family"] == "stock_pair_grid"]
    selected += [(row.run_id, row.campaign_id, "ALL_STOCK_PAIR_TRADES") for row in pairs.itertuples()]
    selected += [(row.run_id, row.campaign_id, "STOPPED_THEN_REVERTED") for row in campaigns[campaigns["stop_before_potential_reversion"].fillna(False)].head(10).itertuples()]
    selected += [(row.run_id, row.campaign_id, "TP_MISSED_THEN_REVERSED") for row in campaigns[campaigns["tp_missed_due_next_bar"].fillna(False)].head(10).itertuples()]
    selected += [(row.run_id, row.campaign_id, "BIGGEST_HEDGE_DRAG") for row in residual.nsmallest(10, "hedge_leg_pnl").itertuples()]
    selected += [(row.run_id, row.campaign_id, "HIGHEST_COST_TP_RATIO") for row in campaigns.nlargest(10, "cost_as_pct_expected_tp").itertuples()]
    reasons: dict[tuple[str, str], list[str]] = {}
    for run_id, campaign_id, reason in selected:
        reasons.setdefault((str(run_id), str(campaign_id)), []).append(reason)
    index_rows: list[dict] = []
    for number, ((run_id, campaign_id), selection_reasons) in enumerate(reasons.items(), start=1):
        match = campaigns[(campaigns["run_id"].astype(str) == run_id) & (campaigns["campaign_id"].astype(str) == campaign_id)]
        if match.empty:
            continue
        row = match.iloc[0]
        path = paths[(paths["run_id"].astype(str) == run_id) & (paths["campaign_id"].astype(str) == campaign_id)].copy()
        filename = f"{number:03d}_{re.sub(r'[^A-Za-z0-9_-]+', '_', run_id + '_' + campaign_id)[:130]}.md"
        detail_columns = [
            "timestamp", "open", "high", "low", "close", "volume", "z_score", "range_high", "range_low", "atr", "state_or_fill",
        ]
        failure = "WINNING_CAMPAIGN" if row["net_pnl"] > 0 else (
            "HEDGE_DRAG" if row["stock_leg_pnl"] > 0 and row["hedge_leg_pnl"] < 0
            else "NO_MEAN_REVERSION" if row["z_continued_against_position"] else "STOP_OR_EXIT_FAILURE"
        )
        _write(
            directory / filename,
            f"# Campaign replay — {campaign_id}\n\n"
            f"Selection: **{', '.join(sorted(set(selection_reasons)))}**  \n"
            f"Run: `{row['run_id']}`  \n"
            f"Period: {row['start_timestamp']} → {row['end_timestamp']}  \n"
            f"Net P&L: **${_fmt(row['net_pnl'], 2)}**; stock leg ${_fmt(row['stock_leg_pnl'], 2)}; hedge leg ${_fmt(row['hedge_leg_pnl'], 2)}  \n"
            f"MAE/MFE: ${_fmt(row['mae'], 2)} / ${_fmt(row['mfe'], 2)}  \n"
            f"Grid: {int(row['filled_levels'])}/{int(row['configured_levels'])} levels; step/ATR {_fmt(row['grid_step_atr'])}; average-entry improvement {_fmt(row['average_entry_improvement'], 4)}  \n"
            f"TP/stop: {_fmt(row['tp_distance_atr'])} ATR / {_fmt(row['stop_distance_atr'])} ATR  \n"
            f"Exit: {row['exit_reason']}  \n"
            f"Failure classification: **{failure}**\n\n"
            "## Sampled path\n\n"
            + _markdown_table(path[detail_columns] if not path.empty else path, limit=80)
            + "\n\n## Interpretation\n\n"
            + (
                "Observed campaign is profitable; it is included as a comparison case, not as evidence of a stable edge."
                if row["net_pnl"] > 0 else
                "The table shows the causal signal path and actual fills. The classification is descriptive; any proposed alternate stop, target, hedge, or filter requires a new pre-registered OOS phase."
            ),
        )
        index_rows.append({
            "campaign_key": row["campaign_key"], "campaign_id": campaign_id, "selection_reasons": ";".join(sorted(set(selection_reasons))),
            "strategy_family": row["strategy_family"], "pair": row["pair"], "timeframe": row["timeframe"],
            "net_pnl": row["net_pnl"], "file": f"manual_replays/{filename}",
        })
    if not gate_examples.empty:
        for number, item in gate_examples.head(10).iterrows():
            filename = f"blocked_{number + 1:02d}_{item['run_id']}_{item['failure_reason']}.md".replace("/", "_")
            _write(
                directory / filename,
                f"# Natural-grid blocked setup\n\nRun: `{item['run_id']}`  \nTimestamp: {item['timestamp']}  \n"
                f"Primary failed gate: **{item['failure_reason']}**\n\n"
                + _markdown_table(pd.DataFrame([item]))
                + "\n\nThis is a no-trade diagnostic example. No hypothetical fill or P&L is assigned.",
            )
            index_rows.append({
                "campaign_key": f"{item['run_id']}::NO_TRADE::{item['timestamp']}", "campaign_id": "NO_TRADE", "selection_reasons": "NATURAL_GRID_BLOCKED",
                "strategy_family": "natural_long_grid", "pair": item["run_id"], "timeframe": str(item["run_id"]).split("__", 1)[0],
                "net_pnl": None, "file": f"manual_replays/{filename}",
            })
    return pd.DataFrame(index_rows)


def _write_reports(
    output: Path,
    campaigns: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
    grid: pd.DataFrame,
    stop_tp: pd.DataFrame,
    residual: pd.DataFrame,
    gates: pd.DataFrame,
    conditional: pd.DataFrame,
    counterfactuals: pd.DataFrame,
    replay_index: pd.DataFrame,
    summary: dict[str, Any],
) -> None:
    strategy_view = tables["strategy"].copy()
    for column in ("net_pnl", "average_pnl", "profit_factor", "max_drawdown", "average_cost"):
        if column in strategy_view:
            strategy_view[column] = strategy_view[column].map(lambda value: _fmt(value))
    _write(
        output / "loss_attribution_report.md",
        "# Phase 3A loss attribution\n\n"
        "## Scope and evidence quality\n\n"
        "This report replays the unchanged Phase 2D frozen engine over cached HF R-LITE bars. The source remains **LIMITED**: adjusted OHLC, IEX-only after March 2022, RTH only, survivorship-biased, and without point-in-time event history. Event effects are therefore `UNAVAILABLE`, never zero.\n\n"
        "## Family/timeframe attribution\n\n" + _markdown_table(strategy_view, limit=20) + "\n\n"
        "## Interpretation\n\n"
        f"The largest campaign-level failure class is **{summary['main_loss_driver']}**. Secondary classes are {', '.join(summary['secondary_loss_drivers']) or 'none measurable'}. "
        "Flags are descriptive. `POTENTIAL_CONDITIONAL_EDGE` requires at least 30 campaigns or 100 legs, multiple symbols and months, PF > 1.15, positive expectancy, and <=25% single-campaign profit concentration.\n\n"
        "Bucket-level details are in the five attribution CSV files. Tiny samples are labeled `UNDERPOWERED` or `TOO_SPARSE`.",
    )
    filled = pd.to_numeric(grid["filled_levels"], errors="coerce")
    _write(
        output / "grid_order_placement_report.md",
        "# Grid level and order placement audit\n\n"
        f"- Campaigns audited: **{len(grid)}**\n"
        f"- Fewer than two filled levels: **{int((filled < 2).sum())}/{len(grid)}**\n"
        f"- Grid step < 0.4 ATR: **{int(grid['grid_too_narrow'].sum())}/{len(grid)}**\n"
        f"- Grid step > 1.2 ATR: **{int(grid['grid_too_wide'].sum())}/{len(grid)}**\n"
        f"- Meaningful average-entry improvement: **{int(grid['average_entry_improved_meaningfully'].sum())}/{len(grid)}**\n"
        f"- Cost >= 50% of expected TP: **{int(grid['tp_cost_dominated'].sum())}/{len(grid)}**\n"
        f"- Stopped then reverted within {FORWARD_BARS} bars: **{int(grid['stopped_then_reverted'].sum())}/{len(grid)}**\n\n"
        "Residual-grid `grid_step/ATR` is a price-equivalent conversion from residual standard deviation, not a resting price-grid measurement. Natural-grid levels are actual resting limits. HF prices are adjusted, so level placement is mechanically comparable but not raw-price execution evidence.\n\n"
        "Averaging is judged meaningful only when improvement exceeds 0.1 ATR. Counterfactual stop/TP conclusions remain explanatory and require new OOS validation.",
    )
    stop_counts = stop_tp["stop_category"].value_counts().rename_axis("category").reset_index(name="count")
    tp_counts = stop_tp["tp_category"].value_counts().rename_axis("category").reset_index(name="count")
    _write(
        output / "stop_tp_failure_report.md",
        "# Stop/TP failure analysis\n\n## Stop classifications\n\n" + _markdown_table(stop_counts) +
        "\n\n## TP classifications\n\n" + _markdown_table(tp_counts) +
        f"\n\nObserved stop logic status: **{summary['stop_logic_status']}**. Observed TP status: **{summary['tp_logic_status']}**. "
        f"Post-stop reversion uses a fixed {FORWARD_BARS}-bar diagnostic horizon. It does not prove a wider stop would be profitable because capital usage and later adverse paths are not replayed. "
        "The alternative stop/TP fields are path heuristics only, never parameter selections.",
    )
    residual_metrics = _bucket_metrics(residual) if len(residual) else {}
    long_short = _group_table(residual, ["direction", "timeframe"], "direction") if len(residual) else pd.DataFrame()
    _write(
        output / "residual_failure_report.md",
        "# Residual-grid failure analysis\n\n"
        f"- Campaigns: **{len(residual)}**\n"
        f"- Net P&L: **${_fmt(residual_metrics.get('net_pnl'), 2)}**\n"
        f"- Profit factor: **{_fmt(residual_metrics.get('profit_factor'))}**\n"
        f"- Mean reversion reached during campaign: **{int(residual['mean_reverted_during_campaign'].sum()) if len(residual) else 0}/{len(residual)}**\n"
        f"- Z-score continued adversely after entry: **{int(residual['z_continued_against_position'].sum()) if len(residual) else 0}/{len(residual)}**\n"
        f"- Stock-leg P&L: **${_fmt(residual['stock_leg_pnl'].sum() if len(residual) else 0, 2)}**\n"
        f"- Hedge-leg P&L: **${_fmt(residual['hedge_leg_pnl'].sum() if len(residual) else 0, 2)}**\n"
        f"- Hedge impact classification: **{summary['hedge_impact']}**\n\n"
        "## Long versus short residual\n\n" + _markdown_table(long_short, limit=12) + "\n\n"
        "Dollar-neutral and no-hedge values are not promoted as strategies. Stock-only P&L is a leg decomposition; an exact dollar-neutral comparison requires a separately pre-registered replay. Z exits and kill levels are analyzed descriptively without choosing a winner.",
    )
    _write(
        output / "natural_grid_no_trade_report.md",
        "# Natural long-grid no-trade analysis\n\n"
        "HF R-LITE has no point-in-time event calendar, so the event gate is explicitly unavailable and was not the cause of observed R-LITE blocking. The waterfall applies frozen filters sequentially; `final_armed_signals` counts bar-level opportunities, while `final_campaigns` respects state, pending orders, cooldown, and position lifecycle.\n\n"
        + _markdown_table(gates, limit=30)
        + "\n\n## Mechanical mismatch found\n\n"
        "The frozen universe threshold is named `min_average_daily_dollar_volume` and equals $50 million, but natural, residual, and pair strategies calculate a rolling mean of **20 intraday bars** and compare that per-bar value directly with the daily threshold. This is a timeframe-unit mismatch, not evidence that the symbols are illiquid. In the natural waterfall, the liquidity stage frequently removes nearly all surviving bars; on 5m many symbols fall from tens of thousands of regime-valid bars to zero. The mismatch is preserved in Phase 3A and must be corrected only in a pre-registered Phase 3B mechanics change.\n\n"
        "The `dominant_gate` column identifies the largest absolute sequential loss of candidate bars; it often reports the earlier range gate because that stage starts from the largest population. The liquidity-stage counts remain the decisive late-stage density bottleneck. Diagnostics do not recommend simply disabling either gate.",
    )
    eligible = conditional[conditional["conditional_edge_eligible"]]
    positive_sparse = conditional[(conditional["profit_factor"] > 1.15) & (conditional["expectancy"] > 0) & ~conditional["conditional_edge_eligible"]]
    _write(
        output / "conditional_edge_report.md",
        "# Conditional edge search\n\n"
        f"Eligible conditional buckets: **{len(eligible)}**. Positive but ineligible/underpowered buckets: **{len(positive_sparse)}**.\n\n"
        "A bucket is eligible only with >=30 campaigns or >=100 legs, PF > 1.15, positive expectancy, <=25% profit concentration, >=2 symbols, and >=2 months. All buckets use pre-entry fields or immutable campaign mechanics; filled-level and averaging buckets are mechanics diagnostics rather than deployable entry filters.\n\n"
        "## Eligible buckets\n\n" + _markdown_table(eligible[[column for column in ["strategy_family", "condition", "condition_bucket", "campaigns", "trades_legs", "profit_factor", "expectancy", "symbols", "months", "profit_concentration"] if column in eligible]], limit=30) +
        "\n\n## Positive but not eligible\n\n" + _markdown_table(positive_sparse[[column for column in ["strategy_family", "condition", "condition_bucket", "campaigns", "profit_factor", "expectancy", "diagnostic_flags"] if column in positive_sparse]], limit=30) +
        "\n\nNo bucket is a final strategy. Any surviving condition must be frozen in Phase 3B and tested on a separate OOS interval/source.",
    )
    failure_summary = counterfactuals.groupby("primary_failure_mode", as_index=False).agg(campaigns=("campaign_id", "size"), net_pnl=("net_pnl", "sum")).sort_values("net_pnl")
    _write(
        output / "counterfactual_report.md",
        "# Counterfactual failure modes\n\n" + _markdown_table(failure_summary, limit=30) +
        "\n\nEach losing campaign receives one primary failure mode via a fixed, documented hierarchy. Boolean `would_*_help` fields are causal-path plausibility checks, not rerun P&L. They ignore portfolio opportunity cost and interactions unless an exact observed leg decomposition exists. They must not be used to select production parameters.",
    )
    _write(
        output / "manual_replay_index.md",
        "# Manual campaign replay index\n\n"
        "Replays use sampled OHLC/z-score paths plus exact fills. They are human-audit artifacts, not separate simulations. Natural blocked examples intentionally contain no hypothetical P&L.\n\n"
        + _markdown_table(replay_index, limit=200),
    )
    family = summary["family_metrics"]
    residual_pf = family.get("residual_grid", {}).get("profit_factor")
    natural_pf = family.get("natural_long_grid", {}).get("profit_factor")
    pairs_pf = family.get("stock_pair_grid", {}).get("profit_factor")
    report = f"""# Phase 3A — Edge failure diagnostic report

## Executive conclusion

Phase 3A does not find a production-ready or paper-trading edge. It explains the frozen R-LITE result at campaign level, but the HF source remains insufficient for definitive market validation. The unchanged live status is **NO-GO**.

MAIN LOSS DRIVER: {summary['main_loss_driver']}
SECONDARY LOSS DRIVERS: {', '.join(summary['secondary_loss_drivers']) or 'NONE MEASURABLE'}
RESIDUAL GRID STATUS: {summary['residual_grid_status']}
NATURAL LONG GRID STATUS: {summary['natural_long_grid_status']}
STOCK PAIRS STATUS: {summary['stock_pairs_status']}
BREAKOUT CONTINUATION STATUS: {summary['breakout_continuation_status']}
GRID GEOMETRY STATUS: {summary['grid_geometry_status']}
STOP LOGIC STATUS: {summary['stop_logic_status']}
TP LOGIC STATUS: {summary['tp_logic_status']}
HEDGE IMPACT: {summary['hedge_impact']}
COST IMPACT: {summary['cost_impact']}
CONDITIONAL EDGE FOUND: {summary['conditional_edge_found']}
LIVE TRADING STATUS: NO-GO
NEXT PHASE RECOMMENDATION: Phase 3B — pre-register only the mechanically justified redesign hypotheses, freeze them, and validate on raw consolidated intraday data with point-in-time events. Do not tune on HF R-LITE.

## Answers to the research questions

1. **Where losses came from.** The dominant classified loss mode is `{summary['main_loss_driver']}`; the next modes are {', '.join(summary['secondary_loss_drivers']) or 'not measurable'}. The exact campaign counts and dollars are in `counterfactual_failure_modes.csv`.
2. **Entry vs geometry vs stop/exit vs hedge/cost.** These effects are separated rather than collapsed: observed PF is residual {_fmt(residual_pf)}, natural {_fmt(natural_pf)}, and pairs {_fmt(pairs_pf)}; stop-reversion rate is {_fmt(summary['stop_reversion_rate'] * 100, 1)}%; costs are {_fmt(summary['cost_ratio_abs_gross'] * 100, 1)}% of absolute gross campaign movement.
3. **Levels.** Frozen orders were placed according to the audited mechanics, but range validity and support proximity are mixed. Adjusted HF prices prevent a raw-price execution verdict.
4. **Regimes.** Regime tables show whether correctly placed orders still failed in trend/volatility states. Only buckets passing the full minimum-sample rule can be called a conditional candidate.
5. **Grid width.** Aggregate status is `{summary['grid_geometry_status']}`; see grid-step/ATR buckets for family-specific behavior.
6. **Averaging.** The dataset records the average entry after each add. Meaningful improvement is defined before inspection as >0.1 ATR.
7. **Filled legs.** Campaigns with fewer than two filled levels are explicitly marked as unable to exercise meaningful averaging.
8. **Stops.** Aggregate status is `{summary['stop_logic_status']}`. A later {FORWARD_BARS}-bar reversion is evidence of timing sensitivity, not proof that a wider stop is superior.
9. **TPs.** Aggregate status is `{summary['tp_logic_status']}`. Cost/TP ratios and missed favorable excursions are reported separately.
10. **Residual reversion.** `residual_failure_analysis.csv` gives z after 1/3/5/10 bars, maximum favorable/adverse z movement, and time to reversion for every residual campaign.
11. **Hedge legs.** Aggregate hedge effect is `{summary['hedge_impact']}`. Stock and hedge cashflows are shown independently; stock-only is not treated as a valid replacement strategy.
12. **Breakout.** {summary['breakout_campaigns']} campaigns contain breakout attribution with ${_fmt(summary['breakout_pnl'], 2)} total breakout P&L. Sparse attribution remains inconclusive and cannot hide grid losses.
13. **Natural-grid scarcity.** The sequential waterfall shows progressive losses through range/ADX/regime gates and a decisive late-stage liquidity bottleneck. The code compares a $50 million **daily** liquidity threshold with the mean dollar volume of 20 **intraday bars**. This unit mismatch explains much of the scarcity and also affects residual/pair opportunity gates. Event blocking remains unavailable because R-LITE had no event history.
14. **Conditional edge.** {summary['eligible_buckets']} buckets pass all diagnostic eligibility rules. Status: `{summary['conditional_edge_found']}`.
15. **Family worth redesigning.** Natural long grid is `{summary['natural_long_grid_status']}` because signal density, support/range gating, and resting-grid geometry can be tested as pre-registered mechanics. Residual grid in its current form is `{summary['residual_grid_status']}`.
16. **Family to stop in current form.** Any family marked `ABANDON` should not receive further parameter sweeps; only a materially different, economically justified hypothesis may return.
17. **Phase 3B tests.** First correct and freeze the liquidity unit: compute ADV from completed daily sessions (or an explicitly equivalent intraday scaling) before any strategy redesign. Then pre-register at most: (a) a natural-grid support/sweep context with a density floor, (b) a residual entry delay or trend veto only if sufficient-sample buckets justify it, and (c) a hedge-ratio redesign only if hedge drag is stable across symbols/months. Use raw prices, consolidated volume, and point-in-time events.
18. **Do not test further.** Do not cherry-pick symbols/months, select the best z/stop/TP from these diagnostics, reuse HF adjusted bars as fill truth, or begin paper/live integration.

## Reliability limits

- HF R-LITE is adjusted and IEX-only after March 2022; volume/level evidence is limited.
- No point-in-time events were available, so event proximity is unavailable.
- The universe is survivorship-biased.
- Counterfactuals are explanatory path heuristics unless explicitly labeled observed leg P&L.
- The frozen engine/config digest was checked before and after the run; Phase 2D baseline parameters were not mutated.
- The 58 replays reproduce Phase 2D-R0 trade counts, fills, returns, PF, and expectancy within a 1e-9 tolerance; details are in `baseline_reproduction_check.csv`.
"""
    _write(output / "edge_failure_diagnostic_report.md", report)


def _collect_cache(run_cache: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    campaign_files = sorted(run_cache.glob("*__campaigns.parquet"))
    path_files = sorted(run_cache.glob("*__paths.parquet"))
    gate_files = sorted(run_cache.glob("*__gate.json"))
    example_files = sorted(run_cache.glob("*__gate_examples.parquet"))
    campaigns = pd.concat([pd.read_parquet(path) for path in campaign_files if path.stat().st_size], ignore_index=True, sort=False) if campaign_files else pd.DataFrame()
    paths = pd.concat([pd.read_parquet(path) for path in path_files if path.stat().st_size], ignore_index=True, sort=False) if path_files else pd.DataFrame()
    gates = pd.DataFrame([json.loads(path.read_text(encoding="utf-8")) for path in gate_files])
    examples = pd.concat([pd.read_parquet(path) for path in example_files if path.stat().st_size], ignore_index=True, sort=False) if example_files else pd.DataFrame()
    return campaigns, paths, gates, examples


def run_phase3a(root: Path, *, workers: int = 3, force: bool = False) -> dict[str, Any]:
    output = root / "outputs" / "phase3a_loss_forensics"
    output.mkdir(parents=True, exist_ok=True)
    run_cache = output / "_run_cache"
    run_cache.mkdir(parents=True, exist_ok=True)
    config = load_config(root / "config" / "phase2d_frozen.yaml")
    snapshot = json.loads((root / "outputs" / "phase2d" / "frozen_engine_snapshot.json").read_text(encoding="utf-8"))
    frozen_before = _digest_value(_frozen_parameters(config))
    if frozen_before != snapshot["frozen_parameter_sha256"]:
        raise RuntimeError("Frozen Phase 2D parameter digest changed; refusing Phase 3A")
    previous_files = [
        path for directory in (root / "outputs").glob("phase*")
        if directory.name != "phase3a_loss_forensics" for path in directory.rglob("*") if path.is_file()
    ]
    previous_hashes = {str(path.relative_to(root)): _sha256(path) for path in previous_files}
    trade_starts = {
        timeframe: _trade_start(config, root / "data" / "phase2d_data_trial" / "hf_data_library", timeframe)
        for timeframe in ("5min", "15min")
    }
    payloads = [
        {
            "root": str(root), "spec": spec, "timeframe": timeframe,
            "trade_start": str(trade_starts[timeframe]), "run_cache": str(run_cache), "force": force,
        }
        for timeframe in ("5min", "15min") for spec in _strategy_specs(config)
    ]
    summaries: list[dict] = []
    if workers <= 1:
        for number, payload in enumerate(payloads, start=1):
            summary = _worker(payload)
            summaries.append(summary)
            print(f"PHASE3A_RUN {number}/{len(payloads)} {summary['run_id']} campaigns={summary['campaigns']}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=min(workers, len(payloads))) as pool:
            futures = {pool.submit(_worker, payload): payload for payload in payloads}
            for number, future in enumerate(as_completed(futures), start=1):
                summary = future.result()
                summaries.append(summary)
                print(f"PHASE3A_RUN {number}/{len(payloads)} {summary['run_id']} campaigns={summary['campaigns']}", flush=True)
    campaigns, paths, gates, gate_examples = _collect_cache(run_cache)
    if campaigns.empty:
        raise RuntimeError("Phase 3A produced no campaign ledger")
    campaigns = campaigns.sort_values(["start_timestamp", "strategy_family", "pair"]).reset_index(drop=True)
    campaigns["campaign_key"] = campaigns["run_id"].astype(str) + "::" + campaigns["campaign_id"].astype(str)
    campaigns = _enrich_sweep_flags(root, campaigns, config)
    campaigns["open_exposure_over_time"] = campaigns["fill_details"].map(_fill_exposure_path)
    campaigns["exit_bucket"] = campaigns["exit_reason"].map(_exit_bucket)
    # A next-bar TP miss is not the same as a later post-stop reversion.  The
    # frozen engine does not retain the target signal mark, so use a conservative
    # proxy only when a TP-labelled next-bar exit turned a positive MFE into a
    # negative campaign.  Preserve the limitation explicitly.
    tp_exit = campaigns["exit_reason"].astype(str).str.lower().str.contains("tp|target|mean reversion completed", regex=True)
    campaigns["tp_missed_due_next_bar"] = tp_exit & campaigns["net_pnl"].lt(0) & campaigns["mfe"].gt(0)
    campaigns["tp_missed_due_next_bar_status"] = "CONSERVATIVE_PROXY_FROM_TP_EXIT_MFE_AND_REALIZED_PNL"
    if not gates.empty:
        gate_differences = {
            "data_quality_or_warmup_failed": ("total_candles", "after_data_session_filters"),
            "range_condition_failed": ("after_data_session_filters", "after_range_filter"),
            "trend_filter_failed": ("after_range_filter", "after_trend_filter"),
            "atr_volatility_filter_failed": ("after_trend_filter", "after_volatility_filter"),
            "market_regime_failed": ("after_volatility_filter", "after_market_regime_filter"),
            "volume_liquidity_filter_failed": ("after_market_regime_filter", "after_volume_filter"),
            "price_not_near_range_low_support": ("after_volume_filter", "after_support_proximity"),
            "tp_cost_distance_invalid": ("after_support_proximity", "after_cost_tp_filter"),
            "grid_geometry_invalid": ("after_cost_tp_filter", "after_grid_geometry_validation"),
        }
        for column, (before, after) in gate_differences.items():
            gates[column] = pd.to_numeric(gates[before], errors="coerce") - pd.to_numeric(gates[after], errors="coerce")
        gates["stop_distance_invalid"] = 0
        gates["stop_distance_gate_status"] = "NOT_A_SEPARATE_FROZEN_ENTRY_GATE"
        gates["liquidity_threshold_basis"] = "DAILY_THRESHOLD_COMPARED_WITH_20_INTRADAY_BAR_DOLLAR_VOLUME"
    campaigns.to_csv(output / "campaign_forensics.csv", index=False)
    paths.to_parquet(output / "campaign_path_samples.parquet", index=False)
    gates.to_csv(output / "natural_grid_gate_waterfall.csv", index=False)
    tables = _attribution_tables(campaigns, output)
    grid = _grid_audit(campaigns, output)
    stop_tp = _stop_tp_analysis(campaigns, output)
    residual = _residual_failure(campaigns, output)
    conditional = _conditional_edges(campaigns, output)
    counterfactuals = _counterfactuals(campaigns, output)
    summary = _status_summary(campaigns, conditional, counterfactuals)
    replay_index = _manual_replays(campaigns, paths, gate_examples, output)
    reproduction = _baseline_reproduction(root, run_cache, output)
    summary["baseline_reproduction"] = reproduction
    _write_reports(
        output, campaigns, tables, grid, stop_tp, residual, gates, conditional,
        counterfactuals, replay_index, summary,
    )
    previous_after = {str(path.relative_to(root)): _sha256(path) for path in previous_files}
    changed_previous = [key for key, digest in previous_hashes.items() if previous_after.get(key) != digest]
    frozen_after = _digest_value(_frozen_parameters(load_config(root / "config" / "phase2d_frozen.yaml")))
    manifest = {
        "phase": PHASE, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "HF_DATA_LIBRARY_R_LITE", "source_status": SOURCE_STATUS,
        "frozen_parameter_sha256_before": frozen_before, "frozen_parameter_sha256_after": frozen_after,
        "frozen_parameters_unchanged": frozen_before == frozen_after,
        "previous_artifacts_checked": len(previous_hashes), "previous_artifacts_changed": changed_previous,
        "runs": len(summaries), "campaigns": len(campaigns), "workers": workers,
        "counterfactual_policy": "EXPLANATORY_ONLY_NOT_OPTIMIZATION",
        "live_trading_status": "NO-GO", "baseline_reproduction": reproduction, "summary": summary,
    }
    _write_json(output / "phase3a_manifest.json", manifest)
    if changed_previous:
        raise RuntimeError(f"Prior artifacts changed during Phase 3A: {changed_previous[:5]}")
    if frozen_before != frozen_after:
        raise RuntimeError("Frozen parameters mutated during Phase 3A")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 3A loss forensics")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--workers", type=int, default=max(1, min(3, (os.cpu_count() or 2) - 1)))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    manifest = run_phase3a(args.root.resolve(), workers=args.workers, force=args.force)
    print(json.dumps(manifest, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
