from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from residual_grid_research.backtest.metrics import compute_baselines
from residual_grid_research.config import project_path
from residual_grid_research.data import YahooFinanceClient
from residual_grid_research.reports import write_real_data_report
from residual_grid_research.research import all_configured_symbols, relationship_diagnostics
from residual_grid_research.validation import (
    acceptance_gate,
    load_events,
    load_real_data,
    metrics_frame,
    robustness_by_run,
    run_oat_sensitivity,
    run_strategy_set,
    select_sensitivity_targets,
    strategy_specs,
    walk_forward_oos,
)


def fetch_phase2a_data(config: dict, *, force: bool = False) -> dict[str, Any]:
    client = YahooFinanceClient(project_path(config, config["data"]["cache_dir"]))
    symbols = all_configured_symbols(config)
    daily, daily_records = client.fetch_universe_daily(
        symbols,
        str(config["data"]["daily_start"]),
        str(config["data"]["daily_end"]),
        force=force,
    )
    stocks = sorted(set(config["universe"]["natural_long_symbols"]))
    event_path = project_path(config, config["data"]["event_path"])
    events, event_warnings = client.build_historical_events(stocks, daily, event_path)
    intraday, intraday_records = client.fetch_universe_intraday(
        symbols,
        period=str(config["data"]["intraday_period"]),
        interval=str(config["data"]["intraday_interval"]),
        force=force,
    )
    manifest = {
        "daily": [{**asdict(record), "quality": asdict(record.quality)} for record in daily_records],
        "intraday": [{**asdict(record), "quality": asdict(record.quality)} for record in intraday_records],
        "events": len(events),
        "event_warnings": event_warnings,
    }
    manifest_path = project_path(config, "data", "real", "download_manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return manifest


def _metric_dict(results) -> dict[str, dict[str, Any]]:
    return {name: result.metrics for name, result in results.items()}


def _read_metric_sidecar(path: Path, campaigns_path: Path | None = None) -> dict[str, dict[str, Any]]:
    frame = pd.read_csv(path)
    metrics = {str(row["run"]): row.drop(labels=["run"]).to_dict() for _, row in frame.iterrows()}
    if campaigns_path is None or not campaigns_path.exists():
        return metrics
    campaigns = pd.read_csv(campaigns_path)
    for name, group in campaigns.groupby("run"):
        selected = metrics.setdefault(str(name), {})
        selected["worst_mae_r"] = float(group["mae_r"].min()) if len(group) else 0.0
        selected["best_mfe_r"] = float(group["mfe_r"].max()) if len(group) else 0.0
        performance = {}
        for regime in ("range", "warning", "breakout", "failed_breakout"):
            rows = group[group["regime"] == regime]
            performance[regime] = {
                "trades": len(rows),
                "pnl_usd": float(rows["pnl_usd"].sum()),
                "win_rate": float((rows["pnl_usd"] > 0).mean()) if len(rows) else None,
                "expectancy_usd": float(rows["pnl_usd"].mean()) if len(rows) else None,
            }
        selected["performance_by_regime"] = performance
    return metrics


def _oos_baselines(
    data: dict[str, pd.DataFrame],
    prepared: dict[str, pd.DataFrame],
    config: dict,
    first_test: pd.Timestamp,
    oos_metrics: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    sliced = {symbol: frame.loc[first_test:] for symbol, frame in data.items()}
    result = {}
    for spec in strategy_specs(config):
        relationship = prepared[spec.run_name].loc[first_test:]
        if not {"price_a", "z"}.issubset(relationship.columns):
            relationship = None
        metrics = oos_metrics.get(spec.run_name, {})
        result[spec.run_name] = compute_baselines(
            sliced,
            primary_symbol=spec.primary,
            secondary_symbol=spec.secondary,
            relationship=relationship,
            strategy_return=metrics.get("total_return"),
            has_trades=bool(metrics.get("number_of_trades")),
        )
    return result


def _write_result_sidecars(prefix: Path, results: dict) -> None:
    fills, decisions, campaigns, equities, exposures = [], [], [], [], []
    for name, result in results.items():
        fills.extend({"run": name, **fill.to_dict()} for fill in result.fills)
        decisions.extend({"run": name, **decision.to_dict()} for decision in result.decisions)
        campaigns.extend({"run": name, **campaign} for campaign in result.campaigns)
        equities.append(result.equity_curve.rename(name))
        if result.exposure_curve is not None:
            frame = result.exposure_curve.copy()
            frame.columns = pd.MultiIndex.from_product([[name], frame.columns])
            exposures.append(frame)
    pd.DataFrame(fills).to_csv(prefix.with_name(prefix.name + "_fills.csv"), index=False)
    pd.DataFrame(decisions).to_csv(prefix.with_name(prefix.name + "_decisions.csv"), index=False)
    pd.DataFrame(campaigns).to_csv(prefix.with_name(prefix.name + "_campaigns.csv"), index=False)
    if equities:
        pd.concat(equities, axis=1).to_csv(prefix.with_name(prefix.name + "_equity.csv"), index_label="timestamp")
    if exposures:
        pd.concat(exposures, axis=1).to_csv(prefix.with_name(prefix.name + "_exposure.csv"), index_label="timestamp")


def run_phase2a(
    config: dict,
    *,
    run_intraday: bool = True,
    run_sensitivity: bool = True,
) -> Path:
    output_dir = project_path(config, "outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    daily = load_real_data(config)
    events = load_events(config)
    diagnostics = relationship_diagnostics(daily, config, include_blind=False)
    daily_results, full_baselines, prepared = run_strategy_set(daily, config, events)
    full_metrics = _metric_dict(daily_results)
    first_test = max(frame.index.min() for frame in daily.values()) + pd.DateOffset(
        months=int(config["walk_forward"]["train_months"])
    )
    oos_results, _, oos_prepared = run_strategy_set(
        daily, config, events, trade_start=first_test
    )
    oos_metrics, monthly, first_test = walk_forward_oos(
        oos_results,
        train_months=int(config["walk_forward"]["train_months"]),
        test_months=int(config["walk_forward"]["test_months"]),
    )
    oos_baselines = _oos_baselines(daily, oos_prepared, config, first_test, oos_metrics)
    targets = select_sensitivity_targets(strategy_specs(config), oos_metrics)
    sensitivity = (
        run_oat_sensitivity(daily, config, events, targets, first_test)
        if run_sensitivity else pd.DataFrame()
    )
    robustness = robustness_by_run(sensitivity)
    gates = {
        name: acceptance_gate(metrics, config, robustness.get(name))
        for name, metrics in oos_metrics.items()
    }
    intraday_results = {}
    intraday_metrics: dict[str, dict[str, Any]] = {}
    if run_intraday:
        intraday = load_real_data(config, intraday=True)
        intraday_results, _, _ = run_strategy_set(intraday, config, events)
        intraday_metrics = _metric_dict(intraday_results)
        intraday_start = str(min(frame.index.min() for frame in intraday.values()))
        intraday_end = str(max(frame.index.max() for frame in intraday.values()))
    else:
        intraday_start = intraday_end = "not run"

    metrics_frame(full_metrics).to_csv(output_dir / "real_data_full_period_metrics.csv", index=False)
    metrics_frame(oos_metrics).to_csv(output_dir / "real_data_oos_metrics.csv", index=False)
    metrics_frame(intraday_metrics).to_csv(output_dir / "real_data_intraday_metrics.csv", index=False)
    monthly.to_csv(output_dir / "real_data_walk_forward_monthly.csv", index=False)
    sensitivity.to_csv(output_dir / "real_data_sensitivity.csv", index=False)
    (output_dir / "real_data_acceptance_gates.json").write_text(
        json.dumps({name: {"passed": value[0], "failed": value[1]} for name, value in gates.items()}, indent=2),
        encoding="utf-8",
    )
    (output_dir / "real_data_baselines.json").write_text(
        json.dumps({"full_period": full_baselines, "oos": oos_baselines}, indent=2, default=str),
        encoding="utf-8",
    )
    _write_result_sidecars(output_dir / "real_data_daily", daily_results)
    _write_result_sidecars(output_dir / "real_data_oos", oos_results)
    if intraday_results:
        _write_result_sidecars(output_dir / "real_data_intraday", intraday_results)

    event_frame = pd.read_csv(project_path(config, config["data"]["event_path"]))
    daily_start = str(min(frame.index.min() for frame in daily.values()))
    daily_end = str(max(frame.index.max() for frame in daily.values()))
    return write_real_data_report(
        output_dir / "real_data_research_report.md",
        daily_start=daily_start,
        daily_end=daily_end,
        intraday_start=intraday_start,
        intraday_end=intraday_end,
        event_count=len(event_frame),
        full_metrics=full_metrics,
        oos_metrics=oos_metrics,
        intraday_metrics=intraday_metrics,
        full_baselines=full_baselines,
        oos_baselines=oos_baselines,
        monthly=monthly,
        sensitivity=sensitivity,
        gates=gates,
        sensitivity_targets=[spec.run_name for spec in targets],
        first_test=first_test,
        diagnostics=diagnostics,
    )


def refresh_phase2a_report(config: dict) -> Path:
    """Rebuild only the Markdown report from completed Phase 2A sidecars."""
    output_dir = project_path(config, "outputs")
    daily = load_real_data(config)
    intraday = load_real_data(config, intraday=True)
    full_metrics = _read_metric_sidecar(
        output_dir / "real_data_full_period_metrics.csv",
        output_dir / "real_data_daily_campaigns.csv",
    )
    oos_metrics = _read_metric_sidecar(
        output_dir / "real_data_oos_metrics.csv",
        output_dir / "real_data_oos_campaigns.csv",
    )
    intraday_metrics = _read_metric_sidecar(output_dir / "real_data_intraday_metrics.csv")
    monthly = pd.read_csv(output_dir / "real_data_walk_forward_monthly.csv")
    sensitivity = pd.read_csv(output_dir / "real_data_sensitivity.csv")
    gates_raw = json.loads((output_dir / "real_data_acceptance_gates.json").read_text(encoding="utf-8"))
    gates = {name: (bool(value["passed"]), list(value["failed"])) for name, value in gates_raw.items()}
    baselines = json.loads((output_dir / "real_data_baselines.json").read_text(encoding="utf-8"))
    diagnostics = relationship_diagnostics(daily, config, include_blind=False)
    first_test = max(frame.index.min() for frame in daily.values()) + pd.DateOffset(
        months=int(config["walk_forward"]["train_months"])
    )
    event_frame = pd.read_csv(project_path(config, config["data"]["event_path"]))
    return write_real_data_report(
        output_dir / "real_data_research_report.md",
        daily_start=str(min(frame.index.min() for frame in daily.values())),
        daily_end=str(max(frame.index.max() for frame in daily.values())),
        intraday_start=str(min(frame.index.min() for frame in intraday.values())),
        intraday_end=str(max(frame.index.max() for frame in intraday.values())),
        event_count=len(event_frame),
        full_metrics=full_metrics,
        oos_metrics=oos_metrics,
        intraday_metrics=intraday_metrics,
        full_baselines=baselines["full_period"],
        oos_baselines=baselines["oos"],
        monthly=monthly,
        sensitivity=sensitivity,
        gates=gates,
        sensitivity_targets=sensitivity["run"].drop_duplicates().tolist(),
        first_test=first_test,
        diagnostics=diagnostics,
    )
