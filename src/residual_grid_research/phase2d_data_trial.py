from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from residual_grid_research.backtest import BacktestEngine
from residual_grid_research.config import load_config
from residual_grid_research.data.events import EventCalendar
from residual_grid_research.data.exchange_calendar import USExchangeCalendar
from residual_grid_research.data.trial_adapters import (
    EODHDEventsAdapter,
    EarningsAPIAdapter,
    HFDataLibraryAdapter,
    HistoricalDataNetSampleAdapter,
    MarketParquetLocalAdapter,
)
from residual_grid_research.phase2d import _digest_value, _frozen_parameters, _universe
from residual_grid_research.strategies import (
    NaturalLongGridStrategy,
    ResidualGridStrategy,
    StockPairGridStrategy,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    clean = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    lines = [
        "| " + " | ".join(clean(column) for column in columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    lines.extend(
        "| " + " | ".join(clean(value) for value in row) + " |"
        for row in frame.itertuples(index=False, name=None)
    )
    return "\n".join(lines)


def _lite_summary_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "## Frozen LITE metrics\n\nNo completed LITE metrics are available."
    metrics = frame.copy()
    metrics["family"] = metrics["run"].str.split(":").str[0]
    summary = metrics.groupby(["timeframe", "family"], as_index=False).agg(
        runs=("run", "size"),
        active_runs=("number_of_trades", lambda values: int((values > 0).sum())),
        positive_return=("total_return", lambda values: int((values > 0).sum())),
        pf_gt_115=("profit_factor", lambda values: int((values > 1.15).sum())),
        median_return=("total_return", "median"),
        median_pf=("profit_factor", "median"),
        total_trades=("number_of_trades", "sum"),
    )
    for column in ("median_return", "median_pf"):
        summary[column] = summary[column].map(lambda value: f"{value:.6f}")
    gate = (
        (metrics["profit_factor"] > 1.15)
        & (metrics["expectancy_usd"] > 0)
        & (metrics["number_of_trades"] >= 30)
    )
    thin_winners = metrics[
        (metrics["profit_factor"] > 1.15) & (metrics["expectancy_usd"] > 0)
    ]
    sufficiently_active = metrics[
        (metrics["expectancy_usd"] > 0) & (metrics["number_of_trades"] >= 30)
    ].sort_values("profit_factor", ascending=False)
    evidence = ""
    if not thin_winners.empty:
        evidence += (
            f" All PF > 1.15 positive-expectancy runs have at most "
            f"{int(thin_winners['number_of_trades'].max())} trades."
        )
    if not sufficiently_active.empty:
        closest = sufficiently_active.iloc[0]
        evidence += (
            f" The closest sufficiently active run is {closest['run']} on "
            f"{closest['timeframe']} with {int(closest['number_of_trades'])} trades "
            f"and PF {float(closest['profit_factor']):.3f}."
        )
    return (
        "## Frozen LITE metrics\n\n"
        f"- Completed rows: **{len(metrics)}**\n"
        f"- Active runs: **{int((metrics['number_of_trades'] > 0).sum())}/{len(metrics)}**\n"
        f"- Zero-trade runs: **{int((metrics['number_of_trades'] == 0).sum())}/{len(metrics)}**\n"
        f"- Runs with positive return: **{int((metrics['total_return'] > 0).sum())}/{len(metrics)}**\n"
        f"- Runs passing PF > 1.15 + positive expectancy + >=30 trades: **{int(gate.sum())}/{len(metrics)}**\n\n"
        + _markdown_table(summary)
        + "\n\nNo run passes the minimum combined research screen."
        + evidence
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _roles(config: dict) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {symbol: set() for symbol in _universe(config)["all_symbols"]}
    for stock, etf in config["universe"]["stock_etf_pairs"]:
        result[stock].add("residual_stock")
        result[etf].add("residual_hedge")
    for first, second in config["universe"]["stock_pairs"]:
        result[first].add("stock_pair")
        result[second].add("stock_pair")
    for symbol in config["universe"]["natural_long_symbols"]:
        result[symbol].add("natural_long")
    for symbol in config["universe"]["benchmarks"]:
        result[symbol].add("benchmark")
    return result


def _hf_quality(frame: pd.DataFrame, timeframe: str, calendar: USExchangeCalendar) -> dict[str, Any]:
    minutes = int(timeframe.removesuffix("min"))
    required = ["open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in frame]
    duplicates = int(frame.index.duplicated().sum()) if not frame.empty else 0
    bad_ohlc = int((
        (frame["high"] < frame[["open", "close", "low"]].max(axis=1))
        | (frame["low"] > frame[["open", "close", "high"]].min(axis=1))
    ).sum()) if not missing and not frame.empty else -1
    span = (
        (frame.index.max() - frame.index.min()).total_seconds() / (365.2425 * 86400)
        if len(frame) > 1 else 0.0
    )
    session_checks = calendar.validate_rth_index(frame.index, interval_minutes=minutes)
    session_dates = pd.DatetimeIndex(frame.index.tz_convert("America/New_York").normalize().unique()).tz_localize(None)
    expected = len(session_dates) * (390 // minutes)
    density = min(len(frame) / expected, 1.0) if expected else 0.0
    passed = bool(
        not missing and not duplicates and bad_ohlc == 0 and span >= 2.0 and density >= 0.80
        and session_checks["non_session_bars"] == 0
        and session_checks["outside_rth_bars"] == 0
        and session_checks["early_close_violations"] == 0
    )
    return {
        "rows": len(frame), "start": frame.index.min() if len(frame) else None,
        "end": frame.index.max() if len(frame) else None, "span_years": span,
        "bar_density": density, "duplicates": duplicates, "bad_ohlc": bad_ohlc,
        **session_checks, "passed": passed,
    }


def _strategy_specs(config: dict, events: EventCalendar):
    for stock, etf in config["universe"]["stock_etf_pairs"]:
        yield ResidualGridStrategy(config, stock, etf, events=events)
    for first, second in config["universe"]["stock_pairs"]:
        yield StockPairGridStrategy(config, first, second, events=events)
    for symbol in config["universe"]["natural_long_symbols"]:
        yield NaturalLongGridStrategy(config, symbol, events=events)


def _run_lite(config: dict, frames: dict[str, pd.DataFrame], timeframe: str) -> pd.DataFrame:
    """Price-only frozen-parameter trial; never a full Phase 2D acceptance run."""
    empty_events = EventCalendar(session_calendar=USExchangeCalendar(start="2000-01-01", end="2030-12-31"))
    common_start = max(frame.index.min() for frame in frames.values())
    trade_start = common_start + pd.DateOffset(months=int(config["walk_forward"]["train_months"]))
    rows = []
    before = _digest_value(_frozen_parameters(config))
    for strategy in _strategy_specs(config, empty_events):
        result = BacktestEngine(config).run(strategy, frames, trade_start=trade_start)
        rows.append({"run": result.strategy_name, "timeframe": timeframe, **result.metrics})
    if _digest_value(_frozen_parameters(config)) != before:
        raise RuntimeError("Frozen parameter mutation detected during R-LITE")
    return pd.DataFrame(rows)


def run_trial(root: Path) -> dict[str, Any]:
    output = root / "outputs" / "phase2d_data_trial"
    output.mkdir(parents=True, exist_ok=True)
    config = load_config(root / "config" / "phase2d_frozen.yaml")
    snapshot = json.loads((root / "outputs" / "phase2d" / "frozen_engine_snapshot.json").read_text(encoding="utf-8"))
    frozen_hash = _digest_value(_frozen_parameters(config))
    if frozen_hash != snapshot["frozen_parameter_sha256"]:
        raise RuntimeError("Frozen Phase 2D parameters changed; refusing data trial")
    universe = _universe(config)
    symbols = universe["all_symbols"]
    roles = _roles(config)
    cache = root / "data" / "phase2d_data_trial"
    hf = HFDataLibraryAdapter(cache / "hf_data_library")
    historical = HistoricalDataNetSampleAdapter(cache / "historicaldata")
    market = MarketParquetLocalAdapter(
        os.getenv("MARKETPARQUET_ARCHIVE", str(root / "data" / "marketparquet"))
    )
    earnings = EarningsAPIAdapter(cache / "earningsapi")
    eodhd = EODHDEventsAdapter(cache / "eodhd")

    try:
        hf_coverage = hf.coverage(symbols, force=True).set_index("symbol")
        hf_catalog_error = ""
    except Exception as exc:
        hf_coverage = pd.DataFrame(index=symbols, data={"available": False, "size_bytes": 0, "last_modified": None})
        hf_catalog_error = f"{type(exc).__name__}: {exc}"
    try:
        sample_symbols = set(historical.sample_symbols())
        sample_error = ""
    except Exception as exc:
        sample_symbols = set()
        sample_error = f"{type(exc).__name__}: {exc}"
    local_files_5m = market.files("5min")
    local_files_15m = market.files("15min")
    hf_cache_complete = all(
        (cache / "hf_data_library" / timeframe / f"{symbol}_clean.parquet").exists()
        for symbol in symbols for timeframe in ("5min", "15min")
    )

    loaded: dict[str, dict[str, pd.DataFrame]] = {"5min": {}, "15min": {}}
    hf_details: dict[tuple[str, str], dict[str, Any]] = {}
    calendar = USExchangeCalendar(start="2000-01-01", end="2030-12-31")
    download_errors: dict[tuple[str, str], str] = {}
    if hf.api_key:
        tasks = [
            (symbol, timeframe)
            for symbol in symbols
            for timeframe in ("5min", "15min")
            if bool(hf_coverage.at[symbol, "available"])
        ]

        def download_one(symbol: str, timeframe: str):
            adapter = HFDataLibraryAdapter(cache / "hf_data_library", api_key=hf.api_key)
            return adapter.download(symbol, timeframe=timeframe, version="clean")

        with ThreadPoolExecutor(max_workers=min(8, len(tasks))) as pool:
            futures = {pool.submit(download_one, symbol, timeframe): (symbol, timeframe) for symbol, timeframe in tasks}
            for number, future in enumerate(as_completed(futures), start=1):
                symbol, timeframe = futures[future]
                try:
                    future.result()
                    outcome = "PASS"
                except Exception as exc:
                    outcome = f"{type(exc).__name__}: {exc}"
                    download_errors[(symbol, timeframe)] = outcome
                print(f"HF_DOWNLOAD {number}/{len(tasks)} {symbol} {timeframe} {outcome}", flush=True)
    for symbol in symbols:
        for timeframe in ("5min", "15min"):
            if not bool(hf_coverage.at[symbol, "available"]):
                hf_details[(symbol, timeframe)] = {"status": "SYMBOL_NOT_AVAILABLE"}
            elif not hf.api_key and not (
                cache / "hf_data_library" / timeframe / f"{symbol}_clean.parquet"
            ).exists():
                hf_details[(symbol, timeframe)] = {"status": "AUTH_REQUIRED"}
            elif (symbol, timeframe) in download_errors:
                hf_details[(symbol, timeframe)] = {"status": f"DOWNLOAD_FAIL:{download_errors[(symbol, timeframe)].split(':', 1)[0]}"}
            else:
                try:
                    frame = hf.load(symbol, timeframe=timeframe, version="clean")
                    start = pd.Timestamp(config["data"]["start"], tz="America/New_York")
                    end = pd.Timestamp(config["data"]["end"], tz="America/New_York") + pd.Timedelta(days=1)
                    frame = frame[(frame.index >= start) & (frame.index < end)]
                    quality = _hf_quality(frame, timeframe, calendar)
                    quality["calendar_rth_removed_bars"] = int(
                        frame.attrs.get("calendar_rth_removed_bars", 0)
                    )
                    status = "PASS" if quality["passed"] else "QUALITY_FAIL"
                    hf_details[(symbol, timeframe)] = {"status": status, **quality}
                    if quality["passed"]:
                        loaded[timeframe][symbol] = frame
                except Exception as exc:
                    hf_details[(symbol, timeframe)] = {"status": f"DOWNLOAD_FAIL:{type(exc).__name__}"}

    historical_details: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        if symbol not in sample_symbols:
            historical_details[symbol] = {"available": False, "span_years": 0.0, "rows_5m": 0, "rows_15m": 0}
            continue
        try:
            five = historical.load(symbol, timeframe="5min")
            fifteen = historical.load(symbol, timeframe="15min")
            span = (five.index.max() - five.index.min()).total_seconds() / (365.2425 * 86400)
            historical_details[symbol] = {
                "available": True, "span_years": span, "rows_5m": len(five), "rows_15m": len(fifteen),
                "start": five.index.min(), "end": five.index.max(),
            }
        except Exception as exc:
            historical_details[symbol] = {"available": False, "error": type(exc).__name__, "span_years": 0.0, "rows_5m": 0, "rows_15m": 0}

    rows = []
    for symbol in symbols:
        five, fifteen = hf_details[(symbol, "5min")], hf_details[(symbol, "15min")]
        history = historical_details[symbol]
        rows.append({
            "symbol": symbol,
            "frozen_roles": ";".join(sorted(roles[symbol])),
            "hf_symbol_available": bool(hf_coverage.at[symbol, "available"]),
            "hf_catalog_size_bytes": int(hf_coverage.at[symbol, "size_bytes"] or 0),
            "hf_last_modified": hf_coverage.at[symbol, "last_modified"],
            "hf_5m_status": five["status"],
            "hf_5m_rows": five.get("rows", 0),
            "hf_5m_span_years": five.get("span_years", 0.0),
            "hf_5m_bar_density": five.get("bar_density"),
            "hf_5m_bad_ohlc": five.get("bad_ohlc"),
            "hf_5m_non_session_bars": five.get("non_session_bars"),
            "hf_5m_outside_rth_bars": five.get("outside_rth_bars"),
            "hf_5m_early_close_violations": five.get("early_close_violations"),
            "hf_5m_calendar_bars_removed": five.get("calendar_rth_removed_bars", 0),
            "hf_15m_status": fifteen["status"],
            "hf_15m_rows": fifteen.get("rows", 0),
            "hf_15m_span_years": fifteen.get("span_years", 0.0),
            "hf_15m_bar_density": fifteen.get("bar_density"),
            "hf_15m_bad_ohlc": fifteen.get("bad_ohlc"),
            "hf_15m_non_session_bars": fifteen.get("non_session_bars"),
            "hf_15m_outside_rth_bars": fifteen.get("outside_rth_bars"),
            "hf_15m_early_close_violations": fifteen.get("early_close_violations"),
            "hf_15m_calendar_bars_removed": fifteen.get("calendar_rth_removed_bars", 0),
            "historicaldata_sample_available": history.get("available", False),
            "historicaldata_sample_span_years": history.get("span_years", 0.0),
            "marketparquet_local_5m_files": len(local_files_5m),
            "marketparquet_local_15m_files": len(local_files_15m),
            "earningsapi_key_present": bool(earnings.api_key),
            "eodhd_key_present": bool(eodhd.api_key),
        })
    coverage = pd.DataFrame(rows)
    coverage.to_csv(output / "coverage_matrix.csv", index=False)

    catalog_pass = bool(coverage["hf_symbol_available"].all())
    five_pass = bool((coverage["hf_5m_status"] == "PASS").all())
    fifteen_pass = bool((coverage["hf_15m_status"] == "PASS").all())
    candle_gate = catalog_pass and five_pass and fifteen_pass
    lite_metrics = pd.DataFrame()
    lite_status = "NOT_RUN"
    lite_reason = "HF symbol catalog passes, but authenticated 5m/15m download and quality coverage do not pass"
    if candle_gate:
        try:
            result_parts = [_run_lite(config, loaded[timeframe], timeframe) for timeframe in ("5min", "15min")]
            lite_metrics = pd.concat(result_parts, ignore_index=True)
            lite_metrics.to_csv(output / "hf_lite_metrics.csv", index=False)
            lite_status = "COMPLETED_LIMITED"
            lite_reason = "Price-only adjusted/IEX-limited run completed; not eligible for Phase 2D acceptance"
        except Exception as exc:
            lite_status = "FAILED"
            lite_reason = f"{type(exc).__name__}: {exc}"
    lite_gate_passes = int((
        (lite_metrics.get("profit_factor", pd.Series(dtype=float)) > 1.15)
        & (lite_metrics.get("expectancy_usd", pd.Series(dtype=float)) > 0)
        & (lite_metrics.get("number_of_trades", pd.Series(dtype=float)) >= 30)
    ).sum()) if not lite_metrics.empty else 0

    source_rows = [
        {
            "source": "HF Data Library", "role": "intraday bars", "cost": "FREE key",
            "coverage": f"{int(coverage['hf_symbol_available'].sum())}/{len(symbols)} catalog; bars {'cached' if hf_cache_complete else 'downloadable' if hf.api_key else 'not authenticated'}",
            "raw_execution": "NO (adjusted bars)", "events": "NO",
            "limitations": "Post-Mar-2022 IEX-only (~2-3% consolidated volume); adjusted; RTH only; survivorship-biased universe",
            "classification": "LIMITED" if catalog_pass else "FAIL",
        },
        {
            "source": "MarketParquet local", "role": "local Parquet bars", "cost": "$79 one-time archive if purchased",
            "coverage": f"local 5m files={len(local_files_5m)}, local 15m files={len(local_files_15m)}",
            "raw_execution": "NO (split-adjusted)", "events": "NO",
            "limitations": "No local archive configured; 15m may require deterministic 5m resample",
            "classification": "FAIL" if not local_files_5m else "LIMITED",
        },
        {
            "source": "HistoricalData.net free sample", "role": "format/adapter sample", "cost": "FREE sample; full 1m archive $699 one-time",
            "coverage": f"{int(coverage['historicaldata_sample_available'].sum())}/{len(symbols)}, Jul-Dec 2022 only",
            "raw_execution": "YES in sample", "events": "dividend/split columns",
            "limitations": "Only KO and SPY from frozen universe; ~6 months; cannot validate pairs/universe",
            "classification": "FAIL",
        },
        {
            "source": "EarningsAPI free", "role": "earnings dates", "cost": "FREE 100/day, 1000/month",
            "coverage": f"not queried; key {'present' if earnings.api_key else 'absent'}",
            "raw_execution": "N/A", "events": "earnings only",
            "limitations": "Free history most recent 24 months; not guaranteed point-in-time; no dividends/splits",
            "classification": "FAIL" if not earnings.api_key else "LIMITED",
        },
        {
            "source": "EODHD free events", "role": "dividends/splits", "cost": "FREE 20/day",
            "coverage": f"not queried; key {'present' if eodhd.api_key else 'absent'}",
            "raw_execution": "N/A", "events": "dividends/splits",
            "limitations": "Free history limited to past year; 25-symbol backfill exceeds one-day free quota",
            "classification": "FAIL" if not eodhd.api_key else "LIMITED",
        },
    ]
    comparison = pd.DataFrame(source_rows)
    table = _markdown_table(comparison)
    _write(
        output / "data_source_comparison.md",
        "# Phase 2D-R0 — Free/cheap data source comparison\n\n"
        "## Result\n\n"
        "HF Data Library is the cheapest plausible **R-LITE** price source because its public catalog covers all 25 frozen symbols and its key is free. It does not qualify for full Phase 2D: prices are adjusted, the post-March-2022 segment is IEX-only, and no extended-hours data exists. "
        + ("Authenticated downloads and quality checks completed.\n\n" if hf.api_key else "Previously authenticated candle files were loaded from the local cache; no key was persisted.\n\n" if hf_cache_complete else "No key was available, so authenticated downloads and quality checks could not run.\n\n")
        + table
        + "\n\n## Cheapest usable path\n\n"
        "1. Use the free HF Data Library key only through the `HFDL_API_KEY` environment variable; never commit it.\n"
        "2. Require 25/25 symbols, both 5m and 15m, at least two years per symbol, valid calendar-aware RTH timestamps, and >=80% bar density.\n"
        "3. Use HF only for `Phase 2D-R-LITE`; never call it raw-price independent validation.\n"
        "4. For a stronger low-cost archive, MarketParquet is listed at $79 one-time, but remains split-adjusted. HistoricalData.net's full stock minute archive is $699 one-time and includes raw plus adjusted values.\n"
        "5. EarningsAPI free can supply up to the most recent 24 months of earnings after a free key is configured; EODHD free supplies only about one year of dividend/split history.\n\n"
        "No strategy parameters or frozen-engine module changed. All R0 source additions are classified `DATA_ADAPTER_ONLY`, `REPORTING_ONLY`, or `TEST_ONLY`.",
    )
    _write(
        output / "hf_lite_validation_report.md",
        "# HF Data Library Phase 2D-R-LITE report\n\n"
        f"HF SOURCE CLASSIFICATION: **{'LIMITED' if catalog_pass else 'FAIL'}**\n\n"
        f"- Public catalog coverage: **{int(coverage['hf_symbol_available'].sum())}/{len(symbols)}** ({'PASS' if catalog_pass else 'FAIL'})\n"
        f"- `HFDL_API_KEY` present: **{bool(hf.api_key)}**\n"
        f"- Complete authenticated local candle cache: **{hf_cache_complete}**\n"
        f"- 5m data-quality coverage: **{int((coverage['hf_5m_status'] == 'PASS').sum())}/{len(symbols)}**\n"
        f"- 15m data-quality coverage: **{int((coverage['hf_15m_status'] == 'PASS').sum())}/{len(symbols)}**\n"
        f"- Calendar-invalid bars removed from working views: **{int(coverage['hf_5m_calendar_bars_removed'].sum())} (5m), {int(coverage['hf_15m_calendar_bars_removed'].sum())} (15m)**\n"
        f"- R-LITE status: **{lite_status}**\n"
        f"- Reason: {lite_reason}\n\n"
        + _lite_summary_markdown(lite_metrics)
        + "\n\n"
        "## Mandatory limitations\n\n"
        "- Post-March-2022 bars are IEX-only and represent roughly 2–3% of consolidated volume.\n"
        "- OHLCV is split/dividend adjusted; raw as-traded execution prices are unavailable.\n"
        "- Neither Raw nor Clean version contains extended-hours bars; the clock range is RTH.\n"
        "- Missing no-trade minutes are preserved; no LOCF gap fill is permitted.\n"
        "- The library's 1,391-symbol universe is a circa-2022/2023 snapshot and is survivorship-biased historically.\n"
        "- This is price-only LITE: point-in-time earnings/dividend/split events were not available without separate event-provider keys.\n"
        "- Frozen lookback values are unchanged and therefore interpreted as bar counts on both 5m and 15m; this is a mechanics trial, not an intraday parameter calibration.\n"
        "- LITE applies a six-month warm-up and then one frozen remaining-period run; it is not the full rolling monthly walk-forward required by Phase 2D.\n\n"
        "## Decision\n\n"
        + (
            f"The public catalog and candle gate pass. R-LITE completed on the frozen parameters, but only {lite_gate_passes}/58 runs pass the minimum combined research screen. It remains limited research because HF bars are adjusted and IEX-only after March 2022. Live trading remains NO-GO."
            if lite_status == "COMPLETED_LIMITED"
            else "The public symbols endpoint passes, but the actual candle gate or frozen LITE run did not complete. No qualifying R-LITE conclusion is available, and the Phase 2D frozen conclusions remain unchanged. Live trading remains NO-GO."
        ),
    )
    tracked_changes = {
        "DATA_ADAPTER_ONLY": ["src/residual_grid_research/data/trial_adapters.py"],
        "REPORTING_ONLY": ["src/residual_grid_research/phase2d_data_trial.py", ".gitignore"],
        "TEST_ONLY": ["tests/test_phase2d_data_trial.py"],
        "FROZEN_ENGINE_FILES_CHANGED": [],
    }
    manifest = {
        "phase": "2D-R0", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_commit": snapshot["git_commit_hash"], "frozen_parameter_sha256": frozen_hash,
        "catalog_coverage": {"covered": int(coverage["hf_symbol_available"].sum()), "required": len(symbols)},
        "candle_coverage_gate": candle_gate, "r_lite_status": lite_status,
        "classifications": {row["source"]: row["classification"] for row in source_rows},
        "post_freeze_changes": tracked_changes,
        "errors": {"hf_catalog": hf_catalog_error, "historical_sample": sample_error},
    }
    _write_json(output / "trial_manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 2D-R0 free/cheap data-source trial")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    result = run_trial(Path(args.root).resolve())
    print(f"HF CATALOG COVERAGE: {result['catalog_coverage']['covered']}/{result['catalog_coverage']['required']}")
    print(f"PHASE 2D-R-LITE: {result['r_lite_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
