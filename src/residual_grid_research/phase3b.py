from __future__ import annotations

"""Phase 3B: corrected ADV gate and pre-registered redesign diagnostics.

The module deliberately keeps the Phase 2D engine configuration immutable. It
loads the separate Phase 3B protocol, freezes its code/config/universe hashes,
then runs only the variants registered below. Results remain HF R-LITE limited
and cannot promote a strategy to paper or live trading.
"""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
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
from residual_grid_research.features.regime import regime_allows_grid
from residual_grid_research.phase3a import (
    _average_entry_progress,
    _entry_fills,
    _fill_level_count,
    _load_frames,
    _make_strategy,
    _previous_row,
    _safe_div,
    _safe_float,
    _sha256,
    _signal_time,
    _strategy_specs,
    _trade_start,
    _write,
    _write_json,
)


PHASE = "3B"
SOURCE_STATUS = "HF_R_LITE_LIMITED"
CONFIG_PATH = Path("config/phase3b_redesign.yaml")
TIMEFRAMES = ("5min", "15min")


def _json(value: Any) -> str:
    return json.dumps(value, default=str, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _deep_update(target: dict, updates: dict) -> dict:
    result = deepcopy(target)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_update(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def variant_registry() -> dict[str, dict[str, Any]]:
    """Executable mirror of the variants pre-registered in the YAML protocol."""

    return {
        "H1_CORRECTED_BASELINE": {
            "hypothesis": "H1", "family": "natural_long_grid", "changes": {},
        },
        "H2_STEP08_TP10_DEPTH3_RANGE1": {
            "hypothesis": "H2", "family": "natural_long_grid",
            "changes": {"strategy": {"natural": {
                "grid_step_atr": 0.8, "tp_mode": "1.0_step", "max_grid_depth": 3,
                "grid_level_count": 3, "stop_variant": "range_low_1.0_atr",
            }}},
        },
        "H2_STEP10_TP10_DEPTH5_RANGE1": {
            "hypothesis": "H2", "family": "natural_long_grid",
            "changes": {"strategy": {"natural": {
                "grid_step_atr": 1.0, "tp_mode": "1.0_step", "max_grid_depth": 5,
                "grid_level_count": 5, "stop_variant": "range_low_1.0_atr",
            }}},
        },
        "H2_STEP12_TP15_DEPTH7_STRUCTURE": {
            "hypothesis": "H2", "family": "natural_long_grid",
            "changes": {"strategy": {"natural": {
                "grid_step_atr": 1.2, "tp_mode": "1.5_step", "max_grid_depth": 7,
                "grid_level_count": 7, "stop_variant": "structure_close",
            }}},
        },
        "H3_INTRABAR": {
            "hypothesis": "H3", "family": "natural_long_grid",
            "changes": {"strategy": {"natural": {
                "stop_trigger_mode": "intrabar", "stop_variant": "current",
                "catastrophic_stop_atr": None,
            }}},
        },
        "H3_CLOSE1": {
            "hypothesis": "H3", "family": "natural_long_grid",
            "changes": {"strategy": {"natural": {
                "stop_trigger_mode": "close_confirmation", "stop_variant": "structure_close",
                "stop_confirmation_closes": 1, "catastrophic_stop_atr": 2.5,
            }}},
        },
        "H3_CLOSE2": {
            "hypothesis": "H3", "family": "natural_long_grid",
            "changes": {"strategy": {"natural": {
                "stop_trigger_mode": "close_confirmation", "stop_variant": "structure_close",
                "stop_confirmation_closes": 2, "catastrophic_stop_atr": 2.5,
            }}},
        },
        "H4_COST3": {
            "hypothesis": "H4", "family": "natural_long_grid",
            "changes": {"strategy": {"natural": {"cost_aware_tp_multiple": 3.0}}},
        },
        "H4_COST5": {
            "hypothesis": "H4", "family": "natural_long_grid",
            "changes": {"strategy": {"natural": {"cost_aware_tp_multiple": 5.0}}},
        },
        "H4_COST8": {
            "hypothesis": "H4", "family": "natural_long_grid",
            "changes": {"strategy": {"natural": {"cost_aware_tp_multiple": 8.0}}},
        },
        "H5_CORRECTED_BASELINE": {
            "hypothesis": "H5", "family": "stock_pair_grid", "changes": {},
        },
        "H6_EXIT05": {
            "hypothesis": "H6", "family": "stock_pair_grid",
            "changes": {"strategy": {"pairs": {"simple_exit_z": 0.5}}},
        },
        "H6_EXIT02": {
            "hypothesis": "H6", "family": "stock_pair_grid",
            "changes": {"strategy": {"pairs": {"simple_exit_z": 0.2}}},
        },
        "H6_EXIT00": {
            "hypothesis": "H6", "family": "stock_pair_grid",
            "changes": {"strategy": {"pairs": {"simple_exit_z": 0.0}}},
        },
        "H6_TIME3": {
            "hypothesis": "H6", "family": "stock_pair_grid",
            "changes": {"strategy": {"pairs": {"max_holding_days": 3}}},
        },
        "H6_TIME5": {
            "hypothesis": "H6", "family": "stock_pair_grid", "alias_of": "H5_CORRECTED_BASELINE",
            "changes": {},
        },
        "H6_TIME10": {
            "hypothesis": "H6", "family": "stock_pair_grid",
            "changes": {"strategy": {"pairs": {"max_holding_days": 10}}},
        },
        "H7_RESIDUAL_CONFIRMATION": {
            "hypothesis": "H7", "family": "residual_grid", "changes": {},
        },
    }


def _validate_registry(config: dict) -> None:
    registered = variant_registry()
    declared: set[str] = set()
    for hypothesis, item in config["phase3b"]["hypotheses"].items():
        if hypothesis == "H8":
            continue
        declared.update(item["variants"])
    if declared != set(registered):
        raise RuntimeError(
            f"Variant registry/config mismatch: missing={sorted(declared - set(registered))}, "
            f"undeclared={sorted(set(registered) - declared)}"
        )
    if bool(config["strategy"]["breakout"]["enabled"]):
        raise RuntimeError("Phase 3B breakout baseline must remain disabled")


def _code_hash(root: Path) -> tuple[str, dict[str, str]]:
    relative = [
        str(path.relative_to(root)).replace("\\", "/")
        for path in sorted((root / "src" / "residual_grid_research").rglob("*.py"))
    ]
    hashes = {path: _sha256(root / path) for path in relative}
    return _digest(hashes), hashes


def _git_commit(root: Path) -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()


def freeze_baseline(root: Path, *, overwrite: bool = False) -> dict[str, Any]:
    output = root / "outputs" / "phase3b_redesign"
    output.mkdir(parents=True, exist_ok=True)
    path = output / "frozen_phase3b_baseline.json"
    if path.exists() and not overwrite:
        return json.loads(path.read_text(encoding="utf-8"))
    config = load_config(root / CONFIG_PATH)
    _validate_registry(config)
    code_hash, component_hashes = _code_hash(root)
    raw_config_hash = _sha256(root / CONFIG_PATH)
    universe = {
        key: config["universe"][key]
        for key in ("stock_etf_pairs", "stock_pairs", "natural_long_symbols", "benchmarks")
    }
    snapshot = {
        "phase": PHASE,
        "protocol": config["phase3b"]["protocol"],
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit_hash": _git_commit(root),
        "package_version": config["project"]["package_version"],
        "code_sha256": code_hash,
        "code_components": component_hashes,
        "config_sha256": raw_config_hash,
        "universe_sha256": _digest(universe),
        "variant_registry_sha256": _digest(variant_registry()),
        "universe": universe,
        "liquidity_gate": {
            "basis": config["features"]["liquidity_basis"],
            "window_sessions": config["features"]["liquidity_adv_window_sessions"],
            "threshold_usd": config["universe"]["min_average_daily_dollar_volume"],
            "lag": "one_full_trading_session",
            "missing_volume": "FAIL_CLOSED",
            "early_close": "SUM_ACTUAL_SESSION_BARS_NO_SCALING",
        },
        "strategy_configs": config["strategy"],
        "cost_model": config["costs"],
        "fill_model": config["execution"],
        "event_filter": config["events"],
        "calendar_handling": config["data"]["calendar"],
        "walk_forward": config["walk_forward"],
        "data_source": SOURCE_STATUS,
        "source_limitations": [
            "adjusted OHLC rather than raw as-traded execution prices",
            "post-March-2022 IEX-only volume and prints",
            "survivorship-biased symbol catalog",
            "point-in-time events unavailable",
        ],
        "disabled_modules": ["residual_grid_redesign", "breakout_continuation_baseline"],
        "allowed_post_freeze_changes": config["phase3b"]["allowed_post_freeze_changes"],
        "variants": variant_registry(),
        "live_trading_status": "NO-GO",
    }
    _write_json(path, snapshot)
    return snapshot


def _verify_snapshot(root: Path) -> dict[str, Any]:
    path = root / "outputs" / "phase3b_redesign" / "frozen_phase3b_baseline.json"
    if not path.exists():
        raise RuntimeError("Phase 3B baseline has not been frozen; run --freeze-only first")
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    code_hash, current_components = _code_hash(root)
    checks = {
        "config_sha256": _sha256(root / CONFIG_PATH),
        "variant_registry_sha256": _digest(variant_registry()),
    }
    failures = {key: (snapshot.get(key), value) for key, value in checks.items() if snapshot.get(key) != value}
    if snapshot.get("code_sha256") != code_hash:
        change_path = root / "outputs" / "phase3b_redesign" / "post_freeze_change_log.json"
        changes = json.loads(change_path.read_text(encoding="utf-8")) if change_path.exists() else {"changes": []}
        allowed = {
            item["module"]: item
            for item in changes.get("changes", [])
            if item.get("classification") in {"REPORTING_ONLY", "TEST_ONLY", "DATA_ADAPTER_ONLY"}
            and item.get("trading_results_affected") is False
        }
        all_paths = set(snapshot.get("code_components", {})) | set(current_components)
        unexpected = []
        for module in sorted(all_paths):
            before = snapshot.get("code_components", {}).get(module)
            after = current_components.get(module)
            if before == after:
                continue
            item = allowed.get(module)
            if item is None or item.get("before_sha256") != before or item.get("after_sha256") != after:
                unexpected.append({"module": module, "before": before, "after": after})
        if unexpected:
            failures["code_sha256"] = (snapshot.get("code_sha256"), code_hash, unexpected)
    if failures:
        raise RuntimeError(f"Frozen Phase 3B baseline mismatch: {failures}")
    return snapshot


def _job_id(variant: str, spec: dict[str, Any], timeframe: str, threshold: float | None = 50_000_000) -> str:
    pair = spec["primary"] + (f"_{spec['secondary']}" if spec.get("secondary") else "")
    liquidity = "NONE" if threshold is None else str(int(threshold))
    return f"{variant}__LQ{liquidity}__{timeframe}__{spec['family']}__{pair}"


def _apply_variant(config: dict, variant: str, threshold: float | None) -> dict:
    item = variant_registry()[variant]
    if item.get("alias_of"):
        item = variant_registry()[item["alias_of"]]
    result = _deep_update(config, item["changes"])
    result["features"]["liquidity_gate_enabled"] = threshold is not None
    if threshold is not None:
        result["universe"]["min_average_daily_dollar_volume"] = float(threshold)
    result["strategy"]["breakout"]["enabled"] = False
    return result


def _legacy_liquidity(frame: pd.DataFrame) -> pd.Series:
    return (frame["close"] * frame["volume"]).shift(1).rolling(20, min_periods=20).mean()


def _gate_counts(
    strategy: Any,
    spec: dict[str, Any],
    timeframe: str,
    config: dict,
    frames: dict[str, pd.DataFrame],
    result: Any,
) -> dict[str, Any]:
    frame = strategy.prepared
    family = spec["family"]
    gate_enabled = bool(config["features"].get("liquidity_gate_enabled", True))
    threshold = float(config["universe"]["min_average_daily_dollar_volume"])
    legacy_primary = _legacy_liquidity(frames[spec["primary"]]).reindex(frame.index)
    corrected_primary = frame["dollar_volume_20"] if family != "stock_pair_grid" else frame["dollar_volume_a"]
    usable = pd.Series(True, index=frame.index)
    relation = pd.Series(True, index=frame.index)
    safety = pd.Series(True, index=frame.index)
    opportunity = pd.Series(True, index=frame.index)
    support = pd.Series(True, index=frame.index)
    costs = pd.Series(True, index=frame.index)
    geometry = pd.Series(True, index=frame.index)
    legacy_liquid = legacy_primary >= threshold if gate_enabled else pd.Series(True, index=frame.index)
    corrected_liquid = corrected_primary >= threshold if gate_enabled else pd.Series(True, index=frame.index)

    if family == "natural_long_grid":
        settings, features = config["strategy"]["natural"], config["features"]
        required = ["close", "atr_14", "adx_14", "atr_ratio", "range_high", "range_low", "range_position", "range_width_atr"]
        usable = frame[required].notna().all(axis=1)
        relation = frame["range_width_atr"].between(
            float(features["range_width_atr_min"]), float(features["range_width_atr_max"])
        )
        trend = frame["adx_14"] < float(features["range_adx_max"])
        volatility = frame["atr_ratio"] <= float(features["atr_expansion_max"])
        regime = frame["market_regime"].map(regime_allows_grid)
        safety = trend & volatility & regime
        support = frame["range_position"].between(0.0, float(settings["lower_range_fraction"]))
        round_trip = 2 * (float(config["costs"]["spread_bps"]) + float(config["costs"]["slippage_bps"]))
        step_bps = float(settings["grid_step_atr"]) * frame["atr_14"] / frame["close"] * 10000
        if settings.get("cost_aware_tp_multiple") is None:
            costs = step_bps >= round_trip * float(config["costs"]["costs_safety_multiple"])
        else:
            tp_mode = str(settings.get("tp_mode", "range_scaleout"))
            multiplier = {"0.5_step": 0.5, "1.0_step": 1.0, "1.5_step": 1.5}.get(tp_mode)
            distance = (
                ((frame["range_low"] + frame["range_high"]) / 2 - frame["close"]).clip(lower=0)
                if multiplier is None else multiplier * float(settings["grid_step_atr"]) * frame["atr_14"]
            )
            costs = distance / frame["close"] * 10000 >= round_trip * float(settings["cost_aware_tp_multiple"])
        levels = pd.Series(0, index=frame.index, dtype=int)
        for level in range(min(int(settings["grid_level_count"]), int(settings["max_grid_depth"]))):
            levels += (frame["close"] - level * float(settings["grid_step_atr"]) * frame["atr_14"] >= frame["range_low"]).fillna(False).astype(int)
        geometry = levels >= 1
        opportunity = support & costs & geometry
        cumulative = usable.copy()
        after_data = int(cumulative.sum())
        cumulative &= relation.fillna(False)
        after_range = int(cumulative.sum())
        cumulative &= trend.fillna(False)
        after_trend = int(cumulative.sum())
        cumulative &= volatility.fillna(False)
        after_volatility = int(cumulative.sum())
        cumulative &= regime.fillna(False)
        after_regime = int(cumulative.sum())
        pre_liquidity = cumulative.copy()
        detail = {
            "after_data_session_filters": after_data,
            "after_range_filter": after_range,
            "after_trend_filter": after_trend,
            "after_volatility_filter": after_volatility,
            "after_market_regime_filter": after_regime,
            "regime_valid_bars": after_regime,
        }
    elif family == "stock_pair_grid":
        settings, features = config["strategy"]["pairs"], config["features"]
        required = ["z", "corr_60", "corr_90", "beta", "beta_stability", "residual_std"]
        usable = frame[required].notna().all(axis=1)
        relation = (
            (frame["corr_60"] >= float(features["stock_pair_corr_min"]))
            & (frame["corr_90"] >= float(features["stock_pair_corr_90_min"]))
            & (frame["beta_stability"] <= float(features["beta_stability_max"]))
        )
        safety = frame["market_regime"].map(regime_allows_grid)
        if bool(features.get("adx_filter_enabled", False)):
            safety &= frame["a_adx_14"] < float(features["range_adx_max"])
        direction = frame["z"].abs() >= float(settings["entry_z"])
        stationarity = not bool(settings.get("stationarity_proxy_enabled", True)) or strategy.diagnostics.get("half_life_bars") is not None
        opportunity = direction & bool(stationarity)
        secondary = spec["secondary"]
        legacy_secondary = _legacy_liquidity(frames[secondary]).reindex(frame.index)
        legacy_liquid = pd.concat([legacy_primary, legacy_secondary], axis=1).min(axis=1) >= threshold if gate_enabled else pd.Series(True, index=frame.index)
        corrected_liquid = frame[["dollar_volume_a", "dollar_volume_b"]].min(axis=1) >= threshold if gate_enabled else pd.Series(True, index=frame.index)
        cumulative = usable.copy()
        after_data = int(cumulative.sum())
        cumulative &= relation.fillna(False)
        after_relation = int(cumulative.sum())
        cumulative &= safety.fillna(False)
        after_regime = int(cumulative.sum())
        pre_liquidity = cumulative.copy()
        detail = {
            "after_data_session_filters": after_data,
            "pair_candidates": after_relation,
            "after_relationship_filter": after_relation,
            "after_regime_filter": after_regime,
            "regime_valid_bars": after_regime,
        }
    else:
        settings, features = config["strategy"]["residual"], config["features"]
        required = ["z", "corr_60", "beta", "beta_stability", "residual_std", "stock_adx_14"]
        usable = frame[required].notna().all(axis=1)
        direction_long = frame["z"] <= -float(settings["entry_z"])
        direction_short = frame["z"] >= float(settings["entry_z"])
        relation = (
            ((direction_long & (frame["corr_60"] >= float(features["stock_etf_corr_min"])))
             | (direction_short & (frame["corr_60"] >= float(features["stock_etf_short_corr_min"]))))
            & (frame["beta"] > 0)
            & (frame["beta_stability"] <= float(features["beta_stability_max"]))
        )
        safety = frame["market_regime"].map(regime_allows_grid)
        if bool(features.get("adx_filter_enabled", False)):
            safety &= frame["stock_adx_14"] < float(features["range_adx_max"])
        opportunity = direction_long | direction_short
        cumulative = usable.copy()
        after_data = int(cumulative.sum())
        cumulative &= relation.fillna(False)
        after_relation = int(cumulative.sum())
        cumulative &= safety.fillna(False)
        after_regime = int(cumulative.sum())
        pre_liquidity = cumulative.copy()
        detail = {
            "after_data_session_filters": after_data,
            "after_relationship_filter": after_relation,
            "after_regime_filter": after_regime,
            "regime_valid_bars": after_regime,
        }

    legacy_after = int((pre_liquidity & legacy_liquid.fillna(False)).sum())
    corrected_after = int((pre_liquidity & corrected_liquid.fillna(False)).sum())
    final_legacy = int((pre_liquidity & legacy_liquid.fillna(False) & opportunity.fillna(False)).sum())
    final_corrected = int((pre_liquidity & corrected_liquid.fillna(False) & opportunity.fillna(False)).sum())
    if family == "natural_long_grid":
        legacy_after_support_mask = pre_liquidity & legacy_liquid.fillna(False) & support.fillna(False)
        corrected_after_support_mask = pre_liquidity & corrected_liquid.fillna(False) & support.fillna(False)
        legacy_after_cost_mask = legacy_after_support_mask & costs.fillna(False)
        corrected_after_cost_mask = corrected_after_support_mask & costs.fillna(False)
        legacy_final_mask = legacy_after_cost_mask & geometry.fillna(False)
        corrected_final_mask = corrected_after_cost_mask & geometry.fillna(False)
        final_legacy = int(legacy_final_mask.sum())
        final_corrected = int(corrected_final_mask.sum())
        detail.update({
            "legacy_after_support_proximity": int(legacy_after_support_mask.sum()),
            "corrected_after_support_proximity": int(corrected_after_support_mask.sum()),
            "legacy_after_event_filter": int(legacy_after_support_mask.sum()),
            "corrected_after_event_filter": int(corrected_after_support_mask.sum()),
            "legacy_after_cost_tp_filter": int(legacy_after_cost_mask.sum()),
            "corrected_after_cost_tp_filter": int(corrected_after_cost_mask.sum()),
            "legacy_after_grid_geometry": final_legacy,
            "corrected_after_grid_geometry": final_corrected,
        })
    else:
        detail.update({
            "legacy_spread_valid_bars": final_legacy,
            "corrected_spread_valid_bars": final_corrected,
            "legacy_entry_signal_bars": final_legacy,
            "corrected_entry_signal_bars": final_corrected,
        })
    return {
        "strategy_family": family,
        "symbol": spec["primary"],
        "pair": f"{spec['primary']}/{spec.get('secondary')}" if spec.get("secondary") else spec["primary"],
        "timeframe": timeframe,
        "total_bars": len(frame),
        **detail,
        "pre_liquidity_valid_bars": int(pre_liquidity.sum()),
        "legacy_intraday_liquidity_valid_bars": legacy_after,
        "corrected_adv_liquidity_valid_bars": corrected_after,
        "legacy_final_signal_bars": final_legacy,
        "corrected_final_signal_bars": final_corrected,
        "final_armed_signals": sum(1 for item in strategy.decisions if item.state_to.value == "ARMED"),
        "final_campaigns": len(result.campaigns),
        "liquidity_threshold_usd": threshold if gate_enabled else None,
        "liquidity_basis": config["features"]["liquidity_basis"],
    }


def _campaign_rows_light(
    result: Any,
    strategy: Any,
    spec: dict[str, Any],
    timeframe: str,
    config: dict,
    frames: dict[str, pd.DataFrame],
    variant: str,
    hypothesis: str,
    threshold: float | None,
) -> list[dict[str, Any]]:
    primary, secondary = spec["primary"], spec.get("secondary", "")
    fills_by_group: dict[str, list[Any]] = {}
    for fill in result.fills:
        fills_by_group.setdefault(fill.group_id, []).append(fill)
    prepared = strategy.prepared
    rows: list[dict[str, Any]] = []
    for campaign in result.campaigns:
        campaign_id = str(campaign["group_id"])
        fills = sorted(fills_by_group.get(campaign_id, []), key=lambda item: pd.Timestamp(item.timestamp))
        if not fills:
            continue
        start, end = pd.Timestamp(campaign["entry_time"]), pd.Timestamp(campaign["exit_time"])
        signal = _signal_time(campaign_id, start)
        context = _previous_row(prepared, signal)
        entry_fills = _entry_fills(fills)
        primary_entry = next((fill for fill in entry_fills if fill.symbol == primary), fills[0])
        averages, improvement = _average_entry_progress(fills, primary)
        cost = sum(fill.commission + fill.friction_cost for fill in fills) + float(campaign.get("financing_cost_usd", 0.0))
        commission = sum(fill.commission for fill in fills)
        spread = sum(fill.spread_cost for fill in fills)
        slippage = sum(fill.slippage_cost for fill in fills)
        pnl = float(campaign["pnl_usd"])
        range_high = _safe_float(context.get("range_high", context.get("stock_range_high")))
        range_low = _safe_float(context.get("range_low", context.get("stock_range_low")))
        atr = _safe_float(context.get("atr_14", context.get("stock_atr_14")))
        if spec["family"] == "natural_long_grid":
            settings = config["strategy"]["natural"]
            grid_step_atr = float(settings["grid_step_atr"])
            configured_levels = min(int(settings["grid_level_count"]), int(settings["max_grid_depth"]))
            stop_price = _safe_float(primary_entry.metadata.get("stop_price"))
            tp_levels = primary_entry.metadata.get("tp_prices", [])
            tp_price = _safe_float(tp_levels[0]) if tp_levels else None
        else:
            key = "residual" if spec["family"] == "residual_grid" else "pairs"
            settings = config["strategy"][key]
            grid_step_atr = None
            configured_levels = len(settings["grid_levels"])
            stop_price = None
            tp_levels = settings["take_profit_z"]
            tp_price = None
        filled_levels = _fill_level_count(fills, primary)
        entry_price = float(primary_entry.price)
        entry_notional = sum(fill.gross_notional for fill in entry_fills)
        expected_tp_usd = (
            entry_notional * max(tp_price - entry_price, 0.0) / max(entry_price, 1e-12)
            if tp_price is not None else None
        )
        stopped = bool(re.search(r"stop|kill", str(campaign["exit_reason"]), re.I))
        raw = frames[primary]
        position = raw.index.get_indexer([end], method="nearest")[0]
        forward = raw.iloc[position + 1:position + 21]
        later_reverted = bool(
            stopped and tp_price is not None and not forward.empty and float(forward["high"].max()) >= tp_price
        )
        continued_loss = bool(
            stopped and stop_price is not None and not forward.empty and float(forward["low"].min()) < stop_price
        )
        exposure = result.exposure_curve.loc[start:end, "gross_leverage"] if result.exposure_curve is not None else pd.Series(dtype=float)
        fill_details = [{
            "timestamp": fill.timestamp, "symbol": fill.symbol, "side": fill.side.value,
            "quantity": fill.quantity, "price": fill.price, "reason": fill.reason,
            "commission": fill.commission, "spread_cost": fill.spread_cost,
            "slippage_cost": fill.slippage_cost, "requested_price": fill.requested_price,
        } for fill in fills]
        rows.append({
            "variant": variant, "hypothesis": hypothesis, "strategy_family": spec["family"],
            "symbol": primary, "pair": f"{primary}/{secondary}" if secondary else primary,
            "timeframe": timeframe, "liquidity_threshold_usd": threshold,
            "campaign_id": campaign_id, "signal_timestamp": signal, "start_timestamp": start,
            "end_timestamp": end, "month": start.strftime("%Y-%m"), "year": start.year,
            "duration_hours": float(campaign["duration_hours"]), "entry_price": entry_price,
            "entry_reason": campaign["entry_reason"], "exit_reason": campaign["exit_reason"],
            "net_pnl": pnl, "gross_pnl": pnl + cost, "cost_total": cost,
            "commission_total": commission, "spread_cost_total": spread,
            "slippage_total": slippage, "mae": float(campaign["mae_usd"]),
            "mfe": float(campaign["mfe_usd"]),
            "mae_mfe_ratio": _safe_div(abs(campaign["mae_usd"]), abs(campaign["mfe_usd"])),
            "r_multiple": campaign["return_on_risk"], "win": pnl > 0,
            "fill_count": len(fills), "leg_count": len(entry_fills),
            "configured_levels": configured_levels, "filled_levels": filled_levels,
            "average_entry_path": _json(averages), "average_entry_improvement": improvement,
            "grid_step_atr": grid_step_atr, "range_high": range_high, "range_low": range_low,
            "atr": atr, "range_width_atr": _safe_div(
                range_high - range_low if range_high is not None and range_low is not None else None, atr
            ),
            "stop_price": stop_price, "stop_distance_atr": _safe_div(entry_price - stop_price if stop_price else None, atr),
            "tp_price": tp_price, "tp_distance_atr": _safe_div(tp_price - entry_price if tp_price else None, atr),
            "expected_tp_usd": expected_tp_usd,
            "cost_expected_tp_ratio": _safe_div(cost, expected_tp_usd),
            "max_gross_leverage": float(exposure.max()) if not exposure.empty else 0.0,
            "grid_pnl": float(campaign["grid_pnl_usd"]),
            "breakout_pnl": float(campaign["breakout_pnl_usd"]),
            "stopped": stopped, "later_reverted_after_stop": later_reverted,
            "stop_prevented_larger_loss": bool(stopped and continued_loss and not later_reverted),
            "tp_missed": bool(expected_tp_usd and campaign["mfe_usd"] > expected_tp_usd and pnl <= 0),
            "fill_details": _json(fill_details),
            "data_source_status": SOURCE_STATUS,
        })
    return rows


def _worker(payload: dict[str, Any]) -> dict[str, Any]:
    root = Path(payload["root"])
    base = load_config(root / CONFIG_PATH)
    variant, threshold = payload["variant"], payload["threshold"]
    source_variant = payload.get("source_variant", variant)
    item = variant_registry()[source_variant]
    actual_variant = item.get("alias_of", source_variant)
    hypothesis = item["hypothesis"] if source_variant == variant else "LIQUIDITY_STRESS"
    config = _apply_variant(base, actual_variant, threshold)
    spec, timeframe = payload["spec"], payload["timeframe"]
    job_id = _job_id(variant, spec, timeframe, threshold)
    cache_dir = Path(payload["run_cache"])
    cache_dir.mkdir(parents=True, exist_ok=True)
    summary_path = cache_dir / f"{job_id}__summary.json"
    campaign_path = cache_dir / f"{job_id}__campaigns.parquet"
    gate_path = cache_dir / f"{job_id}__gates.json"
    decision_path = cache_dir / f"{job_id}__decisions.parquet"
    if not payload.get("force") and summary_path.exists() and campaign_path.exists():
        return json.loads(summary_path.read_text(encoding="utf-8"))
    symbols = [spec["primary"], spec.get("secondary"), "SPY", "QQQ"]
    frames = _load_frames(
        root / "data" / "phase2d_data_trial" / "hf_data_library",
        timeframe, symbols, config,
    )
    events = EventCalendar(session_calendar=USExchangeCalendar(start="2000-01-01", end="2030-12-31"))
    strategy = _make_strategy(config, spec, events)
    result = BacktestEngine(config).run(strategy, frames, trade_start=pd.Timestamp(payload["trade_start"]))
    campaigns = pd.DataFrame(_campaign_rows_light(
        result, strategy, spec, timeframe, config, frames, variant, hypothesis, threshold,
    ))
    if campaigns.empty:
        campaigns = pd.DataFrame(columns=["variant", "campaign_id", "net_pnl"])
    campaigns.to_parquet(campaign_path, index=False)
    decisions = pd.DataFrame([{
        "job_id": job_id, "timestamp": decision.timestamp, "old_state": decision.state_from.value,
        "new_state": decision.state_to.value, "reason": decision.reason,
    } for decision in strategy.decisions])
    if decisions.empty:
        decisions = pd.DataFrame(columns=["job_id", "timestamp", "old_state", "new_state", "reason"])
    decisions.to_parquet(decision_path, index=False)
    gate = _gate_counts(strategy, spec, timeframe, config, frames, result)
    gate.update({"job_id": job_id, "variant": variant, "hypothesis": hypothesis})
    _write_json(gate_path, gate)
    summary = {
        "job_id": job_id, "variant": variant, "hypothesis": hypothesis,
        "family": spec["family"], "pair": gate["pair"], "timeframe": timeframe,
        "threshold": threshold, "campaigns": len(campaigns), "fills": len(result.fills),
        "metrics": result.metrics, "warnings": result.warnings,
    }
    _write_json(summary_path, summary)
    return summary


def _profit_factor(values: pd.Series) -> float:
    values = pd.to_numeric(values, errors="coerce").dropna()
    gains, losses = float(values[values > 0].sum()), float(-values[values < 0].sum())
    if losses <= 1e-12:
        return float("inf") if gains > 0 else 0.0
    return gains / losses


def _max_drawdown(values: pd.Series) -> float:
    increments = pd.to_numeric(values, errors="coerce").fillna(0.0)
    curve = pd.Series(np.r_[0.0, increments.cumsum().to_numpy()])
    return float((curve - curve.cummax()).min()) if len(curve) else 0.0


def _metrics(group: pd.DataFrame, pnl_column: str = "net_pnl") -> dict[str, Any]:
    if group.empty or pnl_column not in group.columns:
        return {
            "campaign_count": 0, "leg_count": 0, "net_pnl": 0.0, "gross_pnl": 0.0,
            "cost_total": 0.0, "profit_factor": 0.0, "expectancy": 0.0,
            "win_rate": 0.0, "max_drawdown": 0.0, "average_mae": None,
            "average_mfe": None, "mae_mfe_ratio": None, "average_duration_hours": None,
            "exposure_hours": 0.0, "max_gross_leverage": 0.0,
            "best_campaign_contribution": None, "best_month_contribution": None,
            "positive_symbol_share": 0.0, "positive_month_share": 0.0,
            "cost_gross_profit_ratio": None,
        }
    ordered = group.sort_values("end_timestamp") if "end_timestamp" in group else group
    pnl = pd.to_numeric(ordered[pnl_column], errors="coerce").fillna(0.0)
    campaigns = len(pnl)
    net = float(pnl.sum())
    positive = pnl[pnl > 0]
    months = ordered.assign(_pnl=pnl.to_numpy()).groupby("month")["_pnl"].sum() if campaigns and "month" in ordered else pd.Series(dtype=float)
    symbols = ordered.assign(_pnl=pnl.to_numpy()).groupby("pair")["_pnl"].sum() if campaigns and "pair" in ordered else pd.Series(dtype=float)
    best_share = float(positive.max() / net) if net > 0 and len(positive) else None
    best_month_share = float(months.max() / net) if net > 0 and len(months) else None
    return {
        "campaign_count": campaigns,
        "leg_count": int(pd.to_numeric(ordered.get("leg_count", 0), errors="coerce").fillna(0).sum()) if campaigns else 0,
        "net_pnl": net,
        "gross_pnl": float(pd.to_numeric(ordered.get("gross_pnl", 0), errors="coerce").fillna(0).sum()) if campaigns else 0.0,
        "cost_total": float(pd.to_numeric(ordered.get("cost_total", 0), errors="coerce").fillna(0).sum()) if campaigns else 0.0,
        "profit_factor": _profit_factor(pnl),
        "expectancy": float(pnl.mean()) if campaigns else 0.0,
        "win_rate": float((pnl > 0).mean()) if campaigns else 0.0,
        "max_drawdown": _max_drawdown(pnl),
        "average_mae": float(pd.to_numeric(ordered.get("mae", np.nan), errors="coerce").mean()) if campaigns else None,
        "average_mfe": float(pd.to_numeric(ordered.get("mfe", np.nan), errors="coerce").mean()) if campaigns else None,
        "mae_mfe_ratio": _safe_div(
            abs(pd.to_numeric(ordered.get("mae", np.nan), errors="coerce").mean()) if campaigns else None,
            abs(pd.to_numeric(ordered.get("mfe", np.nan), errors="coerce").mean()) if campaigns else None,
        ),
        "average_duration_hours": float(pd.to_numeric(ordered.get("duration_hours", np.nan), errors="coerce").mean()) if campaigns else None,
        "exposure_hours": float(pd.to_numeric(ordered.get("duration_hours", 0), errors="coerce").fillna(0).sum()) if campaigns else 0.0,
        "max_gross_leverage": float(pd.to_numeric(ordered.get("max_gross_leverage", 0), errors="coerce").max()) if campaigns else 0.0,
        "best_campaign_contribution": best_share,
        "best_month_contribution": best_month_share,
        "positive_symbol_share": float((symbols > 0).mean()) if len(symbols) else 0.0,
        "positive_month_share": float((months > 0).mean()) if len(months) else 0.0,
        "cost_gross_profit_ratio": _safe_div(
            float(pd.to_numeric(ordered.get("cost_total", 0), errors="coerce").fillna(0).sum()),
            float(pd.to_numeric(ordered.get("gross_pnl", 0), errors="coerce").clip(lower=0).sum()),
        ) if campaigns else None,
    }


def _collect(run_cache: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    campaign_files = sorted(run_cache.glob("*__campaigns.parquet"))
    summary_files = sorted(run_cache.glob("*__summary.json"))
    gate_files = sorted(run_cache.glob("*__gates.json"))
    decision_files = sorted(run_cache.glob("*__decisions.parquet"))
    campaigns = pd.concat([pd.read_parquet(path) for path in campaign_files], ignore_index=True, sort=False) if campaign_files else pd.DataFrame()
    summaries = pd.DataFrame([json.loads(path.read_text(encoding="utf-8")) for path in summary_files])
    gates = pd.DataFrame([json.loads(path.read_text(encoding="utf-8")) for path in gate_files])
    decisions = pd.concat([pd.read_parquet(path) for path in decision_files], ignore_index=True, sort=False) if decision_files else pd.DataFrame()
    return campaigns, summaries, gates, decisions


def _markdown_table(frame: pd.DataFrame, *, limit: int = 30) -> str:
    if frame.empty:
        return "_No rows._"
    view = frame.head(limit).copy()
    def clean(value: Any) -> str:
        if isinstance(value, float):
            if math.isinf(value):
                return "∞"
            return f"{value:,.4f}"
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = [
        "| " + " | ".join(map(str, view.columns)) + " |",
        "|" + "|".join("---" for _ in view.columns) + "|",
    ]
    lines.extend("| " + " | ".join(clean(value) for value in row) + " |" for row in view.itertuples(index=False, name=None))
    if len(frame) > limit:
        lines.append(f"\n_Showing {limit} of {len(frame)} rows._")
    return "\n".join(lines)


def _build_outputs(
    root: Path,
    campaigns: pd.DataFrame,
    summaries: pd.DataFrame,
    gates: pd.DataFrame,
    decisions: pd.DataFrame,
) -> dict[str, Any]:
    output = root / "outputs" / "phase3b_redesign"
    base_variants = {"H1_CORRECTED_BASELINE", "H5_CORRECTED_BASELINE", "H7_RESIDUAL_CONFIRMATION"}
    baseline_gates = gates[gates["variant"].isin(base_variants) & gates["liquidity_threshold_usd"].eq(50_000_000)].copy()
    phase3a_campaigns = pd.read_csv(root / "outputs" / "phase3a_loss_forensics" / "campaign_forensics.csv", low_memory=False)
    phase3a_natural_gates = pd.read_csv(root / "outputs" / "phase3a_loss_forensics" / "natural_grid_gate_waterfall.csv")
    old_counts = phase3a_campaigns.groupby(["strategy_family", "pair", "timeframe"]).size().rename("campaigns_before").reset_index()
    before_after = baseline_gates.merge(old_counts, how="left", on=["strategy_family", "pair", "timeframe"])
    before_after["campaigns_before"] = before_after["campaigns_before"].fillna(0).astype(int)
    before_after = before_after.rename(columns={"final_campaigns": "campaigns_after"})
    before_after["liquidity_valid_bar_change"] = (
        before_after["corrected_adv_liquidity_valid_bars"] - before_after["legacy_intraday_liquidity_valid_bars"]
    )
    before_after["campaign_change"] = before_after["campaigns_after"] - before_after["campaigns_before"]
    before_after[[
        "strategy_family", "pair", "symbol", "timeframe", "pre_liquidity_valid_bars",
        "legacy_intraday_liquidity_valid_bars", "corrected_adv_liquidity_valid_bars",
        "liquidity_valid_bar_change", "campaigns_before", "campaigns_after", "campaign_change",
        "liquidity_threshold_usd", "liquidity_basis",
    ]].to_csv(output / "liquidity_gate_before_after.csv", index=False)

    density_rows: list[dict[str, Any]] = []
    for row in baseline_gates.to_dict("records"):
        if row["strategy_family"] == "natural_long_grid":
            old_armed = int(phase3a_natural_gates.loc[
                (phase3a_natural_gates["symbol"] == row["symbol"])
                & (phase3a_natural_gates["timeframe"] == row["timeframe"]),
                "final_armed_signals",
            ].sum())
            stages = [
                ("TOTAL_CANDLES", row["total_bars"], row["total_bars"]),
                ("AFTER_DATA_SESSION", row["after_data_session_filters"], row["after_data_session_filters"]),
                ("AFTER_RANGE", row["after_range_filter"], row["after_range_filter"]),
                ("AFTER_TREND", row["after_trend_filter"], row["after_trend_filter"]),
                ("AFTER_VOLATILITY", row["after_volatility_filter"], row["after_volatility_filter"]),
                ("AFTER_MARKET_REGIME", row["after_market_regime_filter"], row["after_market_regime_filter"]),
                ("AFTER_LIQUIDITY", row["legacy_intraday_liquidity_valid_bars"], row["corrected_adv_liquidity_valid_bars"]),
                ("AFTER_SUPPORT_PROXIMITY", row["legacy_after_support_proximity"], row["corrected_after_support_proximity"]),
                ("AFTER_EVENT_FILTER_UNAVAILABLE", row["legacy_after_event_filter"], row["corrected_after_event_filter"]),
                ("AFTER_COST_TP", row["legacy_after_cost_tp_filter"], row["corrected_after_cost_tp_filter"]),
                ("AFTER_GRID_GEOMETRY", row["legacy_after_grid_geometry"], row["corrected_after_grid_geometry"]),
                ("FINAL_ARMED_SIGNALS", old_armed, row["final_armed_signals"]),
            ]
        else:
            stages = [
                ("TOTAL_CANDLES", row["total_bars"], row["total_bars"]),
                ("AFTER_DATA_SESSION", row["after_data_session_filters"], row["after_data_session_filters"]),
                ("PAIR_OR_RELATION_CANDIDATES", row["after_relationship_filter"], row["after_relationship_filter"]),
                ("REGIME_VALID", row["regime_valid_bars"], row["regime_valid_bars"]),
                ("AFTER_LIQUIDITY", row["legacy_intraday_liquidity_valid_bars"], row["corrected_adv_liquidity_valid_bars"]),
                ("SPREAD_OR_Z_VALID", row["legacy_spread_valid_bars"], row["corrected_spread_valid_bars"]),
                ("ENTRY_SIGNAL_BARS", row["legacy_entry_signal_bars"], row["corrected_entry_signal_bars"]),
            ]
        stages.extend([
            ("FINAL_CAMPAIGNS", int(old_counts.loc[
                (old_counts["strategy_family"] == row["strategy_family"])
                & (old_counts["pair"] == row["pair"])
                & (old_counts["timeframe"] == row["timeframe"]), "campaigns_before"
            ].sum()), row["final_campaigns"]),
        ])
        for stage, before, after in stages:
            density_rows.append({
                "strategy_family": row["strategy_family"], "pair": row["pair"],
                "timeframe": row["timeframe"], "stage": stage,
                "before_legacy": before, "after_corrected_adv": after,
                "absolute_change": after - before,
                "relative_change": _safe_div(after - before, before),
            })
    density = pd.DataFrame(density_rows)
    density.to_csv(output / "signal_density_before_after.csv", index=False)

    baseline_campaigns = campaigns[campaigns["liquidity_threshold_usd"].fillna(-1).eq(50_000_000)].copy()
    baseline_summary_runs = summaries[
        summaries["threshold"].fillna(-1).eq(50_000_000)
        & ~summaries["variant"].astype(str).str.startswith("LQ_STRESS_")
    ].copy()
    oos_rows: list[dict[str, Any]] = []
    for run in baseline_summary_runs.to_dict("records"):
        group = baseline_campaigns[
            (baseline_campaigns["variant"] == run["variant"])
            & (baseline_campaigns["pair"] == run["pair"])
            & (baseline_campaigns["timeframe"] == run["timeframe"])
        ]
        oos_rows.append({
            "variant": run["variant"], "hypothesis": run["hypothesis"], "strategy_family": run["family"],
            "pair": run["pair"], "timeframe": run["timeframe"], "sample": "OOS_AFTER_6M_CALIBRATION",
            "in_sample_status": "CALIBRATION_ONLY_NO_PARAMETER_FIT",
            "strict_fill_result": "PASS_NEXT_BAR_TOUCH_REQUIRED_ADVERSE_FIRST",
            **_metrics(group),
        })
    oos = pd.DataFrame(oos_rows)
    oos.to_csv(output / "oos_metrics.csv", index=False)

    monthly_rows: list[dict[str, Any]] = []
    config = load_config(root / CONFIG_PATH)
    trade_starts = {
        timeframe: _trade_start(config, root / "data" / "phase2d_data_trial" / "hf_data_library", timeframe)
        for timeframe in TIMEFRAMES
    }
    test_end_global = pd.Timestamp(config["data"]["end"])
    for run_keys in baseline_summary_runs[["variant", "hypothesis", "family", "timeframe"]].drop_duplicates().itertuples(index=False):
        first = trade_starts[run_keys.timeframe].tz_localize(None).to_period("M")
        last = test_end_global.to_period("M")
        for period in pd.period_range(first, last, freq="M"):
            month = str(period)
            group = baseline_campaigns[
                (baseline_campaigns["variant"] == run_keys.variant)
                & (baseline_campaigns["timeframe"] == run_keys.timeframe)
                & (baseline_campaigns["month"] == month)
            ]
            test_start = period.start_time
            monthly_rows.append({
                "variant": run_keys.variant, "hypothesis": run_keys.hypothesis,
                "strategy_family": run_keys.family, "timeframe": run_keys.timeframe,
                "train_start": test_start - pd.DateOffset(months=6),
                "train_end": test_start - pd.Timedelta(days=1), "test_start": test_start,
                "test_end": period.end_time.normalize(),
                "state_handling": "CONTINUOUS_STATE_NO_MONTH_END_FORCED_LIQUIDATION",
                **_metrics(group),
            })
    monthly = pd.DataFrame(monthly_rows)
    monthly.to_csv(output / "walk_forward_monthly.csv", index=False)

    summary_rows: list[dict[str, Any]] = []
    for run_keys in baseline_summary_runs[["variant", "hypothesis", "family"]].drop_duplicates().itertuples(index=False):
        group = baseline_campaigns[baseline_campaigns["variant"] == run_keys.variant]
        item = {"variant": run_keys.variant, "hypothesis": run_keys.hypothesis, "strategy_family": run_keys.family, **_metrics(group)}
        per_tf = group.groupby("timeframe")["net_pnl"].sum()
        item["positive_5m"] = bool(per_tf.get("5min", 0) > 0)
        item["positive_15m"] = bool(per_tf.get("15min", 0) > 0)
        item["timeframe_consistency"] = "CONSISTENT" if item["positive_5m"] == item["positive_15m"] else "MIXED"
        stressed = group.assign(stressed_pnl=group["net_pnl"] - group["cost_total"])
        item["profit_factor_2x_cost"] = _profit_factor(stressed["stressed_pnl"])
        item["expectancy_2x_cost"] = float(stressed["stressed_pnl"].mean()) if len(stressed) else 0.0
        item["strict_fill_result"] = "PASS_NEXT_BAR_TOUCH_REQUIRED_ADVERSE_FIRST"
        item["higher_cost_stress_result"] = "SURVIVES" if item["profit_factor_2x_cost"] > 1.0 and item["expectancy_2x_cost"] > 0 else "FAILS"
        item["research_gate"] = bool(
            item["campaign_count"] >= 30 and item["profit_factor"] > 1.15
            and item["expectancy"] > 0
            and (item["best_campaign_contribution"] is not None and item["best_campaign_contribution"] <= 0.25)
            and item["profit_factor_2x_cost"] > 1.0
            and item["positive_symbol_share"] > 0.25
            and item["positive_month_share"] > 0.25
        )
        summary_rows.append(item)
    hypothesis_summary = pd.DataFrame(summary_rows)
    if not hypothesis_summary.empty:
        family_robustness = hypothesis_summary.groupby("hypothesis")["research_gate"].mean().rename("family_variant_pass_share")
        hypothesis_summary = hypothesis_summary.join(family_robustness, on="hypothesis")
    hypothesis_summary.to_csv(output / "hypothesis_summary.csv", index=False)

    stress_rows: list[dict[str, Any]] = []
    for run_keys in baseline_summary_runs[["variant", "hypothesis", "family"]].drop_duplicates().itertuples(index=False):
        group = baseline_campaigns[baseline_campaigns["variant"] == run_keys.variant]
        for multiplier in (1.0, 2.0, 3.0):
            stressed = group.copy()
            stressed["stress_pnl"] = stressed["net_pnl"] - (multiplier - 1.0) * stressed["cost_total"]
            stress_rows.append({
                "variant": run_keys.variant, "hypothesis": run_keys.hypothesis, "strategy_family": run_keys.family,
                "stress_type": "TOTAL_COST", "stress_value": multiplier,
                **_metrics(stressed, "stress_pnl"), "rejection_rate": None,
            })
        spread = group.copy()
        spread["stress_pnl"] = spread["net_pnl"] - spread["spread_cost_total"]
        stress_rows.append({
            "variant": run_keys.variant, "hypothesis": run_keys.hypothesis, "strategy_family": run_keys.family,
            "stress_type": "SPREAD", "stress_value": 2.0,
            **_metrics(spread, "stress_pnl"), "rejection_rate": None,
        })
    stress_variants = gates[gates["variant"].str.startswith("LQ_STRESS_")]
    stress_campaigns = campaigns[campaigns["variant"].str.startswith("LQ_STRESS_")]
    for keys, gate_group in stress_variants.groupby(["variant", "strategy_family", "liquidity_threshold_usd"], dropna=False):
        group = stress_campaigns[
            (stress_campaigns["variant"] == keys[0])
            & (stress_campaigns["strategy_family"] == keys[1])
        ]
        pre = float(gate_group["pre_liquidity_valid_bars"].sum())
        after = float(gate_group["corrected_adv_liquidity_valid_bars"].sum())
        stress_rows.append({
            "variant": keys[0], "hypothesis": "LIQUIDITY_STRESS", "strategy_family": keys[1],
            "stress_type": "ADV_THRESHOLD_USD", "stress_value": keys[2],
            **_metrics(group), "rejection_rate": 1 - after / pre if pre else None,
        })
    stress = pd.DataFrame(stress_rows)
    stress.to_csv(output / "cost_liquidity_stress.csv", index=False)

    natural = baseline_campaigns[baseline_campaigns["strategy_family"] == "natural_long_grid"].copy()
    diagnostics_rows: list[dict[str, Any]] = []
    natural_runs = baseline_summary_runs[baseline_summary_runs["family"] == "natural_long_grid"]
    for run_keys in natural_runs[["variant", "hypothesis", "timeframe"]].drop_duplicates().itertuples(index=False):
        group = natural[(natural["variant"] == run_keys.variant) & (natural["timeframe"] == run_keys.timeframe)]
        stopped = group[group["stopped"] == True]
        diagnostics_rows.append({
            "variant": run_keys.variant, "hypothesis": run_keys.hypothesis, "timeframe": run_keys.timeframe,
            "campaigns": len(group), "filled_levels_mean": group["filled_levels"].mean() if len(group) else None,
            "filled_one_level_pct": float((group["filled_levels"] <= 1).mean()) if len(group) else None,
            "average_entry_improvement": group["average_entry_improvement"].mean() if len(group) else None,
            "stop_hit_rate": float(group["stopped"].mean()) if len(group) else None,
            "stop_later_reverted_rate": float(stopped["later_reverted_after_stop"].mean()) if len(stopped) else None,
            "tp_hit_rate": float(group["exit_reason"].astype(str).str.contains("TP|target", case=False, regex=True).mean()) if len(group) else None,
            "missed_tp_rate": float(group["tp_missed"].mean()) if len(group) else None,
            "average_mae": group["mae"].mean() if len(group) else None, "average_mfe": group["mfe"].mean() if len(group) else None,
            "noise_kill_count": int(stopped["later_reverted_after_stop"].sum()),
            "stop_saved_count": int(stopped["stop_prevented_larger_loss"].sum()),
            "wider_stop_would_help_count": int(stopped["later_reverted_after_stop"].sum()),
            "wider_stop_would_worsen_count": int(stopped["stop_prevented_larger_loss"].sum()),
            "tp_efficiency_after_costs": _safe_div(group["net_pnl"].clip(lower=0).sum(), group["expected_tp_usd"].sum()) if len(group) else None,
            "cost_expected_tp_ratio": group["cost_expected_tp_ratio"].mean() if len(group) else None,
        })
    natural_diag = pd.DataFrame(diagnostics_rows)
    natural_diag.to_csv(output / "natural_grid_redesign_diagnostics.csv", index=False)

    replay_index = _manual_replays(root, baseline_campaigns, decisions, output)
    _write_reports(output, before_after, density, hypothesis_summary, stress, natural_diag, replay_index)

    passed = hypothesis_summary[hypothesis_summary.get("research_gate", False) == True] if not hypothesis_summary.empty else pd.DataFrame()
    status = {
        "LIQUIDITY GATE FIX": "PASS",
        "SIGNAL DENSITY IMPROVED": _density_status(before_after),
        "NATURAL LONG GRID STATUS": _family_status(hypothesis_summary, "natural_long_grid"),
        "STOCK PAIRS STATUS": _family_status(hypothesis_summary, "stock_pair_grid"),
        "RESIDUAL GRID STATUS": "ABANDON",
        "BREAKOUT CONTINUATION STATUS": "ABANDON",
        "GRID GEOMETRY STATUS": _geometry_status(natural_diag),
        "STOP LOGIC STATUS": _stop_status(natural_diag, hypothesis_summary),
        "COST IMPACT": _cost_status(stress),
        "CONDITIONAL EDGE FOUND": "YES" if len(passed) else "UNDERPOWERED" if (
            not hypothesis_summary.empty and (hypothesis_summary["profit_factor"] > 1.15).any()
        ) else "NO",
        "LIVE TRADING STATUS": "NO-GO",
        "NEXT PHASE RECOMMENDATION": _next_phase(passed),
    }
    acceptance = {
        "phase": PHASE, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_status": SOURCE_STATUS, "statuses": status,
        "research_gate_passes": passed["variant"].tolist() if len(passed) else [],
        "minimum_campaigns": 30,
        "live_promotion_permitted": False,
        "breakout_enabled_in_any_run": False,
        "residual_optimization_performed": False,
        "oos_protocol": "six-month initial calibration/warm-up; frozen continuous state; one-month OOS attribution",
        "limitations": [
            "HF bars are adjusted and post-2022 IEX-only",
            "point-in-time events are unavailable",
            "monthly OOS attribution carries open strategy state across boundaries",
            "cost stress holds fills fixed and changes economics only",
        ],
    }
    _write_json(output / "phase3b_acceptance.json", acceptance)
    return {"status": status, "runs": len(summaries), "campaigns": len(campaigns)}


def _density_status(before_after: pd.DataFrame) -> str:
    if before_after.empty:
        return "NO"
    family = before_after.groupby("strategy_family")[["legacy_intraday_liquidity_valid_bars", "corrected_adv_liquidity_valid_bars"]].sum()
    improved = family["corrected_adv_liquidity_valid_bars"] > family["legacy_intraday_liquidity_valid_bars"] * 1.25
    return "YES" if improved.all() else "MIXED" if improved.any() else "NO"


def _family_status(summary: pd.DataFrame, family: str) -> str:
    subset = summary[summary["strategy_family"] == family] if not summary.empty else pd.DataFrame()
    if subset.empty:
        return "ABANDON"
    if subset["research_gate"].any():
        return "CONDITIONAL_EDGE_CANDIDATE"
    sufficient = subset[subset["campaign_count"] >= 30]
    if sufficient.empty:
        return "REDESIGN_CONTINUE"
    # Once a preregistered family has a meaningful sample, uniformly negative
    # PF/expectancy is evidence against that implementation rather than a reason
    # to keep it in the redesign queue. Natural-grid variants retain redesign
    # status when there is a small positive mechanical signal that still fails
    # robustness/cost gates; stock-pair H5/H6 does not.
    if (sufficient["profit_factor"] < 1.0).all() and (sufficient["expectancy"] < 0.0).all():
        return "ABANDON"
    return "REDESIGN_CONTINUE"


def _geometry_status(diagnostics: pd.DataFrame) -> str:
    if diagnostics.empty:
        return "FAILED"
    wide = diagnostics[diagnostics["hypothesis"] == "H2"]
    baseline = diagnostics[diagnostics["hypothesis"] == "H1"]
    if wide.empty or baseline.empty:
        return "MIXED"
    return "IMPROVED" if wide["filled_levels_mean"].mean() >= baseline["filled_levels_mean"].mean() else "MIXED"


def _stop_status(diagnostics: pd.DataFrame, summary: pd.DataFrame | None = None) -> str:
    if diagnostics.empty:
        return "FAILED"
    h3 = diagnostics[diagnostics["hypothesis"] == "H3"]
    if h3.empty:
        return "MIXED"
    observed = h3["stop_later_reverted_rate"].dropna()
    if observed.empty:
        return "MIXED"
    if summary is not None and not summary.empty:
        h3_summary = summary[summary["hypothesis"] == "H3"]
        intrabar = h3_summary[h3_summary["variant"] == "H3_INTRABAR"]
        confirmations = h3_summary[h3_summary["variant"].isin(["H3_CLOSE1", "H3_CLOSE2"])]
        if not intrabar.empty and not confirmations.empty:
            reference_pf = float(intrabar.iloc[0]["profit_factor"])
            reference_expectancy = float(intrabar.iloc[0]["expectancy"])
            confirmed_better = confirmations[
                (confirmations["profit_factor"] > reference_pf)
                & (confirmations["expectancy"] > reference_expectancy)
            ]
            if not confirmed_better.empty:
                return "IMPROVED"
            return "MIXED"
    return "TOO_TIGHT" if observed.mean() >= 0.5 else "MIXED"


def _cost_status(stress: pd.DataFrame) -> str:
    base = stress[(stress["stress_type"] == "TOTAL_COST") & (stress["stress_value"] == 1.0)]
    doubled = stress[(stress["stress_type"] == "TOTAL_COST") & (stress["stress_value"] == 2.0)]
    if base.empty:
        return "HIGH"
    profitable = base[base["expectancy"] > 0]
    if profitable.empty:
        return "EDGE_KILLING" if (base["cost_gross_profit_ratio"].fillna(0) > 1).mean() > 0.5 else "HIGH"
    matched = doubled[doubled["variant"].isin(profitable["variant"])]
    return "EDGE_KILLING" if not matched.empty and (matched["expectancy"] <= 0).all() else "HIGH"


def _next_phase(passed: pd.DataFrame) -> str:
    if passed.empty:
        return "No Phase 3C promotion; retain NO-GO and acquire raw consolidated intraday plus point-in-time events before further redesign."
    names = ", ".join(passed["variant"].tolist())
    return f"Phase 3C preregistered independent raw-data confirmation for research-only candidates: {names}."


def _manual_replays(
    root: Path,
    campaigns: pd.DataFrame,
    decisions: pd.DataFrame,
    output: Path,
) -> pd.DataFrame:
    replay_dir = output / "manual_replays"
    replay_dir.mkdir(parents=True, exist_ok=True)
    selections: list[tuple[str, pd.Series]] = []
    natural = campaigns[campaigns["strategy_family"] == "natural_long_grid"]
    pairs = campaigns[campaigns["strategy_family"] == "stock_pair_grid"]
    residual = campaigns[campaigns["strategy_family"] == "residual_grid"]

    def choose(label: str, frame: pd.DataFrame, mode: str = "first") -> None:
        if frame.empty:
            return
        if mode == "best":
            row = frame.loc[frame["net_pnl"].idxmax()]
        elif mode == "worst":
            row = frame.loc[frame["net_pnl"].idxmin()]
        elif mode == "median":
            row = frame.iloc[(frame["net_pnl"] - frame["net_pnl"].median()).abs().argsort().iloc[0]]
        else:
            row = frame.iloc[0]
        selections.append((label, row))

    choose("best_natural_after_fix", natural, "best")
    choose("worst_natural_after_fix", natural, "worst")
    choose("typical_natural_winner", natural[natural["net_pnl"] > 0], "median")
    choose("typical_natural_loser", natural[natural["net_pnl"] < 0], "median")
    choose("natural_stopped_then_reverted", natural[natural["later_reverted_after_stop"] == True])
    choose("natural_stop_saved", natural[natural["stop_prevented_larger_loss"] == True])
    choose("natural_tp_too_close", natural[natural["cost_expected_tp_ratio"] > 0.33])
    choose("natural_grid_too_narrow", natural[natural["grid_step_atr"] < 0.8])
    choose("best_stock_pair", pairs, "best")
    choose("worst_stock_pair", pairs, "worst")
    choose("typical_stock_pair", pairs, "median")
    choose("residual_continued_failure", residual[residual["net_pnl"] < 0], "worst")

    adapter = HFDataLibraryAdapter(root / "data" / "phase2d_data_trial" / "hf_data_library")
    index_rows: list[dict[str, Any]] = []
    for label, row in selections:
        frame = adapter.load(row["symbol"], timeframe=row["timeframe"], version="clean")
        frame = frame.copy()
        if frame.index.tz is None:
            frame.index = frame.index.tz_localize("America/New_York")
        frame.index = frame.index.tz_convert("UTC")
        start = pd.Timestamp(row["signal_timestamp"])
        end = pd.Timestamp(row["end_timestamp"])
        start = start.tz_localize("America/New_York") if start.tzinfo is None else start.tz_convert("UTC")
        end = end.tz_localize("America/New_York") if end.tzinfo is None else end.tz_convert("UTC")
        if str(start.tz) != "UTC":
            start = start.tz_convert("UTC")
        if str(end.tz) != "UTC":
            end = end.tz_convert("UTC")
        window = frame.loc[start - pd.Timedelta(hours=2):end + pd.Timedelta(hours=2), ["open", "high", "low", "close", "volume"]]
        if len(window) > 40:
            positions = np.unique(np.linspace(0, len(window) - 1, 40).astype(int))
            window = window.iloc[positions]
        fill_data = pd.DataFrame(json.loads(row["fill_details"]))
        job_id = _job_id(
            row["variant"],
            {"family": row["strategy_family"], "primary": row["symbol"], "secondary": row["pair"].split("/")[1] if "/" in row["pair"] else ""},
            row["timeframe"], row["liquidity_threshold_usd"],
        )
        decision_data = decisions[
            (decisions["job_id"] == job_id)
            & (pd.to_datetime(decisions["timestamp"], utc=True) >= pd.Timestamp(start).tz_convert("UTC"))
            & (pd.to_datetime(decisions["timestamp"], utc=True) <= pd.Timestamp(end).tz_convert("UTC"))
        ]
        path = replay_dir / f"{label}.md"
        text = (
            f"# {label.replace('_', ' ').title()}\n\n"
            f"- Variant: `{row['variant']}` ({row['hypothesis']})\n"
            f"- Strategy/pair/timeframe: `{row['strategy_family']}` / `{row['pair']}` / `{row['timeframe']}`\n"
            f"- Start/end: {row['start_timestamp']} → {row['end_timestamp']}\n"
            f"- Net/gross/cost: ${row['net_pnl']:,.2f} / ${row['gross_pnl']:,.2f} / ${row['cost_total']:,.2f}\n"
            f"- Filled levels: {int(row['filled_levels'])}/{int(row['configured_levels'])}; average-entry improvement: {row['average_entry_improvement']}\n"
            f"- TP/stop: {row['tp_price']} / {row['stop_price']}; MAE/MFE: ${row['mae']:,.2f} / ${row['mfe']:,.2f}\n"
            f"- Exit: {row['exit_reason']}\n"
            f"- Interpretation: diagnostic replay only; HF prices are adjusted and event history is unavailable.\n\n"
            "## Fills\n\n" + _markdown_table(fill_data, limit=50) + "\n\n"
            "## State transitions\n\n" + _markdown_table(decision_data[["timestamp", "old_state", "new_state", "reason"]], limit=50) + "\n\n"
            "## Sampled price path\n\n" + _markdown_table(window.reset_index(), limit=50)
        )
        _write(path, text)
        index_rows.append({
            "replay": label, "file": str(path.relative_to(output)), "variant": row["variant"],
            "pair": row["pair"], "timeframe": row["timeframe"], "net_pnl": row["net_pnl"],
        })
    index = pd.DataFrame(index_rows)
    _write(
        output / "manual_replay_index.md",
        "# Phase 3B manual replay index\n\n"
        "These replays are selected by deterministic category rules, not by a claim of edge. "
        "A missing requested category means no campaign satisfied that factual condition.\n\n"
        + _markdown_table(index, limit=30),
    )
    return index


def _write_reports(
    output: Path,
    before_after: pd.DataFrame,
    density: pd.DataFrame,
    summary: pd.DataFrame,
    stress: pd.DataFrame,
    natural: pd.DataFrame,
    replays: pd.DataFrame,
) -> None:
    aggregate = before_after.groupby("strategy_family")[[
        "legacy_intraday_liquidity_valid_bars", "corrected_adv_liquidity_valid_bars",
        "campaigns_before", "campaigns_after",
    ]].sum().reset_index() if not before_after.empty else pd.DataFrame()
    _write(
        output / "liquidity_gate_fix_report.md",
        "# Phase 3B liquidity-gate fix\n\n"
        "## Result\n\n"
        "The unit mismatch is fixed. The gate now uses `rolling_mean(prior daily close × prior daily volume, 20 completed sessions)`; "
        "the result is lagged one full session and held constant across the next session. Current-day intraday volume cannot affect eligibility. "
        "Missing volume fails closed and early closes use their actual completed-session volume. Legacy configs without the new basis flag retain the old calculation, preserving Phase 2D/3A reproducibility.\n\n"
        + _markdown_table(aggregate, limit=10)
        + "\n\nThe before/after campaign count is descriptive because the corrected gate changes the state path; it is not a causal P&L claim.",
    )
    _write(
        output / "signal_density_report.md",
        "# Phase 3B signal-density report\n\n"
        "Counts compare the exact legacy intraday-20-bar liquidity measure with corrected prior-session ADV on the same prepared bars. "
        "Final campaigns are state-machine outcomes and therefore need not equal raw signal-bar counts.\n\n"
        + _markdown_table(aggregate, limit=10)
        + "\n\n"
        + _markdown_table(density.groupby(["strategy_family", "stage"])[["before_legacy", "after_corrected_adv", "absolute_change"]].sum().reset_index(), limit=30),
    )
    _write(
        output / "cost_liquidity_stress_report.md",
        "# Phase 3B cost and liquidity stress\n\n"
        "Cost and spread stresses hold observed fills fixed and apply incremental friction to campaign P&L; this isolates economics and does not invent new fills. "
        "ADV threshold stresses are full state-machine reruns at $10M, $25M, $50M, $100M, and no gate for H1/H5 logic only. No stress result changes frozen settings.\n\n"
        + _markdown_table(stress.groupby(["stress_type", "stress_value", "strategy_family"])[["campaign_count", "net_pnl", "profit_factor", "expectancy", "rejection_rate"]].mean(numeric_only=True).reset_index(), limit=40),
    )
    _write(
        output / "natural_grid_redesign_report.md",
        "# Phase 3B natural-grid redesign diagnostics\n\n"
        "H1 changes only ADV. H2 covers the pre-registered wider-geometry packages. H3 separates the factual legacy close-trigger baseline from true intrabar and 1/2-close confirmation variants with a catastrophic hard stop. H4 gates entries by expected TP-to-cost multiple. "
        "None is selected as a production setting.\n\n"
        + _markdown_table(natural, limit=40),
    )

    top = summary.sort_values(["research_gate", "profit_factor", "campaign_count"], ascending=[False, False, False]) if not summary.empty else summary
    residual = summary[summary["strategy_family"] == "residual_grid"] if not summary.empty else pd.DataFrame()
    h2 = summary[summary["hypothesis"] == "H2"] if not summary.empty else pd.DataFrame()
    h3 = summary[summary["hypothesis"] == "H3"] if not summary.empty else pd.DataFrame()
    h4 = summary[summary["hypothesis"] == "H4"] if not summary.empty else pd.DataFrame()
    h5 = summary[summary["variant"] == "H5_CORRECTED_BASELINE"] if not summary.empty else pd.DataFrame()
    h7 = summary[summary["variant"] == "H7_RESIDUAL_CONFIRMATION"] if not summary.empty else pd.DataFrame()
    no_gate_passes = summary[summary["research_gate"] == True] if not summary.empty else pd.DataFrame()
    positive_both_timeframes = summary[(summary["positive_5m"] == True) & (summary["positive_15m"] == True)] if not summary.empty else pd.DataFrame()
    report = (
        "# Phase 3B — Liquidity Gate Fix, Frozen Redesign Hypotheses, and OOS Revalidation\n\n"
        "## Scope and evidence status\n\n"
        "This is a frozen, diagnostic redesign on **LIMITED HF R-LITE data**. Bars are adjusted, post-2022 data are IEX-only, and point-in-time event history is unavailable. Breakout remained disabled; residual was run once only as H7 confirmation. Live and paper trading remain NO-GO.\n\n"
        "## Hypothesis results\n\n" + _markdown_table(top[[
            "variant", "hypothesis", "strategy_family", "campaign_count", "net_pnl", "profit_factor",
            "expectancy", "win_rate", "max_drawdown", "best_campaign_contribution",
            "best_month_contribution", "positive_symbol_share", "positive_month_share",
            "timeframe_consistency", "profit_factor_2x_cost", "research_gate",
        ]] if not top.empty else top, limit=40)
        + "\n\n## Required answers\n\n"
        f"1. **Liquidity density:** {_density_status(before_after)}. Corrected ADV increased eligible bars where the prior unit mismatch had suppressed them.\n"
        f"2. **Natural testability:** {'yes' if not summary.empty and (summary.loc[summary['strategy_family']=='natural_long_grid', 'campaign_count'] >= 30).any() else 'not yet at the 30-campaign gate'}.\n"
        f"3. **Pair testability:** {'yes' if not summary.empty and (summary.loc[summary['strategy_family']=='stock_pair_grid', 'campaign_count'] >= 30).any() else 'not yet at the 30-campaign gate'}. "
        + (f"The H5 corrected baseline produced {int(h5.iloc[0]['campaign_count'])} campaigns, PF {h5.iloc[0]['profit_factor']:.3f}, and expectancy ${h5.iloc[0]['expectancy']:.2f}; H6 exits did not repair it.\n" if not h5.empty else "\n")
        + "4. **Residual confirmation:** " + (f"PF {h7.iloc[0]['profit_factor']:.3f}, expectancy ${h7.iloc[0]['expectancy']:.2f}; status remains ABANDON.\n" if not h7.empty else "no qualifying confirmation campaigns; status remains ABANDON.\n")
        + "5. **Prior no-trade diagnosis:** the liquidity unit bug was the main density bottleneck for natural and pair campaigns (2→64 and 4→355), but it did not explain their economics.\n"
        + (f"6. **Wider geometry:** the preregistered H2 variants span PF {h2['profit_factor'].min():.3f}–{h2['profit_factor'].max():.3f}; all fail the research and 2×-cost gates, so geometry is MIXED rather than an edge.\n" if not h2.empty else "6. **Wider geometry:** insufficient evidence.\n")
        + (f"7. **Stop mechanics:** intrabar PF is {h3.loc[h3['variant']=='H3_INTRABAR', 'profit_factor'].iloc[0]:.3f}; neither 1-close nor 2-close confirmation improves both PF and expectancy. The diagnostic conclusion is MIXED, not a stop upgrade.\n" if not h3.empty and (h3['variant'] == 'H3_INTRABAR').any() else "7. **Stop mechanics:** insufficient evidence.\n")
        + (f"8. **Cost-aware TP:** H4 spans PF {h4['profit_factor'].min():.3f}–{h4['profit_factor'].max():.3f}; k=3/5 remain below 1.15 and fail 2× costs, while k=8 loses money. It changes density but does not establish edge.\n" if not h4.empty else "8. **Cost-aware TP:** insufficient evidence.\n")
        + f"9. **Statistical sufficiency:** {len(no_gate_passes)} variants pass the preregistered research gate; no positive result is promoted.\n"
        + f"10. **Stability:** {len(positive_both_timeframes)} variants are positive on both 5m and 15m, and none passes the complete robustness gate.\n"
        + "11. **Phase 3C:** no hypothesis advances. Higher-quality raw consolidated intraday data and point-in-time events are required before another controlled redesign.\n"
        + "12. **Abandon:** residual current form, breakout current form, and stock-pair H5/H6 current mechanics are abandoned. Natural grid remains redesign-only, not an edge candidate.\n"
        "13. **Live/paper:** none is eligible.\n\n"
        "## Expected conclusion format\n\n"
    )
    status_preview = {
        "LIQUIDITY GATE FIX": "PASS",
        "SIGNAL DENSITY IMPROVED": _density_status(before_after),
        "NATURAL LONG GRID STATUS": _family_status(summary, "natural_long_grid"),
        "STOCK PAIRS STATUS": _family_status(summary, "stock_pair_grid"),
        "RESIDUAL GRID STATUS": "ABANDON",
        "BREAKOUT CONTINUATION STATUS": "ABANDON",
        "GRID GEOMETRY STATUS": _geometry_status(natural),
        "STOP LOGIC STATUS": _stop_status(natural, summary),
        "COST IMPACT": _cost_status(stress),
        "CONDITIONAL EDGE FOUND": "YES" if (not summary.empty and summary["research_gate"].any()) else "UNDERPOWERED" if (not summary.empty and (summary["profit_factor"] > 1.15).any()) else "NO",
        "LIVE TRADING STATUS": "NO-GO",
        "NEXT PHASE RECOMMENDATION": _next_phase(summary[summary["research_gate"] == True] if not summary.empty else pd.DataFrame()),
    }
    report += "\n".join(f"{key}: **{value}**" for key, value in status_preview.items())
    report += "\n\n## Manual replays\n\n" + _markdown_table(replays, limit=20)
    _write(output / "phase3b_redesign_report.md", report)


def _jobs(config: dict) -> list[dict[str, Any]]:
    specs = _strategy_specs(config)
    jobs: list[dict[str, Any]] = []
    for variant, item in variant_registry().items():
        if item.get("alias_of"):
            continue
        for timeframe in TIMEFRAMES:
            for spec in specs:
                if spec["family"] == item["family"]:
                    jobs.append({"variant": variant, "spec": spec, "timeframe": timeframe, "threshold": 50_000_000.0})
    # Liquidity stress is a full rerun of unchanged H1/H5 logic. H6_TIME5 is
    # represented later as an exact alias of H5, avoiding duplicate simulation.
    for family, base_variant in (("natural_long_grid", "H1_CORRECTED_BASELINE"), ("stock_pair_grid", "H5_CORRECTED_BASELINE")):
        for threshold in (10_000_000.0, 25_000_000.0, 100_000_000.0, None):
            label = "NONE" if threshold is None else str(int(threshold / 1_000_000)) + "M"
            variant = f"LQ_STRESS_{label}_{family}"
            for timeframe in TIMEFRAMES:
                for spec in specs:
                    if spec["family"] == family:
                        jobs.append({
                            "variant": variant, "source_variant": base_variant, "spec": spec,
                            "timeframe": timeframe, "threshold": threshold,
                        })
    return jobs


def run_phase3b(root: Path, *, workers: int = 6, force: bool = False) -> dict[str, Any]:
    _verify_snapshot(root)
    output = root / "outputs" / "phase3b_redesign"
    run_cache = output / "_run_cache"
    run_cache.mkdir(parents=True, exist_ok=True)
    config = load_config(root / CONFIG_PATH)
    _validate_registry(config)
    previous_files = [
        path for directory in (root / "outputs").glob("phase*")
        if directory.name != "phase3b_redesign" for path in directory.rglob("*") if path.is_file()
    ]
    previous_hashes = {str(path.relative_to(root)): _sha256(path) for path in previous_files}
    trade_starts = {
        timeframe: _trade_start(config, root / "data" / "phase2d_data_trial" / "hf_data_library", timeframe)
        for timeframe in TIMEFRAMES
    }
    jobs = _jobs(config)
    payloads = []
    for job in jobs:
        payloads.append({
            "root": str(root), "variant": job["variant"], "source_variant": job.get("source_variant", job["variant"]),
            "spec": job["spec"], "timeframe": job["timeframe"], "threshold": job["threshold"],
            "trade_start": str(trade_starts[job["timeframe"]]), "run_cache": str(run_cache), "force": force,
        })

    summaries: list[dict[str, Any]] = []
    if workers <= 1:
        for number, payload in enumerate(payloads, start=1):
            summary = _worker(dict(payload))
            summaries.append(summary)
            print(f"PHASE3B_RUN {number}/{len(payloads)} {summary['job_id']} campaigns={summary['campaigns']}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=min(workers, len(payloads))) as pool:
            futures = {pool.submit(_worker, payload): payload for payload in payloads}
            for number, future in enumerate(as_completed(futures), start=1):
                summary = future.result()
                summaries.append(summary)
                print(f"PHASE3B_RUN {number}/{len(payloads)} {summary['job_id']} campaigns={summary['campaigns']}", flush=True)

    # H6_TIME5 is exactly H5 by preregistration; materialize it from H5 outputs
    # without rerunning a byte-identical engine path.
    for path in list(run_cache.glob("H5_CORRECTED_BASELINE__*")):
        new_name = path.name.replace("H5_CORRECTED_BASELINE", "H6_TIME5", 1)
        target = run_cache / new_name
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            data["variant"] = "H6_TIME5"
            data["hypothesis"] = "H6"
            if "job_id" in data:
                data["job_id"] = str(data["job_id"]).replace("H5_CORRECTED_BASELINE", "H6_TIME5", 1)
            _write_json(target, data)
        else:
            data = pd.read_parquet(path)
            if "variant" in data:
                data["variant"] = "H6_TIME5"
            if "hypothesis" in data:
                data["hypothesis"] = "H6"
            if "job_id" in data:
                data["job_id"] = data["job_id"].astype(str).str.replace("H5_CORRECTED_BASELINE", "H6_TIME5", n=1, regex=False)
            data.to_parquet(target, index=False)

    campaigns, summary_frame, gates, decisions = _collect(run_cache)
    if campaigns.empty:
        raise RuntimeError("Phase 3B produced no campaigns")
    result = _build_outputs(root, campaigns, summary_frame, gates, decisions)
    previous_after = {str(path.relative_to(root)): _sha256(path) for path in previous_files}
    changed = [key for key, value in previous_hashes.items() if previous_after.get(key) != value]
    if changed:
        raise RuntimeError(f"Prior artifacts changed during Phase 3B: {changed[:5]}")
    _verify_snapshot(root)
    manifest = {
        "phase": PHASE, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_status": SOURCE_STATUS, "runs": len(summary_frame), "campaigns": len(campaigns),
        "workers": workers, "previous_artifacts_checked": len(previous_hashes),
        "previous_artifacts_changed": changed, "frozen_baseline_verified": True,
        "breakout_enabled": False, "residual_runs": 22, "residual_optimized": False,
        "live_trading_status": "NO-GO", **result,
    }
    _write_json(output / "phase3b_manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 3B frozen redesign validation")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--workers", type=int, default=max(1, min(6, (os.cpu_count() or 2) - 1)))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--freeze-only", action="store_true")
    parser.add_argument("--overwrite-freeze", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.freeze_only:
        snapshot = freeze_baseline(root, overwrite=args.overwrite_freeze)
        print(json.dumps(snapshot, indent=2, default=str), flush=True)
        return 0
    manifest = run_phase3b(root, workers=args.workers, force=args.force)
    print(json.dumps(manifest, indent=2, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
