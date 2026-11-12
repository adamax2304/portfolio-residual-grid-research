from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from residual_grid_research.backtest import BacktestEngine, compute_baselines
from residual_grid_research.data import EventCalendar
from residual_grid_research.features import mean_reversion_diagnostics, rolling_relationship
from residual_grid_research.reports import write_research_report
from residual_grid_research.strategies import NaturalLongGridStrategy, ResidualGridStrategy, StockPairGridStrategy


def all_configured_symbols(config: dict) -> list[str]:
    universe = config["universe"]
    symbols = set(universe.get("benchmarks", []))
    for stock, etfs in universe["stock_etf_map"].items():
        symbols.add(stock)
        symbols.update(etfs)
    for pair in universe["stock_pairs"] + universe.get("blind_expansion_pairs", []):
        symbols.update(pair)
    symbols.update(universe.get("natural_long_symbols", []))
    return sorted(symbols)


def relationship_diagnostics(
    data: dict[str, pd.DataFrame], config: dict, *, include_blind: bool = True
) -> dict[str, dict[str, Any]]:
    feature = config["features"]
    output: dict[str, dict[str, Any]] = {}
    for stock, etfs in config["universe"]["stock_etf_map"].items():
        for etf in etfs:
            if stock not in data or etf not in data:
                continue
            relation = rolling_relationship(
                data[stock], data[etf], beta_window=int(feature["beta_window"]),
                z_window=int(feature["z_window"]), correlation_windows=feature["correlation_windows"],
            )
            output[f"{stock}/{etf}"] = mean_reversion_diagnostics(relation, entry_z=1.4, kill_z=2.8)
    pairs = list(config["universe"]["stock_pairs"])
    if include_blind:
        pairs += list(config["universe"].get("blind_expansion_pairs", []))
    for a, b in pairs:
        if a not in data or b not in data:
            continue
        relation = rolling_relationship(
            data[a], data[b], beta_window=int(feature["beta_window"]),
            z_window=int(feature["z_window"]), correlation_windows=feature["correlation_windows"],
        )
        output[f"{a}/{b}"] = mean_reversion_diagnostics(relation, entry_z=1.4, kill_z=3.0)
    return output


def selection_bias_summary(
    diagnostics: dict[str, dict[str, Any]],
    config: dict,
    results: list | None = None,
    baselines: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    curated = {f"{a}/{b}" for a, b in config["universe"]["stock_pairs"]}
    curated.update(f"{stock}/{etf}" for stock, etfs in config["universe"]["stock_etf_map"].items() for etf in etfs)
    blind = {f"{a}/{b}" for a, b in config["universe"].get("blind_expansion_pairs", [])}
    curated_items = [value for key, value in diagnostics.items() if key in curated]
    blind_items = [value for key, value in diagnostics.items() if key in blind]
    curated_go = sum(str(value.get("go_no_go", "")).startswith("GO") for value in curated_items)
    blind_go = sum(str(value.get("go_no_go", "")).startswith("GO") for value in blind_items)
    results = results or []
    baselines = baselines or {}
    curated_result_names = {f"stock_pair_grid:{value}" for value in curated}
    curated_result_names.update(f"residual_grid:{value}" for value in curated)
    blind_result_names = {f"stock_pair_grid:{value}" for value in blind}
    curated_results = [result for result in results if result.strategy_name in curated_result_names]
    blind_results = [result for result in results if result.strategy_name in blind_result_names]

    def average_return(items):
        return sum(float(item.metrics.get("total_return", 0)) for item in items) / len(items) if items else None

    def edge_rate(items):
        return sum(bool(baselines.get(item.strategy_name, {}).get("edge_found")) for item in items) / len(items) if items else None

    return {
        "curated_count": len(curated_items),
        "curated_go": curated_go,
        "curated_go_rate": curated_go / len(curated_items) if curated_items else None,
        "blind_count": len(blind_items),
        "blind_go": blind_go,
        "blind_go_rate": blind_go / len(blind_items) if blind_items else None,
        "curated_backtests": len(curated_results),
        "curated_average_return": average_return(curated_results),
        "curated_edge_rate": edge_rate(curated_results),
        "blind_backtests": len(blind_results),
        "blind_average_return": average_return(blind_results),
        "blind_edge_rate": edge_rate(blind_results),
    }


def run_all_backtests(
    data: dict[str, pd.DataFrame], config: dict, events: EventCalendar | None = None
):
    events = events or EventCalendar()
    candidates = []
    for stock, etfs in config["universe"]["stock_etf_map"].items():
        candidates.extend(ResidualGridStrategy(config, stock, etf, events=events) for etf in etfs)
    pair_values = config["universe"]["stock_pairs"] + config["universe"].get("blind_expansion_pairs", [])
    candidates.extend(StockPairGridStrategy(config, a, b, events=events) for a, b in pair_values)
    candidates.extend(NaturalLongGridStrategy(config, symbol, events=events) for symbol in config["universe"]["natural_long_symbols"])
    results = []
    baselines = {}
    for strategy in candidates:
        missing = [symbol for symbol in strategy.required_symbols if symbol not in data and symbol != "SPY"]
        if missing:
            continue
        result = BacktestEngine(config).run(strategy, data)
        results.append(result)
        relationship = strategy.prepared if {"price_a", "z"}.issubset(strategy.prepared.columns) else None
        secondary = getattr(strategy, "etf", None) or getattr(strategy, "asset_b", None)
        base = compute_baselines(
            data,
            primary_symbol=strategy.symbol,
            secondary_symbol=secondary,
            relationship=relationship,
            strategy_return=result.metrics.get("total_return"),
            has_trades=bool(result.metrics.get("fill_count")),
        )
        baselines[result.strategy_name] = base
    return results, baselines


# Backwards-friendly alias for notebooks created during the initial scaffold.
run_representative_backtests = run_all_backtests


def run_full_research(
    data: dict[str, pd.DataFrame],
    config: dict,
    *,
    output_path: str | Path,
    data_source: str,
    events: EventCalendar | None = None,
    event_coverage: str = "No historical event file supplied; event-filtered claims are provisional.",
) -> Path:
    diagnostics = relationship_diagnostics(data, config)
    results, baselines = run_all_backtests(data, config, events)
    report_path = write_research_report(
        output_path,
        diagnostics=diagnostics,
        results=results,
        baselines=baselines,
        selection_bias=selection_bias_summary(diagnostics, config, results, baselines),
        data_source=data_source,
        event_coverage=event_coverage,
        config_path=config["_config_path"],
    )
    stem = report_path.with_suffix("")
    fill_rows = []
    decision_rows = []
    equity_series = []
    for result in results:
        fill_rows.extend({"run": result.strategy_name, **fill.to_dict()} for fill in result.fills)
        decision_rows.extend({"run": result.strategy_name, **decision.to_dict()} for decision in result.decisions)
        equity_series.append(result.equity_curve.rename(result.strategy_name))
    pd.DataFrame(fill_rows).to_csv(f"{stem}_trades.csv", index=False)
    pd.DataFrame(decision_rows).to_csv(f"{stem}_decisions.csv", index=False)
    if equity_series:
        pd.concat(equity_series, axis=1).to_csv(f"{stem}_equity.csv", index_label="timestamp")
    pd.DataFrame.from_dict(diagnostics, orient="index").to_json(
        f"{stem}_diagnostics.json", orient="index", indent=2, default_handler=str
    )
    return report_path
