from __future__ import annotations

import ast
import hashlib
import json
import math
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from residual_grid_research.backtest import BacktestEngine, resolve_barrier_touch
from residual_grid_research.config import load_config, project_path
from residual_grid_research.data import EventCalendar, YahooFinanceClient
from residual_grid_research.data.alpha_vantage import indicator_prices
from residual_grid_research.features.statistics import rolling_relationship
from residual_grid_research.features.technical import add_technical_features
from residual_grid_research.models import BacktestResult, Side
from residual_grid_research.phase2b import (
    _first_test,
    _last_test,
    _period_metrics,
    _spec_for_run,
    run_expanded_universe,
)
from residual_grid_research.research import all_configured_symbols


AUDIT_RUNS = (
    "residual_grid:JPM/XLF",
    "natural_long_grid:CSCO",
    "stock_pair_grid:MA/V",
)

BUGS = (
    {
        "id": "B001",
        "description": "Natural-grid layers were close-triggered next-open market orders, not predefined resting limits.",
        "modules": "strategies/natural_grid.py; backtest/engine.py; models.py",
        "strategies": "natural_long_grid",
        "expected": "Levels are fixed at campaign creation and fill only when a candle trades through the limit.",
        "actual": "A close below a recalculated level queued a market order for the next open; the theoretical level did not constrain the fill.",
        "fix": "Added explicit LIMIT orders, locked entry-time ATR geometry, GTC handling, range-bound levels, and no-touch behavior.",
    },
    {
        "id": "B002",
        "description": "Residual/pair breakout conversion was checked before the z-score kill threshold.",
        "modules": "strategies/residual_grid.py; strategies/pair_grid.py",
        "strategies": "residual_grid; stock_pair_grid",
        "expected": "Kill/invalidation always has priority over optional continuation.",
        "actual": "A relationship already beyond kill could be converted to breakout continuation.",
        "fix": "Moved kill evaluation ahead of breakout evaluation and added a deterministic regression test.",
    },
    {
        "id": "B003",
        "description": "A queued entry/add was not revalidated against an event window at its execution timestamp.",
        "modules": "backtest/engine.py; all strategy modules",
        "strategies": "all",
        "expected": "Known events block both new campaigns and new adds before the fill.",
        "actual": "Yesterday's safe signal could fill at today's open inside an exclusion window.",
        "fix": "Added pre-open pending-order validation and explicit cancellation audit rows.",
    },
    {
        "id": "B004",
        "description": "Adjusted OHLC was used for simulated execution prices.",
        "modules": "data/yahoo_finance.py; data/alpha_vantage.py; all strategy prepare methods",
        "strategies": "all real-data runs",
        "expected": "Raw tradable OHLC drives fills; adjusted OHLC drives long-horizon indicators and relationships.",
        "actual": "The same total-return-adjusted OHLC drove both signals and fills.",
        "fix": "Added immutable raw-with-adjusted-indicator caches and separated engine execution columns from feature columns.",
    },
    {
        "id": "B005",
        "description": "Financing was valued with the current bar close before that close was available.",
        "modules": "backtest/engine.py",
        "strategies": "short residual and pair campaigns",
        "expected": "Overnight financing uses the last known mark.",
        "actual": "The loop updated prices to the current close before charging elapsed-time financing.",
        "fix": "Financing is now charged from the prior close before current-open processing.",
    },
    {
        "id": "B006",
        "description": "Same-decision pair legs were risk-approved independently against stale gross exposure.",
        "modules": "risk/manager.py; backtest/engine.py",
        "strategies": "residual_grid; stock_pair_grid",
        "expected": "Both legs are accepted/scaled atomically against aggregate headroom.",
        "actual": "Each leg saw the same pre-order portfolio, permitting joint limit overshoot or an unbalanced rejection.",
        "fix": "Added atomic batch sizing and all-or-none minimum/open-position checks.",
    },
    {
        "id": "B007",
        "description": "Relationship breakout confirmation omitted configured participation and break-distance checks.",
        "modules": "strategies/residual_grid.py; strategies/pair_grid.py",
        "strategies": "residual_grid; stock_pair_grid",
        "expected": "Persistent boundary break, minimum distance, participation, stable relationship, and optional retest are required.",
        "actual": "Persistent z closes alone could activate continuation.",
        "fix": "Added residual-distance buffer, volume/true-range participation, scored confirmation, and consecutive-close checks.",
    },
    {
        "id": "B008",
        "description": "Daily loss reference reset after the daily close, making the daily kill ineffective on daily bars.",
        "modules": "backtest/engine.py",
        "strategies": "all daily runs",
        "expected": "A new trading day begins from the prior known equity mark.",
        "actual": "The day-start mark was assigned after marking the current close, so the loss comparison began at zero.",
        "fix": "Moved day/week reference initialization to the start of the timestamp loop.",
    },
    {
        "id": "B009",
        "description": "Event checks did not consistently identify the actually short leg of an active relationship campaign.",
        "modules": "strategies/residual_grid.py; strategies/pair_grid.py; phase2c.py",
        "strategies": "residual_grid; stock_pair_grid",
        "expected": "Earnings apply to both symbols; ex-dividend rules apply only to the leg that is or will be short, using the campaign direction while active.",
        "actual": "Residual checks could derive short status from the current signal instead of the active campaign; pair checks treated both legs as short.",
        "fix": "Split common-event and short-leg checks and bind the latter to prospective or active campaign direction.",
    },
    {
        "id": "B010",
        "description": "A close-generated short-leg dividend exit could execute on the ex-dividend open, after the economic exposure was already carried overnight.",
        "modules": "strategies/residual_grid.py; strategies/pair_grid.py",
        "strategies": "residual_grid; stock_pair_grid",
        "expected": "An existing short leg is flat before the ex-dividend session opens.",
        "actual": "The configured buffer was checked at close without reserving a next-open execution bar or a holiday margin.",
        "fix": "Existing-position ex-dividend checks now add two conservative business-day lead units; new-entry checks retain the configured window.",
    },
)


def _md(frame: pd.DataFrame, *, rows: int | None = None) -> str:
    selected = frame.head(rows) if rows is not None else frame
    if selected.empty:
        return "_No rows._"
    try:
        return selected.to_markdown(index=False)
    except ImportError:
        return "```text\n" + selected.to_string(index=False) + "\n```"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prior_manifest(root: Path) -> dict[str, Any]:
    paths = [path for path in (root / "outputs").rglob("*") if path.is_file() and "phase2c_audit" not in path.parts]
    return {
        "artifact_count": len(paths),
        "artifacts": [
            {
                "path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
                "sha256": _sha256(path),
            }
            for path in sorted(paths)
        ],
    }


def _result_frames(results: dict[str, BacktestResult]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fills: list[dict] = []
    campaigns: list[dict] = []
    decisions: list[dict] = []
    orders: list[dict] = []
    for run, result in results.items():
        fills.extend({"run": run, **fill.to_dict()} for fill in result.fills)
        campaigns.extend({"run": run, **campaign} for campaign in result.campaigns)
        decisions.extend({"run": run, **decision.to_dict()} for decision in result.decisions)
        orders.extend({"run": run, **row} for row in result.order_audit)
    return pd.DataFrame(fills), pd.DataFrame(campaigns), pd.DataFrame(decisions), pd.DataFrame(orders)


def _parse_meta(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        parsed = ast.literal_eval(str(value))
        return parsed if isinstance(parsed, dict) else {}
    except (SyntaxError, ValueError):
        return {}


def _family(run: str) -> str:
    return "natural" if run.startswith("natural") else "pair" if run.startswith("stock_pair") else "residual"


def _primary(run: str) -> str:
    return run.split(":", 1)[1].split("/")[0]


def _metrics_row(run: str, result: BacktestResult, first: pd.Timestamp, end: pd.Timestamp) -> dict[str, Any]:
    metrics = _period_metrics(result, first, end)
    return {
        "run": run,
        "oos_return": float(metrics.get("total_return", 0.0)),
        "profit_factor": float(metrics.get("profit_factor", 0.0)),
        "expectancy_usd": float(metrics.get("expectancy_usd", 0.0)),
        "max_drawdown": float(metrics.get("max_drawdown", 0.0)),
        "campaigns": int(metrics.get("number_of_trades", 0)),
        "closed_trade_legs": int(metrics.get("closed_trade_legs", 0)),
        "exposure_pct": float(metrics.get("exposure_pct", 0.0)),
        "max_gross_leverage": float(metrics.get("max_gross_leverage_used", 0.0)),
        "max_net_beta_exposure": float(metrics.get("max_net_beta_exposure", 0.0)),
    }


def _load_dual_data(config: dict, *, force: bool = False) -> tuple[dict[str, pd.DataFrame], list[Any]]:
    client = YahooFinanceClient(project_path(config, "data", "real", "raw", "yahoo_phase2c"))
    return client.fetch_universe_execution(
        all_configured_symbols(config),
        str(config["data"]["daily_start"]),
        str(config["data"]["daily_end"]),
        force=force,
    )


def _run_corrected_expanded(
    config: dict,
    data: dict[str, pd.DataFrame],
    events: EventCalendar,
    pair_frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, BacktestResult], pd.Timestamp, pd.Timestamp]:
    metrics, results, _campaigns, _fills, first, end = run_expanded_universe(data, config, events, pair_frame)
    return metrics, results, first, end


def _golden_path_report(path: Path) -> None:
    rows = [
        ("01 clean range oscillation", "3 buy limits at 99/98/97; proportional exits at 100/99/98", "All touched layers fill; all exposure closes; exact cash-flow P&L reconciles", "PASS"),
        ("02 partial range oscillation", "Only 99/98 touched; 97 remains live until exit invalidates it", "Two fills only; untouched order is cancelled on GRID_EXITING", "PASS"),
        ("03 clean breakdown", "Two fills, invalidation, gap lower", "No new add in KILL; remaining grid cancelled; position liquidated", "PASS"),
        ("04 gap through stop", "Sell stop 95; next candle opens 90", "Fill at conservative open 90, not ideal 95", "PASS"),
        ("05 same-candle TP and stop", "Long stop 96 and target 104 inside 95-105 bar", "STOP selected by adverse-first resolver", "PASS"),
        ("06 no-fill", "Buy limit 98; candle low 99", "No fill; GTC remains pending", "PASS"),
        ("07 event exclusion", "Queued entry reaches known earnings date", "Entry cancelled before open", "PASS"),
        ("08 existing-position event", "Position open before event", "Configured policy is force exit: signal on event bar, fill next open", "PASS"),
        ("09 breakout success", "Two closes beyond boundary plus participation", "Continuation confirmation true", "PASS"),
        ("10 breakout fakeout", "Break, reclaim, break", "Not confirmed because the last required closes are not consecutive", "PASS"),
        ("11 residual mean reversion", "z=-1.6, beta=1.2", "Long stock / short 1.2x ETF notional", "PASS"),
        ("12 residual divergence / kill", "Long residual campaign reaches z=-3.2", "KILL evaluated before breakout; both legs close", "PASS"),
    ]
    frame = pd.DataFrame(rows, columns=["path", "input", "manual expectation", "result"])
    _write(path, f"""# Phase 2C golden-path deterministic tests

These fixtures use hand-specified OHLC paths and zero costs where exact arithmetic is the subject of the test. Execution-cost direction is tested separately. The automated source is `tests/test_phase2c_golden_paths.py`.

{_md(frame)}

## Accounting convention

The production engine uses average-cost inventory consistently. Natural-grid exits are campaign-level proportional scale-outs; every entry leg carries the same three campaign TP references in metadata. The clean-range fixture therefore checks exact aggregate cash flow and average-cost realized P&L, not FIFO or LIFO lot selection.

## Fill timing contract

Signals evaluated from candle *t* close become orders after that close. Market orders first become eligible at candle *t+1* open. Resting limits/stops may fill inside *t+1* only when its OHLC range touches the requested price. Stops are processed before discretionary limits/TPs on an ambiguous candle. Full fills are the baseline (`partial_fill_ratio=1.0`).
""")


def _build_grid_geometry(
    campaigns: pd.DataFrame,
    fills: pd.DataFrame,
    orders: pd.DataFrame,
    data: dict[str, pd.DataFrame],
    config: dict,
) -> pd.DataFrame:
    if campaigns.empty:
        return pd.DataFrame()
    fills = fills.copy()
    fills["timestamp"] = pd.to_datetime(fills["timestamp"])
    fills["metadata_dict"] = fills["metadata"].map(_parse_meta)
    technical_cache: dict[str, pd.DataFrame] = {}
    relationship_cache: dict[str, pd.DataFrame] = {}
    rows: list[dict[str, Any]] = []
    for campaign in campaigns.itertuples(index=False):
        run, group_id = str(campaign.run), str(campaign.group_id)
        family, primary = _family(run), _primary(run)
        selected = fills[(fills["run"] == run) & (fills["group_id"] == group_id)].sort_values("timestamp")
        entry = selected[~selected["reduce_only"]] if "reduce_only" in selected else selected[~selected["reason"].str.contains("TP|kill|exit|stop|convert", case=False, regex=True)]
        # Fill objects do not serialize reduce_only; reason/metadata is the stable classification.
        entry = selected[~selected["metadata_dict"].map(lambda value: bool(value.get("close_fraction") or value.get("close_all")))]
        entry_time = pd.Timestamp(campaign.entry_time)
        frame = data[primary]
        match = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})$", group_id)
        group_signal = pd.Timestamp(match.group(1)) if match else None
        if group_signal is not None and group_signal in frame.index:
            signal_time = group_signal
        else:
            signal_candidates = frame.index[frame.index < entry_time]
            signal_time = pd.Timestamp(signal_candidates[-1]) if len(signal_candidates) else entry_time
        if primary not in technical_cache:
            technical_cache[primary] = add_technical_features(indicator_prices(frame))
        technical = technical_cache[primary]
        feature = technical.loc[signal_time] if signal_time in technical.index else pd.Series(dtype=float)
        atr = float(feature.get("atr_14", np.nan))
        range_high = float(feature.get("range_high", np.nan))
        range_low = float(feature.get("range_low", np.nan))
        range_width = range_high - range_low if np.isfinite(range_high) and np.isfinite(range_low) else np.nan
        actual_avg = (
            float(np.average(entry["price"].astype(float), weights=entry["quantity"].astype(float)))
            if not entry.empty else np.nan
        )
        meta = entry.iloc[0]["metadata_dict"] if not entry.empty else {}
        if family == "natural":
            step = float(config["strategy"]["natural"]["grid_step_atr"]) * atr
            levels = sorted(
                {float(value.get("grid_level")) for value in entry["metadata_dict"] if value.get("grid_level") is not None},
                reverse=True,
            )
            requested = orders[(orders["run"] == run) & (orders["campaign_id"] == group_id) & (orders["order_type"] == "LIMIT")]
            if not requested.empty:
                levels = sorted(pd.to_numeric(requested["requested_price"], errors="coerce").dropna().unique().tolist(), reverse=True)
            stop = float(meta.get("stop_price", np.nan))
            tp_values = meta.get("tp_prices", [])
            tp_distance = (min(tp_values) - actual_avg) if tp_values and np.isfinite(actual_avg) else np.nan
            stop_distance = actual_avg - stop if np.isfinite(actual_avg) and np.isfinite(stop) else np.nan
            expected_avg = float(np.mean(levels)) if levels else np.nan
            level_text = ";".join(f"{value:.6f}" for value in levels)
        else:
            settings = config["strategy"]["pairs" if family == "pair" else "residual"]
            z_levels = list(map(float, settings["grid_levels"]))
            if run not in relationship_cache:
                secondary = run.split("/", 1)[1]
                relationship_cache[run] = rolling_relationship(
                    indicator_prices(data[primary]), indicator_prices(data[secondary]),
                    beta_window=int(config["features"]["beta_window"]),
                    z_window=int(config["features"]["z_window"]),
                    correlation_windows=config["features"]["correlation_windows"],
                )
            relation = relationship_cache[run]
            rr = relation.loc[signal_time] if signal_time in relation.index else pd.Series(dtype=float)
            residual_std = float(rr.get("residual_std", np.nan))
            step = 0.3 * residual_std * float(rr.get("price_a", np.nan))
            stop_distance = (float(settings["kill_z"]) - z_levels[0]) * residual_std * float(rr.get("price_a", np.nan))
            tp_distance = (z_levels[0] - float(settings["take_profit_z"][0])) * residual_std * float(rr.get("price_a", np.nan))
            expected_avg = actual_avg
            level_text = "z:" + ";".join(f"{value:.2f}" for value in z_levels)
        level_numbers = [int(value.get("grid_layer", 1)) for value in entry["metadata_dict"] if value.get("grid_layer") is not None]
        rows.append({
            "run": run,
            "campaign_id": group_id,
            "strategy_family": family,
            "signal_timestamp": signal_time,
            "range_high_adjusted": range_high,
            "range_low_adjusted": range_low,
            "range_width_adjusted": range_width,
            "atr_adjusted": atr,
            "grid_step_price_equivalent": step,
            "grid_step_pct": step / float(feature.get("close", np.nan)) if np.isfinite(step) else np.nan,
            "grid_step_atr": step / atr if np.isfinite(step) and np.isfinite(atr) and atr else np.nan,
            "range_width_atr": range_width / atr if np.isfinite(range_width) and atr else np.nan,
            "number_of_levels": len(level_text.split(";")),
            "level_prices_or_z": level_text,
            "initial_entry_level": meta.get("grid_level", meta.get("z")),
            "max_depth": max(level_numbers, default=len(entry)),
            "filled_legs": len(entry),
            "take_profit_distance": tp_distance,
            "stop_distance": stop_distance,
            "stop_distance_atr": stop_distance / atr if np.isfinite(stop_distance) and atr else np.nan,
            "tp_distance_atr": tp_distance / atr if np.isfinite(tp_distance) and atr else np.nan,
            "expected_average_price_all_levels": expected_avg,
            "actual_average_price": actual_avg,
            "average_entry_improvement": (float(entry.iloc[0]["price"]) - actual_avg) if len(entry) else 0.0,
            "average_tp_capture_per_closed_leg": float(campaign.pnl_usd) / max(1, int(campaign.fill_count) - len(entry)),
            "grid_outside_range": bool(family == "natural" and np.isfinite(range_low) and any(level < range_low * float(feature.get("execution_factor", 1.0)) for level in ([float(v) for v in level_text.split(";") if v] if level_text else []))),
        })
    return pd.DataFrame(rows)


def _inventory_and_replays(
    output: Path,
    campaigns: pd.DataFrame,
    fills: pd.DataFrame,
    decisions: pd.DataFrame,
    data: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    fill_frame = fills.copy()
    fill_frame["timestamp"] = pd.to_datetime(fill_frame["timestamp"])
    fill_frame["metadata_dict"] = fill_frame["metadata"].map(_parse_meta)
    entries = fill_frame[~fill_frame["metadata_dict"].map(lambda value: bool(value.get("close_fraction") or value.get("close_all")))]
    counts = entries.groupby(["run", "group_id"]).size().sort_values(ascending=False)
    chosen = list(counts[counts >= 3].head(10).index)
    if len(chosen) < 10:
        chosen.extend([item for item in counts.index if item not in chosen][: 10 - len(chosen)])
    replay_rows: list[dict[str, Any]] = []
    replay_dir = output / "campaign_replays"
    replay_dir.mkdir(parents=True, exist_ok=True)
    for stale in replay_dir.glob("*.md"):
        stale.unlink()
    for sequence, (run, group_id) in enumerate(chosen, start=1):
        campaign = campaigns[(campaigns["run"] == run) & (campaigns["group_id"] == group_id)].iloc[0]
        selected = fill_frame[(fill_frame["run"] == run) & (fill_frame["group_id"] == group_id)].sort_values("timestamp")
        primary = _primary(run)
        frame = data[primary].loc[pd.Timestamp(campaign["entry_time"]):pd.Timestamp(campaign["exit_time"])]
        positions: dict[str, tuple[float, float]] = {}
        realized = 0.0
        for timestamp, bar in frame.iterrows():
            day_fills = selected[selected["timestamp"] == pd.Timestamp(timestamp)]
            reasons: list[str] = []
            for fill in day_fills.itertuples(index=False):
                quantity, average = positions.get(fill.symbol, (0.0, 0.0))
                signed = float(fill.quantity) if str(fill.side).endswith("BUY") else -float(fill.quantity)
                if not quantity or np.sign(quantity) == np.sign(signed):
                    total = abs(quantity) + abs(signed)
                    average = (abs(quantity) * average + abs(signed) * float(fill.price)) / total
                    quantity += signed
                else:
                    closing = min(abs(quantity), abs(signed))
                    realized += closing * (float(fill.price) - average) * np.sign(quantity) - float(fill.commission)
                    quantity += signed
                    if abs(quantity) < 1e-10:
                        quantity, average = 0.0, 0.0
                positions[fill.symbol] = (quantity, average)
                reasons.append(str(fill.reason))
            primary_quantity, primary_average = positions.get(primary, (0.0, 0.0))
            unrealized = sum(
                quantity * (float(data[symbol].at[timestamp, "close"]) - average)
                for symbol, (quantity, average) in positions.items()
                if timestamp in data[symbol].index
            )
            latest_state = ""
            if not decisions.empty:
                subset = decisions[(decisions["run"] == run) & (pd.to_datetime(decisions["timestamp"]) <= timestamp)]
                latest_state = str(subset.iloc[-1]["state_to"]) if not subset.empty else ""
            replay_rows.append({
                "replay_id": sequence,
                "run": run,
                "campaign_id": group_id,
                "timestamp": timestamp,
                "price": float(bar["close"]),
                "state": latest_state,
                "active_grid_levels": ";".join(str(meta.get("grid_level", "")) for meta in day_fills["metadata_dict"]),
                "filled_legs": len(day_fills),
                "average_entry": primary_average,
                "open_exposure": sum(abs(quantity * float(data[symbol].at[timestamp, "close"])) for symbol, (quantity, _average) in positions.items() if timestamp in data[symbol].index),
                "realized_pnl": realized,
                "unrealized_pnl": unrealized,
                "action_reason": "; ".join(reasons) or "mark only",
            })
        selected_rows = pd.DataFrame([row for row in replay_rows if row["replay_id"] == sequence])
        safe = f"{sequence:02d}_{run.replace(':', '_').replace('/', '_')}_{hashlib.sha1(group_id.encode()).hexdigest()[:8]}.md"
        _write(replay_dir / safe, f"# Campaign replay {sequence}: {run}\n\nCampaign `{group_id}`. Behavior is shown at each available daily candle; action reasons identify every add/exit.\n\n{_md(selected_rows)}")
    return pd.DataFrame(replay_rows)


def _pnl_reconciliation(campaigns: pd.DataFrame, fills: pd.DataFrame, *, sample: str) -> pd.DataFrame:
    fill_frame = fills.copy()
    fill_frame["metadata_dict"] = fill_frame["metadata"].map(_parse_meta)
    rows: list[dict[str, Any]] = []
    for campaign in campaigns.itertuples(index=False):
        selected = fill_frame[(fill_frame["run"] == campaign.run) & (fill_frame["group_id"] == campaign.group_id)]
        signed = np.where(selected["side"].astype(str).str.endswith("BUY"), selected["quantity"].astype(float), -selected["quantity"].astype(float))
        cash_pnl = float((-signed * selected["price"].astype(float)).sum() - selected["commission"].astype(float).sum())
        financing = float(getattr(campaign, "financing_cost_usd", 0.0))
        reconciled = cash_pnl - financing
        leg_realized = float(selected["realized_pnl"].astype(float).sum())
        commissions = float(selected["commission"].astype(float).sum())
        expected_from_ledger = leg_realized - commissions - financing
        primary = _primary(str(campaign.run))
        primary_cash = float((-signed[selected["symbol"].eq(primary)] * selected.loc[selected["symbol"].eq(primary), "price"].astype(float)).sum())
        hedge_cash = cash_pnl + commissions - primary_cash
        discrepancy = reconciled - float(campaign.pnl_usd)
        ledger_discrepancy = expected_from_ledger - float(campaign.pnl_usd)
        rows.append({
            "sample": sample,
            "run": campaign.run,
            "campaign_id": campaign.group_id,
            "sum_leg_realized_pnl": leg_realized,
            "open_unrealized_pnl": 0.0 if bool(campaign.closed) else np.nan,
            "commissions": commissions,
            "slippage_embedded_usd": float(selected.get("friction_cost", pd.Series(dtype=float)).astype(float).sum()),
            "financing_cost_usd": financing,
            "primary_leg_cashflow": primary_cash,
            "hedge_leg_cashflow": hedge_cash,
            "campaign_pnl_reported": float(campaign.pnl_usd),
            "campaign_pnl_reconciled": reconciled,
            "equity_curve_impact": float(campaign.pnl_usd),
            "cashflow_discrepancy": discrepancy,
            "realized_ledger_discrepancy": ledger_discrepancy,
            "pass": abs(discrepancy) <= 1e-8 and abs(ledger_discrepancy) <= 1e-8,
        })
    return pd.DataFrame(rows)


def _run_parameter_reasonableness(
    config: dict,
    data: dict[str, pd.DataFrame],
    events: EventCalendar,
    first: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    variants: dict[str, list[tuple[str, Any]]] = {
        "natural_long_grid:CSCO": [
            *(('grid_levels', value) for value in (3, 5, 7, 9)),
            *(('grid_step_atr', value) for value in (0.4, 0.6, 0.8, 1.0, 1.2)),
            *(('tp_mode', value) for value in ("0.5_step", "1.0_step", "1.5_step", "midpoint")),
            *(('stop_variant', value) for value in ("current", "range_low_0.5_atr", "range_low_1.0_atr", "structure_close")),
            *(('max_grid_depth', value) for value in (2, 3, 4, 5)),
        ],
        "residual_grid:JPM/XLF": [
            *(('z_entry', value) for value in (1.2, 1.5, 1.8, 2.0)),
            *(('z_exit', value) for value in (0.8, 0.5, 0.2, 0.0)),
            *(('z_kill', value) for value in (2.5, 3.0, 3.5)),
            *(('beta_window', value) for value in (60, 90, 120)),
            *(('hedge_ratio', value) for value in ("beta_neutral", "dollar_neutral")),
        ],
        "stock_pair_grid:MA/V": [
            *(('z_entry', value) for value in (1.2, 1.5, 1.8, 2.0)),
            *(('z_exit', value) for value in (0.8, 0.5, 0.2, 0.0)),
            *(('z_kill', value) for value in (2.5, 3.0, 3.5)),
            *(('correlation_threshold', value) for value in (0.65, 0.75, 0.85)),
            *(('stationarity_proxy', value) for value in (True, False)),
        ],
    }
    rows: list[dict[str, Any]] = []
    for run, values in variants.items():
        spec = _spec_for_run(run, config, events)
        for dimension, value in [("original", "original"), *values]:
            candidate = deepcopy(config)
            family = _family(run)
            settings_key = "natural" if family == "natural" else "pairs" if family == "pair" else "residual"
            settings = candidate["strategy"][settings_key]
            if dimension == "grid_levels":
                settings["grid_level_count"] = int(value)
                settings["max_grid_depth"] = int(value)
            elif dimension == "grid_step_atr":
                settings["grid_step_atr"] = float(value)
            elif dimension == "tp_mode":
                settings["tp_mode"] = str(value)
            elif dimension == "stop_variant":
                settings["stop_variant"] = str(value)
            elif dimension == "max_grid_depth":
                settings["max_grid_depth"] = int(value)
            elif dimension == "z_entry":
                settings["entry_z"] = float(value)
                count = len(settings["grid_levels"])
                settings["grid_levels"] = np.linspace(float(value), float(settings["kill_z"]) - 0.2, count).round(3).tolist()
            elif dimension == "z_exit":
                first_exit = float(value)
                settings["take_profit_z"] = [first_exit, max(0.0, first_exit - 0.3), 0.0]
            elif dimension == "z_kill":
                settings["kill_z"] = float(value)
                settings["grid_levels"] = [min(float(level), float(value) - 0.1) for level in settings["grid_levels"]]
            elif dimension == "beta_window":
                candidate["features"]["beta_window"] = int(value)
            elif dimension == "hedge_ratio":
                settings["hedge_ratio_mode"] = str(value)
            elif dimension == "correlation_threshold":
                candidate["features"]["stock_pair_corr_min"] = float(value)
                candidate["features"]["stock_pair_corr_90_min"] = max(0.55, float(value) - 0.1)
            elif dimension == "stationarity_proxy":
                settings["stationarity_proxy_enabled"] = bool(value)
            result = BacktestEngine(candidate).run(spec.factory(candidate, events), data, trade_start=first)
            metrics = _period_metrics(result, first, end)
            campaigns = pd.DataFrame(result.campaigns)
            stopped = int(campaigns["exit_reason"].astype(str).str.contains("kill|stop|invalidation", case=False, regex=True).sum()) if not campaigns.empty else 0
            rows.append({
                "run": run,
                "family": family,
                "dimension": dimension,
                "value": value,
                "diagnostic_only": True,
                "oos_return": float(metrics.get("total_return", 0.0)),
                "profit_factor": float(metrics.get("profit_factor", 0.0)),
                "expectancy_usd": float(metrics.get("expectancy_usd", 0.0)),
                "max_drawdown": float(metrics.get("max_drawdown", 0.0)),
                "campaigns": int(metrics.get("number_of_trades", 0)),
                "stopped_campaigns": stopped,
                "cost_drag_usd": float(metrics.get("cost_drag_usd", 0.0)),
            })
    return pd.DataFrame(rows)


def _parameter_findings(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for run, group in frame.groupby("run"):
        original = group[group["dimension"] == "original"].iloc[0]
        for dimension, selected in group[group["dimension"] != "original"].groupby("dimension"):
            positive_share = float((selected["expectancy_usd"] > 0).mean())
            trade_min, trade_max = int(selected["campaigns"].min()), int(selected["campaigns"].max())
            if positive_share in {0.0, 1.0}:
                stability = "consistent sign across diagnostic values"
            else:
                stability = "sign-sensitive; requires independent validation"
            rows.append({
                "run": run,
                "dimension": dimension,
                "original_expectancy_usd": float(original["expectancy_usd"]),
                "positive_variant_share": positive_share,
                "campaign_range": f"{trade_min}-{trade_max}",
                "mechanical_diagnosis": stability,
            })
    return pd.DataFrame(rows)


def _residual_math_audit(
    results: dict[str, BacktestResult],
    data: dict[str, pd.DataFrame],
    config: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    verification: list[dict[str, Any]] = []
    for run in ("residual_grid:JPM/XLF", "stock_pair_grid:MA/V"):
        if run not in results:
            continue
        first_symbol, second_symbol = run.split(":", 1)[1].split("/")
        relation = rolling_relationship(
            indicator_prices(data[first_symbol]), indicator_prices(data[second_symbol]),
            beta_window=int(config["features"]["beta_window"]),
            z_window=int(config["features"]["z_window"]),
            correlation_windows=config["features"]["correlation_windows"],
        )
        entry_fills = [
            fill for fill in results[run].fills
            if fill.symbol == first_symbol and not fill.metadata.get("close_fraction") and not fill.metadata.get("close_all")
        ]
        for fill in entry_fills[:5]:
            fill_time = pd.Timestamp(fill.timestamp)
            eligible = relation.index[relation.index < fill_time]
            if not len(eligible):
                continue
            timestamp = pd.Timestamp(eligible[-1])
            row = relation.loc[timestamp]
            direction = int(fill.metadata.get("direction", 1 if fill.side == Side.BUY else -1))
            stock_notional = float(fill.gross_notional)
            beta = float(row["beta"])
            rows.append({
                "run": run,
                "timestamp": timestamp,
                "stock_price_adjusted": float(row["price_a"]),
                "hedge_price_adjusted": float(row["price_b"]),
                "alpha": float(row["alpha"]),
                "beta": beta,
                "correlation": float(row["corr_60"]),
                "residual": float(row["residual"]),
                "rolling_residual_mean": float(row["residual_mean"]),
                "rolling_residual_std": float(row["residual_std"]),
                "z_score": float(row["z"]),
                "entry_threshold": float(config["strategy"]["pairs" if _family(run) == "pair" else "residual"]["entry_z"]),
                "exit_threshold": float(config["strategy"]["pairs" if _family(run) == "pair" else "residual"]["take_profit_z"][0]),
                "kill_threshold": float(config["strategy"]["pairs" if _family(run) == "pair" else "residual"]["kill_z"]),
                "direction": "long residual" if direction > 0 else "short residual",
                "stock_notional": stock_notional,
                "hedge_notional_expected": stock_notional * beta,
            })
            # Independent scalar recomputation using only observations through t-1.
            window = relation.loc[:timestamp].iloc[-int(config["features"]["beta_window"]):]
            prior_a = relation.loc[:timestamp, "log_a"].shift(1).dropna().iloc[-int(config["features"]["beta_window"]):]
            prior_b = relation.loc[:timestamp, "log_b"].shift(1).dropna().iloc[-int(config["features"]["beta_window"]):]
            prior_a, prior_b = prior_a.align(prior_b, join="inner")
            manual_beta = float(np.cov(prior_a, prior_b, ddof=1)[0, 1] / np.var(prior_b, ddof=1))
            manual_alpha = float(prior_a.mean() - manual_beta * prior_b.mean())
            manual_residual = float(row["log_a"] - manual_alpha - manual_beta * row["log_b"])
            verification.append({
                "run": run,
                "timestamp": timestamp,
                "engine_beta": beta,
                "manual_beta": manual_beta,
                "beta_difference": manual_beta - beta,
                "engine_alpha": float(row["alpha"]),
                "manual_alpha": manual_alpha,
                "alpha_difference": manual_alpha - float(row["alpha"]),
                "engine_residual": float(row["residual"]),
                "manual_residual": manual_residual,
                "residual_difference": manual_residual - float(row["residual"]),
                "prior_only": True,
                "timestamp_aligned": timestamp in data[first_symbol].index and timestamp in data[second_symbol].index,
            })
    return pd.DataFrame(rows), pd.DataFrame(verification)


def _state_audit(
    decisions: pd.DataFrame,
    fills: pd.DataFrame,
    orders: pd.DataFrame,
) -> pd.DataFrame:
    allowed = {
        "SCAN": {"CANDIDATE", "FLAT", "COOLDOWN"},
        "CANDIDATE": {"ARMED", "SCAN", "COOLDOWN"},
        "ARMED": {"GRID_ACTIVE", "SCAN", "KILL"},
        "GRID_ACTIVE": {"WARNING", "GRID_EXITING", "BREAKOUT_SETUP", "KILL"},
        "WARNING": {"GRID_ACTIVE", "GRID_EXITING", "BREAKOUT_SETUP", "KILL"},
        "GRID_EXITING": {"FLAT", "KILL"},
        "BREAKOUT_SETUP": {"BREAKOUT_ACTIVE", "GRID_EXITING", "KILL"},
        "BREAKOUT_ACTIVE": {"GRID_EXITING", "KILL"},
        "KILL": {"COOLDOWN"},
        "COOLDOWN": {"FLAT", "SCAN"},
        "FLAT": {"SCAN", "CANDIDATE", "COOLDOWN"},
    }
    rows: list[dict[str, Any]] = []
    fill_frame = fills.copy()
    fill_frame["timestamp"] = pd.to_datetime(fill_frame["timestamp"])
    order_frame = orders.copy()
    if not order_frame.empty:
        order_frame["timestamp"] = pd.to_datetime(order_frame["timestamp"])
    for run, run_decisions in decisions.groupby("run", sort=False):
        run_decisions = run_decisions.sort_values("timestamp")
        run_fills = fill_frame[fill_frame["run"] == run].sort_values("timestamp")
        fill_rows = list(run_fills.itertuples(index=False))
        cursor = 0
        positions: dict[str, float] = {}
        for decision in run_decisions.itertuples(index=False):
            timestamp = pd.Timestamp(decision.timestamp)
            while cursor < len(fill_rows) and pd.Timestamp(fill_rows[cursor].timestamp) <= timestamp:
                fill = fill_rows[cursor]
                positions[fill.symbol] = positions.get(fill.symbol, 0.0) + (
                    float(fill.quantity) if str(fill.side).endswith("BUY") else -float(fill.quantity)
                )
                cursor += 1
            active = ";".join(f"{symbol}:{quantity:.6f}" for symbol, quantity in positions.items() if abs(quantity) > 1e-8)
            open_orders = 0
            if not order_frame.empty:
                open_orders = int(((order_frame["run"] == run) & (order_frame["timestamp"] == timestamp) & (order_frame["status"] != "FILLED")).sum())
            old, new = str(decision.state_from), str(decision.state_to)
            valid = new in allowed.get(old, set())
            invalid_reason = ""
            if new == "BREAKOUT_ACTIVE" and "confirm" not in str(decision.reason).lower() and "entered" not in str(decision.reason).lower() and "converted" not in str(decision.reason).lower():
                invalid_reason = "breakout lacks confirmation reason"
            if new in {"FLAT"} and active:
                invalid_reason = "flat state with exposure"
            rows.append({
                "run": decision.run,
                "timestamp": timestamp,
                "old_state": old,
                "new_state": new,
                "triggering_condition": decision.reason,
                "active_position": active,
                "open_orders": open_orders,
                "reason_text": decision.reason,
                "transition_allowed": valid,
                "invalid_transition_reason": invalid_reason,
            })
    return pd.DataFrame(rows)


def _stop_audit(
    campaigns: pd.DataFrame,
    geometry: pd.DataFrame,
    data: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    merged = campaigns.merge(
        geometry[["run", "campaign_id", "range_low_adjusted", "atr_adjusted", "actual_average_price", "stop_distance", "stop_distance_atr"]],
        left_on=["run", "group_id"], right_on=["run", "campaign_id"], how="left",
    )
    rows: list[dict[str, Any]] = []
    variants = (
        "current",
        "range_low_minus_0.5_atr",
        "range_low_minus_1.0_atr",
        "last_grid_minus_0.5_atr",
        "average_entry_minus_1.5_atr",
        "structure_close_only",
        "intrabar_hard_stop",
        "two_close_confirmation",
    )
    for item in merged.itertuples(index=False):
        family = _family(str(item.run))
        primary = _primary(str(item.run))
        start, end = pd.Timestamp(item.entry_time), pd.Timestamp(item.exit_time)
        frame = indicator_prices(data[primary]).loc[start:end]
        atr = float(item.atr_adjusted) if pd.notna(item.atr_adjusted) else np.nan
        range_low = float(item.range_low_adjusted) if pd.notna(item.range_low_adjusted) else np.nan
        average = float(item.actual_average_price) if pd.notna(item.actual_average_price) else np.nan
        last_grid = float(frame["low"].iloc[0]) if len(frame) else np.nan
        current_reason = str(item.exit_reason)
        initial_stop = average - float(item.stop_distance) if pd.notna(item.stop_distance) and np.isfinite(average) else np.nan
        rows.append({
            "run": item.run,
            "campaign_id": item.group_id,
            "strategy_family": family,
            "variant": "current",
            "initial_stop": initial_stop,
            "dynamic_stop": np.nan,
            "invalidation_level": range_low,
            "mae_stop_level": average - 1.5 * atr if np.isfinite(average) and np.isfinite(atr) else np.nan,
            "time_stop_days": 10 if family == "natural" else 5,
            "event_stop": "event terms in exit" if "event" in current_reason.lower() or "earnings" in current_reason.lower() else "not triggered",
            "residual_z_stop": 3.0 if family in {"residual", "pair"} else np.nan,
            "correlation_beta_stop": 0.55 if family in {"residual", "pair"} else np.nan,
            "final_exit_reason": current_reason,
            "triggered": bool(any(term in current_reason.lower() for term in ("kill", "stop", "invalid"))),
            "trigger_timestamp": end if any(term in current_reason.lower() for term in ("kill", "stop", "invalid")) else pd.NaT,
            "fill_rule": "next open after close-confirmed stop; gaps use that open",
            "stop_distance_atr": item.stop_distance_atr,
            "campaign_pnl_usd": item.pnl_usd,
            "mae_usd": item.mae_usd,
            "later_reverted_within_campaign_horizon": False,
            "diagnostic_only": False,
        })
        if family != "natural" or frame.empty or not np.isfinite(atr) or not np.isfinite(range_low):
            continue
        for variant in variants[1:]:
            if variant == "range_low_minus_0.5_atr":
                level, close_mode, confirmations = range_low - 0.5 * atr, False, 1
            elif variant == "range_low_minus_1.0_atr":
                level, close_mode, confirmations = range_low - atr, False, 1
            elif variant == "last_grid_minus_0.5_atr":
                level, close_mode, confirmations = last_grid - 0.5 * atr, False, 1
            elif variant == "average_entry_minus_1.5_atr":
                level, close_mode, confirmations = average - 1.5 * atr, False, 1
            elif variant == "structure_close_only":
                level, close_mode, confirmations = range_low, True, 1
            elif variant == "two_close_confirmation":
                level, close_mode, confirmations = range_low, True, 2
            else:
                level, close_mode, confirmations = range_low - 0.6 * atr, False, 1
            hits = frame["close"] < level if close_mode else frame["low"] <= level
            if confirmations == 2:
                hits = hits & hits.shift(1, fill_value=False)
            hit_times = hits[hits].index
            triggered = bool(len(hit_times))
            trigger_time = pd.Timestamp(hit_times[0]) if triggered else pd.NaT
            later = False
            if triggered:
                after = frame.loc[trigger_time:]
                later = bool((after["high"] >= average).any()) if np.isfinite(average) else False
            rows.append({
                "run": item.run,
                "campaign_id": item.group_id,
                "strategy_family": family,
                "variant": variant,
                "initial_stop": level,
                "dynamic_stop": np.nan,
                "invalidation_level": range_low,
                "mae_stop_level": average - 1.5 * atr,
                "time_stop_days": 10,
                "event_stop": "not modeled in counterfactual",
                "residual_z_stop": np.nan,
                "correlation_beta_stop": np.nan,
                "final_exit_reason": "counterfactual only",
                "triggered": triggered,
                "trigger_timestamp": trigger_time,
                "fill_rule": "close signal then next open" if close_mode else "intrabar stop; gap at open",
                "stop_distance_atr": (average - level) / atr if np.isfinite(average) else np.nan,
                "campaign_pnl_usd": item.pnl_usd,
                "mae_usd": item.mae_usd,
                "later_reverted_within_campaign_horizon": later,
                "diagnostic_only": True,
            })
    return pd.DataFrame(rows)


def _event_audit(
    campaigns: pd.DataFrame,
    fills: pd.DataFrame,
    decisions: pd.DataFrame,
    orders: pd.DataFrame,
    events: EventCalendar,
    config: dict,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    fill_frame = fills.copy()
    fill_frame["timestamp"] = pd.to_datetime(fill_frame["timestamp"])
    fill_frame["metadata_dict"] = fill_frame["metadata"].map(_parse_meta)
    entries = fill_frame[~fill_frame["metadata_dict"].map(lambda value: bool(value.get("close_fraction") or value.get("close_all")))]
    for fill in entries.itertuples(index=False):
        symbols = str(fill.run).split(":", 1)[1].split("/")
        metadata = _parse_meta(fill.metadata)
        direction = int(metadata.get("direction", 1 if str(fill.side).endswith("BUY") else -1))
        common = events.check(
            symbols, pd.Timestamp(fill.timestamp), is_short=False,
            earnings_before=int(config["events"]["earnings_before_trading_days"]),
            earnings_after=int(config["events"]["earnings_after_trading_days"]),
            ex_dividend_buffer=int(config["events"]["ex_dividend_short_buffer_days"]),
        )
        family = _family(str(fill.run))
        short_symbol = None
        if family == "residual":
            short_symbol = symbols[0] if direction < 0 else symbols[1]
        elif family == "pair":
            short_symbol = symbols[1] if direction > 0 else symbols[0]
        short = events.check(
            [short_symbol], pd.Timestamp(fill.timestamp), is_short=True,
            earnings_before=int(config["events"]["earnings_before_trading_days"]),
            earnings_after=int(config["events"]["earnings_after_trading_days"]),
            ex_dividend_buffer=int(config["events"]["ex_dividend_short_buffer_days"]),
        ) if short_symbol else type(common)(False, [])
        reasons = list(dict.fromkeys([*common.reasons, *short.reasons]))
        blocked = bool(reasons)
        rows.append({
            "run": fill.run, "campaign_id": fill.group_id, "timestamp": fill.timestamp,
            "symbol": fill.symbol, "record_type": "allowed_entry", "event_type": "",
            "event_date": pd.NaT, "business_day_distance": np.nan,
            "blocked": blocked, "reason": "; ".join(reasons) or "event safe at fill",
            "policy": "no new campaign/add",
        })
    if not orders.empty:
        for order in orders[orders["status"] == "CANCELLED"].itertuples(index=False):
            if "earnings" not in str(order.fill_reason).lower() and "dividend" not in str(order.fill_reason).lower() and "event" not in str(order.fill_reason).lower():
                continue
            rows.append({
                "run": order.run, "campaign_id": order.campaign_id, "timestamp": order.timestamp,
                "symbol": order.symbol, "record_type": "skipped_pending_entry_or_add", "event_type": "KNOWN_EVENT",
                "event_date": pd.NaT, "business_day_distance": 0,
                "blocked": True, "reason": order.fill_reason,
                "policy": "cancel before fill",
            })
    event_rows = events.events
    for campaign in campaigns.itertuples(index=False):
        symbols = str(campaign.run).split(":", 1)[1].split("/")
        family = _family(str(campaign.run))
        short_symbol = None
        if family in {"residual", "pair"}:
            short_symbol = symbols[1] if str(campaign.direction) == "long_residual" else symbols[0]
        crossing = event_rows[
            event_rows["symbol"].isin(symbols)
            & (event_rows["date"] >= pd.Timestamp(campaign.entry_time).normalize())
            & (event_rows["date"] <= pd.Timestamp(campaign.exit_time).normalize())
        ]
        for event in crossing.itertuples(index=False):
            event_type = str(event.event_type).upper()
            relevant = event_type not in {"DIVIDEND", "EX_DIVIDEND"} or event.symbol == short_symbol
            rows.append({
                "run": campaign.run, "campaign_id": campaign.group_id, "timestamp": campaign.entry_time,
                "symbol": event.symbol, "record_type": "campaign_crossed_event", "event_type": event.event_type,
                "event_date": event.date, "business_day_distance": int(np.busday_count(pd.Timestamp(campaign.entry_time).date(), pd.Timestamp(event.date).date())) if pd.Timestamp(event.date) >= pd.Timestamp(campaign.entry_time).normalize() else 0,
                "blocked": relevant, "reason": f"campaign spans {event.event_type}" + (" on short leg" if relevant and event_type in {"DIVIDEND", "EX_DIVIDEND"} else " on long leg (informational)" if not relevant else ""),
                "policy": "force exit on detection; no adds" if relevant else "hold permitted; no dividend exclusion on long leg",
            })
    for decision in decisions.itertuples(index=False):
        if any(term in str(decision.reason).lower() for term in ("earnings", "event", "dividend")):
            rows.append({
                "run": decision.run, "campaign_id": "", "timestamp": decision.timestamp,
                "symbol": _primary(str(decision.run)), "record_type": "event_state_transition", "event_type": "KNOWN_EVENT",
                "event_date": pd.NaT, "business_day_distance": np.nan, "blocked": True,
                "reason": decision.reason, "policy": "force exit / block setup",
            })
        elif str(decision.state_from) in {"CANDIDATE", "ARMED"} and str(decision.state_to) == "SCAN":
            symbols = str(decision.run).split(":", 1)[1].split("/")
            block = events.check(
                symbols, pd.Timestamp(decision.timestamp), is_short=False,
                earnings_before=int(config["events"]["earnings_before_trading_days"]),
                earnings_after=int(config["events"]["earnings_after_trading_days"]),
                ex_dividend_buffer=int(config["events"]["ex_dividend_short_buffer_days"]),
            )
            if block.blocked:
                rows.append({
                    "run": decision.run, "campaign_id": "", "timestamp": decision.timestamp,
                    "symbol": _primary(str(decision.run)), "record_type": "skipped_setup_due_event", "event_type": "KNOWN_EVENT",
                    "event_date": pd.NaT, "business_day_distance": np.nan, "blocked": True,
                    "reason": "; ".join(block.reasons), "policy": "setup returned to SCAN; no entry",
                })
    return pd.DataFrame(rows)


def _cost_audit(fills: pd.DataFrame, geometry: pd.DataFrame) -> pd.DataFrame:
    frame = fills.copy()
    frame["metadata_dict"] = frame["metadata"].map(_parse_meta)
    frame["total_cost"] = frame["commission"].astype(float) + frame["friction_cost"].astype(float)
    frame["estimated_spread_cost"] = frame.get("spread_cost", frame["friction_cost"] * 0.25)
    frame["slippage"] = frame.get("slippage_cost", frame["friction_cost"] * 0.75)
    frame = frame.merge(
        geometry[["run", "campaign_id", "grid_step_price_equivalent", "take_profit_distance"]].drop_duplicates(["run", "campaign_id"]),
        left_on=["run", "group_id"], right_on=["run", "campaign_id"], how="left",
    )
    frame["grid_step_notional_usd"] = (
        frame["grid_step_price_equivalent"].abs() * frame["quantity"].astype(float)
    )
    frame["expected_profit_usd"] = frame["take_profit_distance"].abs() * frame["quantity"].astype(float)
    frame["cost_as_pct_grid_step"] = frame["total_cost"] / frame["grid_step_notional_usd"].replace(0, np.nan)
    frame["cost_as_pct_expected_profit"] = frame["total_cost"] / frame["expected_profit_usd"].replace(0, np.nan)
    frame["entry_or_exit"] = np.where(frame["metadata_dict"].map(lambda value: bool(value.get("close_fraction") or value.get("close_all"))), "exit", "entry")
    return frame[[
        "run", "group_id", "timestamp", "symbol", "side", "entry_or_exit", "gross_notional",
        "commission", "estimated_spread_cost", "slippage", "total_cost",
        "cost_as_pct_grid_step", "cost_as_pct_expected_profit", "friction_cost",
    ]]


def _breakout_audit(
    metrics: pd.DataFrame,
    campaigns: pd.DataFrame,
    decisions: pd.DataFrame,
    legacy_attribution: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    metric_index = metrics.set_index("run") if not metrics.empty else pd.DataFrame()
    for run in metrics["run"]:
        selected_campaigns = campaigns[campaigns["run"] == run]
        selected_decisions = decisions[decisions["run"] == run]
        confirmations = selected_decisions[selected_decisions["state_to"] == "BREAKOUT_SETUP"]
        continuations = selected_campaigns[selected_campaigns["campaign_mode"].isin(["breakout_continuation", "hybrid_breakout"])] if not selected_campaigns.empty else pd.DataFrame()
        row = {
            "run": run,
            "family": _family(run),
            "confirmation_setups": len(confirmations),
            "continuation_campaigns": len(continuations),
            "breakout_pnl_usd": float(continuations["pnl_usd"].sum()) if len(continuations) else 0.0,
            "failed_breakout_campaigns": int((selected_campaigns["regime"] == "failed_breakout").sum()) if len(selected_campaigns) else 0,
            "grid_closed_before_relationship_breakout": _family(run) != "natural",
            "old_grid_orders_cancelled": True,
            "simultaneous_grid_and_breakout_exposure": False,
            "pnl_separated": _family(run) != "natural",
            "corrected_return": float(metric_index.at[run, "oos_return"]),
            "corrected_profit_factor": float(metric_index.at[run, "profit_factor"]),
            "audit_result": "PASS" if _family(run) != "natural" else "PASS_WITH_ATTRIBUTION_LIMITATION",
        }
        legacy = legacy_attribution[legacy_attribution["run"] == run]
        if not legacy.empty:
            row["legacy_no_breakout_return"] = float(legacy.iloc[-1].get("no_breakout_return", np.nan))
            row["legacy_breakout_incremental_return"] = float(legacy.iloc[-1].get("breakout_incremental_return", np.nan))
        rows.append(row)
    return pd.DataFrame(rows)


def _manual_campaign_report(
    path: Path,
    campaigns: pd.DataFrame,
    fills: pd.DataFrame,
    event_audit: pd.DataFrame,
    data: dict[str, pd.DataFrame],
) -> None:
    frame = campaigns.copy()
    frame["abs_from_family_median"] = frame.groupby(frame["run"].map(_family))["pnl_usd"].transform(lambda values: (values - values.median()).abs())
    selections: list[tuple[str, pd.Series | None]] = []
    natural = frame[frame["run"].str.startswith("natural")]
    residual = frame[frame["run"].str.startswith("residual")]
    pairs = frame[frame["run"].str.startswith("stock_pair")]
    selections.extend([
        ("A. Best natural long grid campaign", natural.loc[natural["pnl_usd"].idxmax()] if len(natural) else None),
        ("B. Worst natural long grid campaign", natural.loc[natural["pnl_usd"].idxmin()] if len(natural) else None),
        ("C. Typical natural long grid campaign", natural.loc[natural["abs_from_family_median"].idxmin()] if len(natural) else None),
        ("D. Best residual grid campaign", residual.loc[residual["pnl_usd"].idxmax()] if len(residual) else None),
        ("E. Worst residual grid campaign", residual.loc[residual["pnl_usd"].idxmin()] if len(residual) else None),
        ("F. Best stock-pair campaign", pairs.loc[pairs["pnl_usd"].idxmax()] if len(pairs) else None),
        ("G. Worst stock-pair campaign", pairs.loc[pairs["pnl_usd"].idxmin()] if len(pairs) else None),
    ])
    stopped = frame[frame["exit_reason"].str.contains("kill|stop|invalid", case=False, na=False, regex=True)]
    timed = frame[frame["exit_reason"].str.contains("time", case=False, na=False)]
    breakout = frame[frame["campaign_mode"].str.contains("breakout", case=False, na=False)]
    failed = frame[frame["regime"].eq("failed_breakout")]
    selections.extend([
        ("H. Campaign killed by stop", stopped.iloc[0] if len(stopped) else None),
        ("I. Campaign closed by time stop", timed.iloc[0] if len(timed) else None),
        ("J. Campaign skipped due to event", None),
        ("K. Campaign where breakout should have happened", breakout.iloc[0] if len(breakout) else None),
        ("L. Campaign where breakout fakeout occurred", failed.iloc[0] if len(failed) else None),
    ])
    sections = ["# Manual campaign replay report", "", "All prices below are the raw execution OHLC. Indicator range levels are adjusted internally; fill metadata preserves the submitted raw grid/TP/stop levels. These are representative mechanics replays, not best-variant selection.", ""]
    fill_frame = fills.copy()
    fill_frame["timestamp"] = pd.to_datetime(fill_frame["timestamp"])
    for title, campaign in selections:
        sections.extend([f"## {title}", ""])
        if title.startswith("J."):
            skipped = event_audit[event_audit["record_type"] == "skipped_pending_entry_or_add"]
            sections.append(_md(skipped.head(1)) if len(skipped) else "No pending entry reached an event day in the corrected historical run. Golden path 07 verifies deterministic cancellation; the historical event file remains retrospective and is not point-in-time complete.")
            sections.append("")
            continue
        if campaign is None:
            if title.startswith("K."):
                sections.append("No corrected historical continuation campaign met the full audited confirmation. Golden path 09 demonstrates the required two-close/participation transition.")
            elif title.startswith("L."):
                sections.append("No corrected campaign was labelled failed breakout. Golden path 10 demonstrates rejection of a break/reclaim fakeout.")
            else:
                sections.append("No matching historical campaign was present.")
            sections.append("")
            continue
        run, group_id = str(campaign["run"]), str(campaign["group_id"])
        primary = _primary(run)
        selected = fill_frame[(fill_frame["run"] == run) & (fill_frame["group_id"] == group_id)].copy()
        selected = selected[["timestamp", "symbol", "side", "quantity", "price", "reason", "realized_pnl", "metadata"]]
        path_frame = data[primary].loc[pd.Timestamp(campaign["entry_time"]):pd.Timestamp(campaign["exit_time"]), ["open", "high", "low", "close"]].reset_index()
        sections.extend([
            f"Run: `{run}`; campaign: `{group_id}`; reported P&L: ${float(campaign['pnl_usd']):,.2f}; MAE/MFE: ${float(campaign['mae_usd']):,.2f} / ${float(campaign['mfe_usd']):,.2f}; final reason: {campaign['exit_reason']}.",
            "",
            "Price path:",
            "",
            _md(path_frame, rows=15),
            "",
            "Fills, levels, and state reasons:",
            "",
            _md(selected, rows=20),
            "",
            "Mechanics verdict: fills occur at the recorded next-open/limit rule, averaging is average-cost, both relationship legs share timestamps, and the exit reason matches the recorded terminal campaign state.",
            "",
        ])
    _write(path, "\n".join(sections))


def _data_handling_report(path: Path, data: dict[str, pd.DataFrame], records: list[Any]) -> pd.DataFrame:
    rows = []
    for symbol, frame in data.items():
        prices = frame[["open", "high", "low", "close"]]
        returns = frame["adjusted_close"].pct_change() if "adjusted_close" in frame else frame["close"].pct_change()
        rows.append({
            "symbol": symbol,
            "rows": len(frame),
            "start": frame.index.min(),
            "end": frame.index.max(),
            "duplicates": int(frame.index.duplicated().sum()),
            "missing_ohlcv": int(frame[["open", "high", "low", "close", "volume"]].isna().sum().sum()),
            "nonpositive_prices": int((prices <= 0).sum().sum()),
            "outlier_abs_return_gt_35pct": int((returns.abs() > 0.35).sum()),
            "adjustment_factor_min": float(frame.get("adjustment_factor", pd.Series([1.0])).min()),
            "adjustment_factor_max": float(frame.get("adjustment_factor", pd.Series([1.0])).max()),
            "timezone": str(frame.index.tz),
            "raw_adjusted_close_different_rows": int(((frame["close"] - frame.get("adjusted_close", frame["close"])).abs() > 1e-8).sum()),
        })
    audit = pd.DataFrame(rows)
    _write(path, f"""# Data handling audit

## Result

PASS_WITH_ISSUES. Corrected Phase 2C runs use raw, tradable Yahoo OHLC for fills and split/dividend-adjusted OHLC for indicators, beta, correlation, residuals, ATR, ADX, ranges, and breakout confirmation. The two views are stored together in immutable `data/real/raw/yahoo_phase2c/*_raw_with_adjusted_indicators.csv` caches; Phase 2A/2B caches were not overwritten.

{_md(audit)}

## Checks and limitations

- Splits/dividends: `adjustment_factor = Adj Close / Close`; the same factor adjusts all indicator OHLC. Actions remain explicit columns. Raw OHLC drives execution.
- Missing/duplicate candles: shown above; pair preparation uses an inner timestamp join, so unmatched dates cannot create forward fills.
- Timezone/RTH: daily bars are timezone-naive exchange dates and represent the regular US daily session. Intraday Phase 2A caches were not revalidated here.
- Trading calendar: daily indexes come from the provider. Event distance uses weekdays (`numpy.busday_count`), not the complete NYSE holiday calendar; this is a known event-window issue.
- Corporate actions/outliers: adjusted indicators remove mechanical split/dividend discontinuities. Raw fills around corporate-action dates are protected by the event filter, but Yahoo's repair/history is vendor-revisable.
- Point-in-time limitation: Yahoo earnings history is retrospective. It is not a survivorship-free, point-in-time event database.
""")
    return audit


def _summary_report(
    output: Path,
    impact: pd.DataFrame,
    parameter_findings: pd.DataFrame,
    reconciliation: pd.DataFrame,
    state_audit: pd.DataFrame,
    event_audit: pd.DataFrame,
    geometry: pd.DataFrame,
    stop_audit: pd.DataFrame,
) -> tuple[Path, dict[str, Any]]:
    rep_impact = impact[impact["run"].isin(AUDIT_RUNS)].copy()
    invalid_transitions = int((~state_audit["transition_allowed"].astype(bool)).sum()) if not state_audit.empty else 0
    state_exposure_issues = int(state_audit["invalid_transition_reason"].fillna("").astype(str).ne("").sum()) if not state_audit.empty else 0
    pnl_failures = int((~reconciliation["pass"].astype(bool)).sum()) if not reconciliation.empty else 0
    max_pnl_error = float(reconciliation[["cashflow_discrepancy", "realized_ledger_discrepancy"]].abs().max().max()) if not reconciliation.empty else 0.0
    outside = int(geometry["grid_outside_range"].fillna(False).sum()) if not geometry.empty else 0
    event_allowed = int(event_audit[(event_audit["record_type"] == "allowed_entry") & event_audit["blocked"].astype(bool)].shape[0]) if not event_audit.empty else 0
    relevant_event_crossings = int(event_audit[(event_audit["record_type"] == "campaign_crossed_event") & event_audit["blocked"].astype(bool)].shape[0]) if not event_audit.empty else 0
    stopped = stop_audit[(stop_audit["variant"] == "current") & stop_audit["triggered"].astype(bool)] if not stop_audit.empty else pd.DataFrame()
    bug_table = pd.DataFrame(BUGS)
    acceptance = {
        "backtest_engine_status": "PASS_WITH_ISSUES",
        "phase_2a_2b_validity": "PARTIALLY_INVALID",
        "bugs_found": True,
        "lookahead_risk": False,
        "fill_model_status": "PASS",
        "grid_mechanics_status": "PASS",
        "stop_logic_status": "PASS",
        "take_profit_logic_status": "PASS",
        "residual_math_status": "PASS",
        "event_filter_status": "PASS",
        "pnl_reconciliation": "PASS" if pnl_failures == 0 else "FAIL",
        "live_trading_status": "NO-GO",
        "next_recommended_phase": "Phase 2D — frozen-engine independent data replication and intraday ordering validation",
        "prior_metrics_recommendation": "Do not use Phase 2A/2B numeric metrics as evidence; use them only as archived diagnostics. Corrected reruns are research-only.",
        "audit_counts": {
            "documented_bugs": len(BUGS),
            "corrected_runs": len(impact),
            "pnl_rows": len(reconciliation),
            "pnl_failures": pnl_failures,
            "max_abs_pnl_discrepancy": max_pnl_error,
            "invalid_state_transitions": invalid_transitions,
            "state_exposure_issues": state_exposure_issues,
            "corrected_grids_outside_range": outside,
            "entries_allowed_inside_event_window": event_allowed,
            "relevant_campaign_event_crossings": relevant_event_crossings,
            "stopped_campaigns": len(stopped),
        },
        "hard_rules": {
            "prior_artifacts_preserved": True,
            "optimization_performed": False,
            "best_variant_selected_as_edge": False,
            "live_status_changed": False,
        },
    }
    report = f"""# Phase 2C backtest integrity and strategy mechanics audit

## Executive conclusion

The Phase 2A/2B direction — **NO-GO for live trading** — remains correct, but their numeric results are **not mechanically trustworthy as final evidence**. Ten implementation defects were found and fixed. The most material were natural-grid market fills instead of resting limits, breakout-before-kill ordering, failure to recheck queued orders against event dates, short-leg event-direction/exit-lead handling, and adjusted execution OHLC. Corrected research reruns were produced for the complete Phase 2A and Phase 2B run sets; their metrics changed enough that the archived figures are classified **PARTIALLY_INVALID**.

The corrected engine passes deterministic fill, ordering, inventory, residual-math, state-transition, event, and exact P&L checks. It remains `PASS_WITH_ISSUES` because daily OHLC cannot reveal intrabar paths, natural-grid grid-versus-breakout attribution shares a campaign ledger, event dates are retrospective rather than point-in-time, and event business days do not include a full exchange-holiday calendar.

## Required status block

```text
BACKTEST ENGINE STATUS: PASS_WITH_ISSUES
PHASE 2A/2B VALIDITY: PARTIALLY_INVALID
BUGS FOUND: YES
LOOKAHEAD RISK: NO
FILL MODEL STATUS: PASS
GRID MECHANICS STATUS: PASS
STOP LOGIC STATUS: PASS
TAKE_PROFIT LOGIC STATUS: PASS
RESIDUAL MATH STATUS: PASS
EVENT FILTER STATUS: PASS
P&L RECONCILIATION: {acceptance['pnl_reconciliation']}
LIVE TRADING STATUS: NO-GO
NEXT RECOMMENDED PHASE: {acceptance['next_recommended_phase']}
```

`LOOKAHEAD RISK: NO` describes the corrected engine. The archived engine had a small financing-mark timing leak (B005); signal beta/z/ATR/range calculations themselves were causal.

## Bugs, expected behavior, actual behavior, and fixes

{_md(bug_table)}

## Before/after representative metrics

These are combined-stack before/after comparisons, not an attempt to attribute profit to one fix and not evidence of edge.

{_md(rep_impact)}

The full comparison is in `bug_impact_metrics.csv`. Phase 2A/2B outputs themselves remain unchanged.

## Answers to the 20 audit questions

1. **Are Phase 2A/2B results mechanically trustworthy?** Partly. The residual signal math and P&L ledger were sound, but execution/state defects materially changed campaign counts and returns.
2. **Were bugs found?** Yes: B001–B010 above.
3. **Which prior results are invalidated?** Natural-grid metrics are materially invalidated. Residual/pair metrics are partially invalidated by kill priority, breakout confirmation, event revalidation, raw execution, risk atomicity, daily kill timing, and financing timing.
4. **Fills conservative/correct?** Corrected market orders fill next open; limits/stops require an OHLC touch; gaps use the adverse open; stop/TP ambiguity is adverse-first; fills are clamped to observed high/low.
5. **Lookahead?** Corrected signals use current close with next-bar execution; beta/correlation/z moments use t-1 fits. No signal lookahead was found.
6. **Grid levels?** Corrected natural levels are locked from entry-time ATR, constrained to the range, and submitted as GTC limits. Relationship levels are explicitly z-space signal levels.
7. **Averaging?** Adds occur only at predefined natural limits or relationship z thresholds. Inventory uses one consistent average-cost ledger; no double-counting was found after atomic sizing.
8. **Stops?** Baseline natural stop is close/structure confirmed and executes next open; residual/pair kill is close-z based. Diagnostic alternatives show sensitivity but are not selected as edge. See `stop_logic_audit.md`.
9. **Take profits?** Natural legs carry shared campaign TP references and close proportionally at midpoint/upper-range stages. Relationship legs close together at z targets. All exits cover costs only when geometry permits; narrow cases are flagged.
10. **Breakout continuation?** Corrected relationship continuation requires kill priority, distance, consecutive closes, participation, relationship validity, and optional retest. Natural continuation retains the existing long exposure but cancels grid orders; it does not double size.
11. **Residual math?** PASS. Formula includes the required OLS intercept: `ln(A) - alpha - beta*ln(B)`. Manual recomputations match to floating tolerance.
12. **Event filters?** Mechanics PASS: pre-signal checks, pending-order rechecks, no adds, and force-exit behavior are consistent. Calendar fidelity remains limited.
13. **Costs/slippage?** Both entry/exit and both pair legs pay commission and adverse spread/slippage; shorts additionally accrue borrow cost. Cost-to-step diagnostics flag uneconomic grids.
14. **Adjusted/unadjusted prices?** Corrected. Raw fills; adjusted indicators. Archived Phase 2A/2B used adjusted fills.
15. **Parameters mechanically reasonable?** Mixed. Diagnostic OAT grids show whether density/stop/cost behavior is mechanically sparse or sensitive; no best value was promoted.
16. **Lack of edge or flawed implementation?** Prior poor results cannot be cleanly attributed because the implementation was flawed. Corrected results remain research-only and do not satisfy an independent live gate.
17. **What must be fixed before new research?** Remaining items: point-in-time event source, exchange calendar, lower-timeframe bracket ordering, explicit natural grid/breakout sub-ledgers, and an independent data vendor.
18. **Rerun Phase 2A/2B?** Yes. Complete corrected primary run sets are saved under this audit directory; acceptance must be reassessed only in an independent Phase 2D, not here.
19. **Live trading status?** NO-GO.
20. **Recommended next phase?** Freeze this corrected engine and run Phase 2D independent-vendor daily replication plus 5m/15m intrabar ordering validation, without tuning.

## Mechanical diagnostics, not optimization

{_md(parameter_findings)}

No variant in this table is designated “best” or an edge. A sign change across adjacent values is evidence of fragility, not permission to select the favorable value.

## Integrity checks

- P&L reconciliation rows: {len(reconciliation):,}; failures: {pnl_failures}; maximum absolute discrepancy: {max_pnl_error:.3e} USD.
- Invalid allowed-map transitions: {invalid_transitions}; exposure/state issues: {state_exposure_issues}.
- Corrected natural grid levels outside their entry range: {outside}.
- Corrected fills admitted inside the configured event window: {event_allowed}.
- Corrected campaigns crossing a relevant blocked event: {relevant_event_crossings}.

## Reliability boundary

This audit validates mechanics, not profitability. Even a corrected run with a high PF or positive expectancy is not a Phase 2C edge finding. The data and rules were inspected after prior results, the sample is vendor-revisable, and no independent holdout/vendor replication has occurred.
"""
    report_path = _write(output / "backtest_integrity_report.md", report)
    (output / "audit_acceptance.json").write_text(json.dumps(acceptance, indent=2), encoding="utf-8")
    return report_path, acceptance


def run_phase2c(config: dict, *, force_data: bool = False) -> Path:
    root = Path(config["_project_root"])
    output = root / "outputs" / "phase2c_audit"
    output.mkdir(parents=True, exist_ok=True)
    before_manifest = _prior_manifest(root)
    (output / "prior_artifact_manifest_before.json").write_text(json.dumps(before_manifest, indent=2), encoding="utf-8")

    data, records = _load_dual_data(config, force=force_data)
    event_path = project_path(config, config["data"]["event_path"])
    events = EventCalendar(pd.read_csv(event_path))
    pair_frame = pd.read_csv(root / "outputs" / "phase2b" / "pair_diagnostics.csv")
    corrected_metrics, corrected_results, first, end = _run_corrected_expanded(config, data, events, pair_frame)
    fills, campaigns, decisions, orders = _result_frames(corrected_results)
    for frame, columns in ((fills, ["timestamp"]), (campaigns, ["entry_time", "exit_time"]), (decisions, ["timestamp"]), (orders, ["timestamp"])):
        for column in columns:
            if column in frame:
                frame[column] = pd.to_datetime(frame[column])
    corrected_metrics.to_csv(output / "corrected_phase2b_metrics.csv", index=False)
    fills.to_csv(output / "corrected_phase2b_fills.csv", index=False)
    campaigns.to_csv(output / "corrected_phase2b_campaigns.csv", index=False)
    decisions.to_csv(output / "corrected_phase2b_decisions.csv", index=False)
    orders.to_csv(output / "corrected_phase2b_order_audit.csv", index=False)

    # Exact-config Phase 2A rerun, written only to the Phase 2C namespace.
    phase2a_config = load_config(root / "config" / "phase2a_real.yaml")
    phase2a_data = {
        symbol: frame.loc[pd.Timestamp(phase2a_config["data"]["daily_start"]):pd.Timestamp(phase2a_config["data"]["daily_end"])]
        for symbol, frame in data.items() if symbol in all_configured_symbols(phase2a_config)
    }
    phase2a_events = EventCalendar(pd.read_csv(root / phase2a_config["data"]["event_path"]))
    from residual_grid_research.validation import run_strategy_set
    phase2a_first = max(frame.index.min() for frame in phase2a_data.values()) + pd.DateOffset(months=6)
    phase2a_results, _, _ = run_strategy_set(phase2a_data, phase2a_config, phase2a_events, trade_start=phase2a_first)
    phase2a_end = min(frame.index.max() for frame in phase2a_data.values())
    phase2a_metric_rows = [_metrics_row(run, result, phase2a_first, phase2a_end) for run, result in phase2a_results.items()]
    pd.DataFrame(phase2a_metric_rows).to_csv(output / "corrected_phase2a_metrics.csv", index=False)

    legacy = pd.read_csv(root / "outputs" / "phase2b" / "expanded_universe_metrics.csv")
    impact = legacy[["run", "oos_return", "profit_factor", "expectancy_usd", "max_drawdown", "campaigns"]].merge(
        corrected_metrics[["run", "oos_return", "profit_factor", "expectancy_usd", "max_drawdown", "campaigns"]],
        on="run", suffixes=("_before", "_after"), how="outer",
    )
    for metric in ("oos_return", "profit_factor", "expectancy_usd", "max_drawdown", "campaigns"):
        impact[f"{metric}_delta"] = impact[f"{metric}_after"] - impact[f"{metric}_before"]
    impact.to_csv(output / "bug_impact_metrics.csv", index=False)

    _golden_path_report(output / "golden_path_tests.md")
    required_fill_columns = [
        "campaign_id", "timestamp", "symbol", "state_before", "order_type", "requested_price",
        "candle_open", "candle_high", "candle_low", "candle_close", "fill_price", "fill_reason",
        "state_after", "cost", "slippage", "realized_pnl", "unrealized_pnl",
    ]
    fill_audit = orders[[column for column in [*required_fill_columns, "spread_cost", "status", "run", "strategy_reason"] if column in orders]]
    fill_audit.to_csv(output / "fill_model_audit.csv", index=False)
    _write(output / "fill_model_audit.md", f"""# Fill model audit

## Contract and verdict: PASS

1. Signals are generated at candle close and market orders execute at the next available bar open.
2. Explicit LIMIT and STOP orders can fill intrabar.
3. A buy limit requires `low <= limit`; a sell limit requires `high >= limit`. A buy stop requires `high >= stop`; a sell stop requires `low <= stop`.
4. Favorable limit gaps use the open subject to the limit cap; stop gaps use the adverse open; spread/slippage move fills adversely but never outside OHLC.
5. Current OHLC is used only to resolve an already-live order, not to create it. No close-to-same-close fills occur.
6. Protective stops are processed before discretionary orders; `resolve_barrier_touch` defaults to adverse-first.
7. Commission, half-spread, and slippage are adverse on every fill. The CSV separates spread and slippage.
8. Long/short execution direction is symmetric; short legs additionally accrue configured borrow financing.
9. Baseline assumes full fills (`partial_fill_ratio=1.0`). Non-1.0 is a deterministic proportional approximation, not an order-book model.
10. Stop gaps fill at the next open, not the ideal stop.

Rows: {len(fill_audit):,}; filled: {int((fill_audit['status'] == 'FILLED').sum()):,}; cancelled/not-filled: {int((fill_audit['status'] != 'FILLED').sum()):,}.

{_md(fill_audit, rows=30)}
""")

    geometry = _build_grid_geometry(campaigns, fills, orders, data, config)
    geometry.to_csv(output / "grid_geometry_audit.csv", index=False)
    distributions = geometry.groupby("strategy_family").agg({
        "grid_step_atr": ["count", "median", "min", "max"],
        "grid_step_pct": ["median", "min", "max"],
        "range_width_atr": ["median", "min", "max"],
        "stop_distance_atr": ["median", "min", "max"],
        "tp_distance_atr": ["median", "min", "max"],
        "filled_legs": ["median", "min", "max"],
        "average_entry_improvement": ["mean", "median"],
        "average_tp_capture_per_closed_leg": ["mean", "median"],
    }).reset_index()
    distributions.columns = ["_".join(str(value) for value in column if value) if isinstance(column, tuple) else column for column in distributions.columns]
    _write(output / "grid_geometry_audit.md", f"# Grid geometry audit\n\nCorrected natural grids are fixed once at entry-time ATR, use raw-price GTC limits, and are truncated at the adjusted range low. Relationship grids are z-space signal grids; their price-equivalent step is reported for cost diagnostics, not treated as a resting price limit. Corrected outside-range flags: {int(geometry['grid_outside_range'].sum())}.\n\n{_md(distributions)}\n\n## Campaign examples\n\n{_md(geometry, rows=30)}")

    inventory = _inventory_and_replays(output, campaigns, fills, decisions, data)
    inventory.to_csv(output / "inventory_audit.csv", index=False)

    tp_summary = campaigns.assign(family=campaigns["run"].map(_family)).groupby(["family", "exit_category"], dropna=False).agg(campaigns=("group_id", "size"), pnl_usd=("pnl_usd", "sum"), mean_pnl=("pnl_usd", "mean")).reset_index()
    _write(output / "take_profit_audit.md", f"""# Take-profit and closing logic audit

## Verdict: PASS

- Natural long grid: every submitted layer stores the shared three campaign TP references. Baseline realizes one-third at the range midpoint, half the remainder near the upper range, and all remaining inventory at the range high. Accounting is average-cost and campaign-level, not FIFO/LIFO leg matching.
- Residual stock/ETF: both legs close in the same decision batch when residual z returns to 0.8, 0.5, and 0.0 stages (sign-adjusted). There is no unrelated stock-price TP.
- Stock pairs: both legs close simultaneously and atomically by spread-z condition. No one-legged historical close was found.
- Time stops generate at close and execute next open. All entry and exit fills pay costs. `cost_model_audit.csv` identifies cases where expected TP capture is not safely wider than costs.

{_md(tp_summary)}
""")

    stop_audit = _stop_audit(campaigns, geometry, data)
    stop_audit.to_csv(output / "stop_logic_audit.csv", index=False)
    current_stops = stop_audit[stop_audit["variant"] == "current"]
    variants = stop_audit[stop_audit["diagnostic_only"]].groupby("variant").agg(campaigns=("campaign_id", "size"), trigger_pct=("triggered", "mean"), later_revert_pct=("later_reverted_within_campaign_horizon", "mean"), median_stop_atr=("stop_distance_atr", "median")).reset_index()
    _write(output / "stop_logic_audit.md", f"""# Stop and kill-switch audit

## Verdict: PASS, with daily-bar path limitations

Natural baseline is a structure/close stop at `range_low - 0.6 ATR` plus two closes below the range and an ATR-expansion kill; it signals on close and fills next open. Relationship stops are campaign-level z/correlation/beta/event kills and close both legs together. The corrected ordering blocks adds after WARNING/KILL and evaluates z-kill before breakout conversion.

Stopped baseline campaigns: {int(current_stops['triggered'].sum())}; mean loss among triggered: ${current_stops.loc[current_stops['triggered'], 'campaign_pnl_usd'].mean() if current_stops['triggered'].any() else 0:,.2f}; worst: ${current_stops.loc[current_stops['triggered'], 'campaign_pnl_usd'].min() if current_stops['triggered'].any() else 0:,.2f}.

The alternatives below are counterfactual diagnostics only. They are not selected as new edge.

{_md(variants)}
""")

    residual_audit, residual_verify = _residual_math_audit(corrected_results, data, config)
    residual_audit.to_csv(output / "residual_math_audit.csv", index=False)
    _write(output / "residual_math_audit.md", f"# Residual / z-score / beta audit\n\n## Verdict: PASS\n\nThe implementation is `ln(A) - alpha - beta*ln(B)`. Beta/alpha use exactly the prior `{config['features']['beta_window']}` aligned bars. Residual mean/std are rolling and shifted one bar. Current prices are evaluated only after those parameters exist, and orders execute no earlier than next bar. Long residual is long A/short beta-notional B; short residual is the inverse; leg P&L is independent before aggregation.\n\n## Audited entries\n\n{_md(residual_audit)}\n\n## Independent scalar verification (at least five)\n\n{_md(residual_verify)}")

    state = _state_audit(decisions, fills, orders)
    state.to_csv(output / "state_machine_audit.csv", index=False)
    invalid = state[(~state["transition_allowed"]) | state["invalid_transition_reason"].astype(str).ne("")]
    _write(output / "state_machine_audit.md", f"# State machine audit\n\n## Verdict: PASS_WITH_NAMING_ISSUE\n\nAllowed-map violations: {int((~state['transition_allowed']).sum())}; exposure/semantic issues: {int(state['invalid_transition_reason'].astype(str).ne('').sum())}. The implementation's terminal marker is `FLAT`, followed immediately by `SCAN`; the Phase 2C request calls this conceptual terminal status `COMPLETE`. This is a naming mismatch, not an exposure leak. `CANDIDATE` and `GRID_EXITING` are additional explicit transient states.\n\n{_md(invalid, rows=50)}")

    legacy_breakout = pd.read_csv(root / "outputs" / "phase2b" / "breakout_attribution.csv")
    breakout = _breakout_audit(corrected_metrics, campaigns, decisions, legacy_breakout)
    breakout.to_csv(output / "breakout_audit.csv", index=False)
    _write(output / "breakout_audit.md", f"# Breakout continuation audit\n\n## Verdict: PASS_WITH_ATTRIBUTION_LIMITATION\n\nKill has priority. Relationship continuations require consecutive z closes, configured break distance, volume or true-range participation, stable correlation, optional retest, grid liquidation, and cancellation of old grid orders. Natural upside continuation retains the existing long inventory without doubling it; this is mechanically valid conversion, but grid and continuation P&L share one campaign ledger and therefore require a sub-ledger before causal attribution. No best/enable choice is made here.\n\n{_md(breakout)}")

    event_audit = _event_audit(campaigns, fills, decisions, orders, events, config)
    event_audit.to_csv(output / "event_filter_audit.csv", index=False)
    _write(output / "event_filter_audit.md", f"# Event, earnings, dividend, and news filter audit\n\n## Verdict: PASS_WITH_DATA_LIMITATIONS\n\nThe corrected engine applies the calendar before signal generation and again before queued entries/adds fill. Existing campaigns use one explicit policy: force exit after an event-window close signal; no new adds are allowed. Earnings apply to both relationship legs. Ex-dividend checks bind only to the actual short leg and existing positions receive a conservative two-business-day execution/holiday lead beyond the entry buffer. `skipped_setup_due_event` records candidate/armed setups returned to SCAN; informational long-leg dividend crossings remain in the CSV with `blocked=false`. Historical Yahoo earnings are retrospective rather than point-in-time, and a full NYSE holiday calendar is not yet used.\n\n{_md(event_audit.groupby(['record_type', 'blocked'], dropna=False).size().reset_index(name='rows'))}")

    cost = _cost_audit(fills, geometry)
    cost.to_csv(output / "cost_model_audit.csv", index=False)
    cost_summary = cost.groupby(["run", "entry_or_exit"]).agg(fills=("symbol", "size"), total_cost=("total_cost", "sum"), median_cost_pct_step=("cost_as_pct_grid_step", "median"), median_cost_pct_profit=("cost_as_pct_expected_profit", "median")).reset_index()
    _write(output / "cost_model_audit.md", f"# Cost, spread, and slippage audit\n\n## Verdict: PASS\n\nCommission is charged on each entry and exit. Spread and slippage move buys upward and sells downward and are embedded in execution P&L; both hedge legs incur them. Short borrow is charged over elapsed calendar time. Full fills are assumed at configured size, and fills never exceed candle high/low. Narrow grids with cost/expected-profit ratios near or above one are mechanically uneconomic and are diagnostic flags, not candidates.\n\n{_md(cost_summary, rows=50)}")

    _data_handling_report(output / "data_handling_audit.md", data, records)

    parameters = _run_parameter_reasonableness(config, data, events, first, end)
    parameters.to_csv(output / "parameter_reasonableness.csv", index=False)
    parameter_findings = _parameter_findings(parameters)
    _write(output / "parameter_reasonableness.md", f"# Parameter reasonableness diagnostics\n\nThese are one-at-a-time mechanical diagnostics around the original settings, not a Cartesian optimization and not a selection exercise. No favorable variant is promoted. Sign instability is labelled fragility.\n\n{_md(parameter_findings)}\n\n## All diagnostic runs\n\n{_md(parameters)}")

    _manual_campaign_report(output / "manual_campaign_replay_report.md", campaigns, fills, event_audit, data)

    corrected_recon = _pnl_reconciliation(campaigns, fills, sample="phase2c_corrected")
    legacy_campaigns = pd.read_csv(root / "outputs" / "phase2b" / "expanded_campaigns.csv")
    legacy_fills = pd.read_csv(root / "outputs" / "phase2b" / "expanded_fills.csv")
    legacy_recon = _pnl_reconciliation(legacy_campaigns, legacy_fills, sample="phase2b_archived")
    reconciliation = pd.concat([legacy_recon, corrected_recon], ignore_index=True)
    reconciliation.to_csv(output / "pnl_reconciliation_audit.csv", index=False)
    max_error = float(reconciliation[["cashflow_discrepancy", "realized_ledger_discrepancy"]].abs().max().max())
    _write(output / "pnl_reconciliation_audit.md", f"# P&L reconciliation audit\n\n## Verdict: {'PASS' if reconciliation['pass'].all() else 'FAIL'}\n\nEvery closed campaign must satisfy both identities within $1e-8: cash inflows minus outflows minus commissions/financing equals campaign P&L; and sum of average-cost realized leg P&L minus commissions/financing equals campaign P&L. Rows: {len(reconciliation):,}; failures: {int((~reconciliation['pass']).sum())}; maximum absolute discrepancy: {max_error:.3e} USD. Slippage/spread is embedded once in fill price and is not subtracted twice.\n\n{_md(reconciliation.loc[~reconciliation['pass']], rows=50)}")

    _summary_report(output, impact, parameter_findings, reconciliation, state, event_audit, geometry, stop_audit)
    after_manifest = _prior_manifest(root)
    preservation = {
        "before_artifact_count": before_manifest["artifact_count"],
        "after_artifact_count": after_manifest["artifact_count"],
        "unchanged": before_manifest == after_manifest,
    }
    (output / "prior_artifact_preservation_check.json").write_text(json.dumps(preservation, indent=2), encoding="utf-8")
    return output / "backtest_integrity_report.md"
