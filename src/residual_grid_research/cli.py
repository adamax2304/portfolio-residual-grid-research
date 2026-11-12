from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from residual_grid_research.config import load_config, project_path
from residual_grid_research.backtest import BacktestEngine, run_sensitivity, run_walk_forward
from residual_grid_research.data import AlphaVantageClient, EventCalendar, make_synthetic_universe
from residual_grid_research.data.alpha_vantage import quality_report
from residual_grid_research.data.events import normalize_provider_events
from residual_grid_research.research import all_configured_symbols, relationship_diagnostics, run_full_research
from residual_grid_research.strategies import NaturalLongGridStrategy, ResidualGridStrategy, StockPairGridStrategy
from residual_grid_research.phase2a import fetch_phase2a_data, refresh_phase2a_report, run_phase2a
from residual_grid_research.phase2b import fetch_phase2b_data, refresh_phase2b_reports, run_phase2b
from residual_grid_research.phase2c import run_phase2c


def _default_config() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "default.yaml"


def _client(config: dict) -> AlphaVantageClient:
    return AlphaVantageClient(
        api_key_env=config["data"]["api_key_env"],
        cache_dir=project_path(config, config["data"]["cache_dir"]),
        requests_per_minute=int(config["data"]["requests_per_minute"]),
    )


def _load_cached(config: dict, symbols: list[str]) -> dict[str, pd.DataFrame]:
    cache = project_path(config, config["data"]["cache_dir"])
    result = {}
    for symbol in symbols:
        path = cache / f"{symbol}_daily_adjusted.csv"
        if path.exists():
            result[symbol] = pd.read_csv(path, index_col="timestamp", parse_dates=True).sort_index()
    missing = sorted(set(symbols) - set(result))
    if missing:
        raise FileNotFoundError(f"Missing cached daily data for: {', '.join(missing)}. Run `residual-grid fetch-daily`.")
    return result


def _load_cached_intraday(
    config: dict, symbols: list[str], start: str, end: str
) -> dict[str, pd.DataFrame]:
    cache = project_path(config, config["data"]["cache_dir"])
    interval = config["data"]["intraday_interval"]
    periods = pd.period_range(pd.Timestamp(start), pd.Timestamp(end), freq="M")
    result = {}
    missing = []
    for symbol in symbols:
        frames = []
        for period in periods:
            path = cache / f"{symbol}_{interval}_{period}_adjusted_rth.csv"
            if not path.exists():
                missing.append(str(path))
                continue
            frames.append(pd.read_csv(path, index_col="timestamp", parse_dates=True))
        if frames:
            combined = pd.concat(frames).sort_index()
            start_at, end_at = pd.Timestamp(start), pd.Timestamp(end)
            if combined.index.tz is not None:
                if start_at.tzinfo is None:
                    start_at = start_at.tz_localize(combined.index.tz)
                if end_at.tzinfo is None:
                    end_at = end_at.tz_localize(combined.index.tz) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
            result[symbol] = combined.loc[start_at:end_at]
    if missing:
        preview = "\n".join(missing[:10])
        raise FileNotFoundError(f"Missing {len(missing)} intraday cache file(s). Run fetch-intraday first.\n{preview}")
    return result


def _strategy(mode: str, symbols: list[str], config: dict):
    if mode == "residual" and len(symbols) == 2:
        return ResidualGridStrategy(config, symbols[0], symbols[1])
    if mode == "pair" and len(symbols) == 2:
        return StockPairGridStrategy(config, symbols[0], symbols[1])
    if mode == "natural" and len(symbols) == 1:
        return NaturalLongGridStrategy(config, symbols[0])
    expected = "two" if mode in {"residual", "pair"} else "one"
    raise ValueError(f"{mode} mode requires {expected} symbol(s)")


def command_fetch_daily(args: argparse.Namespace, config: dict) -> int:
    symbols = args.symbols or all_configured_symbols(config)
    client = _client(config)
    frames = client.fetch_universe_daily(symbols, years=int(config["data"]["daily_years"]), force=args.force)
    reports = {symbol: asdict(quality_report(symbol, frame)) for symbol, frame in frames.items()}
    print(json.dumps(reports, indent=2, default=str))
    return 0


def command_fetch_intraday(args: argparse.Namespace, config: dict) -> int:
    client = _client(config)
    frames = {}
    for symbol in args.symbols:
        frames[symbol] = client.fetch_intraday_range(
            symbol, args.start, args.end, interval=config["data"]["intraday_interval"], force=args.force
        )
    reports = {symbol: asdict(quality_report(symbol, frame, intraday=True)) for symbol, frame in frames.items()}
    print(json.dumps(reports, indent=2, default=str))
    return 0


def command_fetch_events(args: argparse.Namespace, config: dict) -> int:
    client = _client(config)
    normalized = []
    mapping = {"EARNINGS_CALENDAR": "EARNINGS", "DIVIDENDS": "DIVIDEND", "SPLITS": "SPLIT"}
    for symbol in args.symbols:
        for function, event_type in mapping.items():
            frame = client.fetch_events(function, symbol, force=args.force)
            if not frame.empty:
                normalized.append(normalize_provider_events(symbol, frame, event_type))
    result = pd.concat(normalized, ignore_index=True) if normalized else pd.DataFrame(
        columns=["symbol", "date", "event_type", "severity", "description"]
    )
    output = Path(args.output) if args.output else project_path(config, "data", "processed", "provider_events.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output, index=False)
    print(output.resolve())
    return 0


def command_diagnose(args: argparse.Namespace, config: dict) -> int:
    symbols = all_configured_symbols(config)
    data = make_synthetic_universe(symbols, seed=int(config["project"]["seed"])) if args.synthetic else _load_cached(config, symbols)
    diagnostics = relationship_diagnostics(data, config)
    output = Path(args.output) if args.output else project_path(config, "outputs", "diagnostics.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(diagnostics, indent=2, default=str), encoding="utf-8")
    print(output.resolve())
    return 0


def command_research(args: argparse.Namespace, config: dict) -> int:
    symbols = all_configured_symbols(config)
    if args.synthetic:
        data = make_synthetic_universe(symbols, seed=int(config["project"]["seed"]))
        source = "deterministic synthetic fixture (pipeline validation only; not evidence of edge)"
    elif getattr(args, "intraday", False):
        if not args.start or not args.end:
            raise ValueError("--intraday requires --start and --end")
        data = _load_cached_intraday(config, symbols, args.start, args.end)
        source = "cached Alpha Vantage adjusted 5-minute regular-session bars"
    else:
        data = _load_cached(config, symbols)
        source = "cached Alpha Vantage total-return adjusted daily bars"
    events = EventCalendar(pd.read_csv(args.events)) if args.events else EventCalendar()
    coverage = f"Imported historical event calendar: {Path(args.events).resolve()}" if args.events else "No historical event file supplied; event-filtered claims are provisional."
    output = Path(args.output) if args.output else project_path(config, "outputs", "research_report.md")
    report = run_full_research(data, config, output_path=output, data_source=source, events=events, event_coverage=coverage)
    print(report.resolve())
    return 0


def _experiment_data(args: argparse.Namespace, config: dict) -> dict[str, pd.DataFrame]:
    symbols = list(dict.fromkeys([*args.symbols, "SPY"]))
    if args.synthetic:
        return make_synthetic_universe(symbols, seed=int(config["project"]["seed"]))
    return _load_cached(config, symbols)


def command_walk_forward(args: argparse.Namespace, config: dict) -> int:
    data = _experiment_data(args, config)
    output = run_walk_forward(
        data,
        strategy_factory=lambda: _strategy(args.mode, args.symbols, config),
        engine_factory=lambda: BacktestEngine(config),
        train_months=args.train_months,
        test_months=args.test_months,
    )
    target = Path(args.output) if args.output else project_path(config, "outputs", f"walk_forward_{args.mode}.csv")
    target.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(target, index=False)
    print(target.resolve())
    return 0


def command_sensitivity(args: argparse.Namespace, config: dict) -> int:
    data = _experiment_data(args, config)

    def runner(candidate_config: dict):
        result = BacktestEngine(candidate_config).run(_strategy(args.mode, args.symbols, candidate_config), data)
        return {
            "total_return": result.metrics.get("total_return"),
            "max_drawdown": result.metrics.get("max_drawdown"),
            "sharpe": result.metrics.get("sharpe"),
            "fill_count": result.metrics.get("fill_count"),
            "cost_drag_usd": result.metrics.get("cost_drag_usd"),
        }

    output = run_sensitivity(config, {args.path: args.values}, runner)
    target = Path(args.output) if args.output else project_path(config, "outputs", f"sensitivity_{args.mode}.csv")
    target.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(target, index=False)
    print(target.resolve())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Residual grid and breakout research system (no live trading)")
    parser.add_argument("--config", default=str(_default_config()), help="YAML configuration path")
    sub = parser.add_subparsers(dest="command", required=True)
    daily = sub.add_parser("fetch-daily", help="Download/cache adjusted daily bars")
    daily.add_argument("symbols", nargs="*")
    daily.add_argument("--force", action="store_true")
    intraday = sub.add_parser("fetch-intraday", help="Download/cache adjusted regular-session intraday bars")
    intraday.add_argument("symbols", nargs="+", help="Ticker symbols")
    intraday.add_argument("--start", required=True)
    intraday.add_argument("--end", required=True)
    intraday.add_argument("--force", action="store_true")
    events = sub.add_parser("fetch-events", help="Download current provider earnings/dividend/split events")
    events.add_argument("symbols", nargs="+", help="Ticker symbols")
    events.add_argument("--force", action="store_true")
    events.add_argument("--output")
    diagnose = sub.add_parser("diagnose", help="Run Phase 1a relationship diagnostics")
    diagnose.add_argument("--synthetic", action="store_true")
    diagnose.add_argument("--output")
    research = sub.add_parser("research", help="Run all configured strategy backtests and Markdown report")
    research.add_argument("--synthetic", action="store_true")
    research.add_argument("--events", help="Historical event CSV: symbol,date,event_type[,severity,description]")
    research.add_argument("--intraday", action="store_true", help="Use cached month-sliced intraday data")
    research.add_argument("--start")
    research.add_argument("--end")
    research.add_argument("--output")
    demo = sub.add_parser("demo", help="Offline deterministic end-to-end validation")
    demo.add_argument("--output")
    walk = sub.add_parser("walk-forward", help="Run rolling train/test windows for one strategy")
    walk.add_argument("--mode", required=True, choices=["residual", "pair", "natural"])
    walk.add_argument("symbols", nargs="+")
    walk.add_argument("--train-months", type=int, default=6)
    walk.add_argument("--test-months", type=int, default=1)
    walk.add_argument("--synthetic", action="store_true")
    walk.add_argument("--output")
    sensitivity = sub.add_parser("sensitivity", help="Vary one dotted config path over explicit values")
    sensitivity.add_argument("--mode", required=True, choices=["residual", "pair", "natural"])
    sensitivity.add_argument("symbols", nargs="+")
    sensitivity.add_argument("--path", required=True, help="Example: strategy.residual.entry_z")
    sensitivity.add_argument("--values", nargs="+", type=float, required=True)
    sensitivity.add_argument("--synthetic", action="store_true")
    sensitivity.add_argument("--output")
    phase2fetch = sub.add_parser("phase2a-fetch", help="Cache the controlled real daily/intraday universe and historical events")
    phase2fetch.add_argument("--force", action="store_true")
    phase2run = sub.add_parser("phase2a-run", help="Run the complete real-data validation and acceptance report")
    phase2run.add_argument("--skip-intraday", action="store_true")
    phase2run.add_argument("--skip-sensitivity", action="store_true")
    sub.add_parser("phase2a-report", help="Rebuild the real-data Markdown report from completed sidecars")
    phase2bfetch = sub.add_parser("phase2b-fetch", help="Cache the controlled extended daily universe and events")
    phase2bfetch.add_argument("--force", action="store_true")
    sub.add_parser("phase2b-run", help="Run Phase 2B edge triage, expansion, attribution, and reports")
    phase2breport = sub.add_parser("phase2b-report", help="Rebuild Phase 2B reports from completed sidecars")
    phase2breport.add_argument("--rerun-local-sensitivity", action="store_true")
    phase2c = sub.add_parser("phase2c-audit", help="Run the backtest integrity and mechanics audit")
    phase2c.add_argument("--force-data", action="store_true", help="Refresh Phase 2C raw/adjusted dual-price caches")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    if args.command == "fetch-daily":
        return command_fetch_daily(args, config)
    if args.command == "fetch-intraday":
        return command_fetch_intraday(args, config)
    if args.command == "fetch-events":
        return command_fetch_events(args, config)
    if args.command == "diagnose":
        return command_diagnose(args, config)
    if args.command == "demo":
        args.synthetic = True
        args.events = None
        return command_research(args, config)
    if args.command == "research":
        return command_research(args, config)
    if args.command == "walk-forward":
        return command_walk_forward(args, config)
    if args.command == "sensitivity":
        return command_sensitivity(args, config)
    if args.command == "phase2a-fetch":
        manifest = fetch_phase2a_data(config, force=args.force)
        print(json.dumps({"daily_symbols": len(manifest["daily"]), "intraday_symbols": len(manifest["intraday"]), "events": manifest["events"], "event_warnings": manifest["event_warnings"]}, indent=2))
        return 0
    if args.command == "phase2a-run":
        report = run_phase2a(config, run_intraday=not args.skip_intraday, run_sensitivity=not args.skip_sensitivity)
        print(report.resolve())
        return 0
    if args.command == "phase2a-report":
        print(refresh_phase2a_report(config).resolve())
        return 0
    if args.command == "phase2b-fetch":
        manifest = fetch_phase2b_data(config, force=args.force)
        print(json.dumps({"daily_symbols": len(manifest["daily"]), "events": manifest["events"], "event_warnings": manifest["event_warnings"]}, indent=2))
        return 0
    if args.command == "phase2b-run":
        edge, deep = run_phase2b(config)
        print(json.dumps({"edge_triage_report": str(edge.resolve()), "candidate_deep_dive": str(deep.resolve())}, indent=2))
        return 0
    if args.command == "phase2b-report":
        edge, deep = refresh_phase2b_reports(config, rerun_local_sensitivity=args.rerun_local_sensitivity)
        print(json.dumps({"edge_triage_report": str(edge.resolve()), "candidate_deep_dive": str(deep.resolve())}, indent=2))
        return 0
    if args.command == "phase2c-audit":
        print(run_phase2c(config, force_data=args.force_data).resolve())
        return 0
    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
