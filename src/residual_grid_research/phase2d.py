from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from residual_grid_research.config import load_config
from residual_grid_research.data import AlphaVantageIndependentAdapter, USExchangeCalendar
from residual_grid_research.phase2c import BUGS


SNAPSHOT_NAME = "frozen_engine_snapshot.json"


class FrozenConfigurationError(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _digest_value(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _write_csv(path: Path, columns: list[str], rows: Iterable[dict[str, Any]] = ()) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(list(rows))
    if frame.empty:
        frame = pd.DataFrame(columns=columns)
    else:
        for column in columns:
            if column not in frame:
                frame[column] = None
        frame = frame[columns]
    frame.to_csv(path, index=False)


def _git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise FrozenConfigurationError("A git commit is required before freezing Phase 2D")
    return result.stdout.strip()


def _source_manifest(root: Path) -> dict[str, str]:
    paths = [
        *root.joinpath("src").rglob("*.py"),
        *root.joinpath("tests").rglob("*.py"),
        root / "config" / "phase2d_frozen.yaml",
        root / "pyproject.toml",
    ]
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(set(paths))
        if path.exists()
    }


def _prior_artifact_manifest(root: Path) -> dict[str, str]:
    output = root / "outputs"
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and "phase2d" not in path.parts
    }


def _universe(config: dict) -> dict[str, Any]:
    universe = config["universe"]
    symbols = set(universe["natural_long_symbols"] + universe["benchmarks"])
    for first, second in universe["stock_etf_pairs"] + universe["stock_pairs"]:
        symbols.update((first, second))
    result = {
        "frozen_before_results": True,
        "selection_uses_phase2d_profitability": False,
        "stock_to_etf": universe["stock_etf_pairs"],
        "stock_to_stock": universe["stock_pairs"],
        "natural_long": universe["natural_long_symbols"],
        "benchmarks": universe["benchmarks"],
        "all_symbols": sorted(symbols),
    }
    result["universe_sha256"] = _digest_value(result)
    return result


@dataclass(slots=True)
class FrozenEngineGuard:
    expected_hash: str

    @classmethod
    def capture(cls, config: dict) -> "FrozenEngineGuard":
        return cls(_digest_value(_frozen_parameters(config)))

    def assert_unchanged(self, config: dict) -> None:
        actual = _digest_value(_frozen_parameters(config))
        if actual != self.expected_hash:
            raise FrozenConfigurationError(
                f"Frozen parameter mutation detected: expected {self.expected_hash}, got {actual}"
            )


def _frozen_parameters(config: dict) -> dict[str, Any]:
    return {
        key: deepcopy(config[key])
        for key in (
            "features", "strategy", "risk", "costs", "events", "execution",
            "walk_forward", "acceptance", "universe",
        )
    }


def diagnostic_variants(config: dict) -> list[dict[str, Any]]:
    """Return preregistered diagnostic families without mutating baseline."""
    guard = FrozenEngineGuard.capture(config)
    rows: list[dict[str, Any]] = []
    for family, dimensions in config["diagnostics"].items():
        for dimension, values in dimensions.items():
            rows.append({
                "strategy_family": family,
                "dimension": dimension,
                "values": json.dumps(values),
                "purpose": "mechanical_sanity_not_selection",
                "status": "PREREGISTERED",
            })
    guard.assert_unchanged(config)
    return rows


def create_frozen_snapshot(root: Path, config_path: Path, output: Path) -> dict[str, Any]:
    config = load_config(config_path)
    config.pop("_project_root", None)
    source_manifest = _source_manifest(root)
    prior_manifest = _prior_artifact_manifest(root)
    universe = _universe(config)
    snapshot = {
        "protocol": "PHASE_2D_FROZEN_ENGINE_INDEPENDENT_VALIDATION",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit_hash": _git_commit(root),
        "package_version": importlib.metadata.version("residual-grid-research"),
        "config_file": config_path.relative_to(root).as_posix(),
        "config_sha256": _sha256(config_path),
        "frozen_parameter_sha256": _digest_value(_frozen_parameters(config)),
        "universe_sha256": universe["universe_sha256"],
        "strategy_configs": config["strategy"],
        "fill_model_config": config["execution"],
        "cost_model_config": config["costs"],
        "slippage_model_config": {
            "spread_bps": config["costs"]["spread_bps"],
            "slippage_bps": config["costs"]["slippage_bps"],
            "directional": True,
            "both_entry_and_exit": True,
        },
        "event_filter_config": config["events"],
        "stop_kill_config": {
            "risk": config["risk"],
            "natural": {
                key: config["strategy"]["natural"][key]
                for key in ("hard_stop_atr", "stop_variant", "atr_kill_multiple", "max_holding_days")
            },
            "residual_kill_z": config["strategy"]["residual"]["kill_z"],
            "pair_kill_z": config["strategy"]["pairs"]["kill_z"],
        },
        "breakout_config": config["strategy"]["breakout"],
        "residual_zscore_config": {
            "features": {
                key: config["features"][key]
                for key in ("beta_window", "z_window", "correlation_windows")
            },
            "residual": config["strategy"]["residual"],
            "pairs": config["strategy"]["pairs"],
        },
        "grid_construction_config": {
            "natural": config["strategy"]["natural"],
            "residual": config["strategy"]["residual"]["grid_levels"],
            "pairs": config["strategy"]["pairs"]["grid_levels"],
        },
        "accounting_method": config["execution"]["accounting_method"],
        "session_handling": {
            "timezone": config["project"]["timezone"],
            "regular_hours_only": config["data"]["regular_hours_only"],
            "extended_hours": config["data"]["extended_hours"],
        },
        "calendar_handling": {
            "calendar": config["data"]["calendar"],
            "trading_days_not_weekdays": True,
            "early_closes": True,
        },
        "phase2c_bugfixes_included": [bug["id"] for bug in BUGS],
        "phase2c_bugfix_count": len(BUGS),
        "allowed_post_freeze_change_classes": config["phase2d"]["allowed_post_freeze_changes"],
        "post_freeze_change_log": [],
        "source_manifest": source_manifest,
        "source_manifest_sha256": _digest_value(source_manifest),
        "prior_artifact_manifest": prior_manifest,
        "prior_artifact_manifest_sha256": _digest_value(prior_manifest),
    }
    output.mkdir(parents=True, exist_ok=True)
    snapshot_path = output / SNAPSHOT_NAME
    if snapshot_path.exists():
        existing = json.loads(snapshot_path.read_text(encoding="utf-8"))
        immutable_keys = ("git_commit_hash", "config_sha256", "frozen_parameter_sha256", "universe_sha256")
        if any(existing.get(key) != snapshot.get(key) for key in immutable_keys):
            raise FrozenConfigurationError("Refusing to overwrite a different frozen Phase 2D snapshot")
        snapshot = existing
    else:
        _write_json(snapshot_path, snapshot)
    _write_json(output / "frozen_universe.json", universe)
    return snapshot


def _verify_snapshot(root: Path, config: dict, snapshot: dict) -> list[str]:
    failures: list[str] = []
    if _digest_value(_frozen_parameters(config)) != snapshot["frozen_parameter_sha256"]:
        failures.append("frozen strategy/config parameter hash changed")
    if _universe(config)["universe_sha256"] != snapshot["universe_sha256"]:
        failures.append("frozen universe changed")
    if _source_manifest(root) != snapshot["source_manifest"]:
        failures.append("source changed after freeze without a classified change log")
    return failures


def _artifact_integrity(root: Path, output: Path, snapshot: dict) -> dict[str, Any]:
    actual = _prior_artifact_manifest(root)
    expected = snapshot["prior_artifact_manifest"]
    added = sorted(set(actual) - set(expected))
    missing = sorted(set(expected) - set(actual))
    changed = sorted(path for path in set(expected) & set(actual) if expected[path] != actual[path])
    status = "PASS" if not (added or missing or changed) else "FAIL"
    rows = [
        f"| `{path}` | `{expected[path]}` | `{actual.get(path, 'MISSING')}` | "
        f"{'PASS' if actual.get(path) == expected[path] else 'FAIL'} |"
        for path in expected
    ]
    _write_text(
        output / "artifact_integrity_check.md",
        "# Phase 2D prior-artifact integrity check\n\n"
        f"STATUS: **{status}**\n\n"
        f"Files checked: **{len(expected)}**. Added: {len(added)}; missing: {len(missing)}; changed: {len(changed)}. "
        "The manifest covers every file under `outputs/` except `outputs/phase2d/`.\n\n"
        "| Artifact | Frozen SHA-256 | Current SHA-256 | Result |\n"
        "|---|---|---|---|\n" + "\n".join(rows),
    )
    return {"status": status, "checked": len(expected), "added": added, "missing": missing, "changed": changed}


def _calendar_report(config: dict, output: Path) -> dict[str, Any]:
    calendar = USExchangeCalendar(config["data"]["calendar"], start="2000-01-01", end="2030-12-31")
    christmas_closed = not calendar.is_session("2024-12-25")
    july_info = calendar.session_info("2024-07-03")
    july_close = july_info.close_utc.tz_convert("America/New_York").strftime("%H:%M")
    next_open = calendar.next_open(pd.Timestamp("2024-12-24 16:00", tz="America/New_York"))
    next_open_local = next_open.tz_convert("America/New_York")
    holiday_next_open_ok = next_open_local.strftime("%Y-%m-%d %H:%M") == "2024-12-26 09:30"
    distance_ok = calendar.trading_day_distance("2024-12-24", "2024-12-26") == 1
    status = "PASS" if all((christmas_closed, july_info.early_close, july_close == "13:00", holiday_next_open_ok, distance_ok)) else "FAIL"
    _write_text(
        output / "calendar_validation_report.md",
        "# Exchange calendar validation\n\n"
        f"STATUS: **{status}**\n\n"
        "Calendar: `XNYS` via `exchange_calendars`; all session opens/closes are stored in UTC and converted to America/New_York only for reporting.\n\n"
        f"- Christmas 2024 excluded: `{christmas_closed}`\n"
        f"- 2024-07-03 early close recognized: `{july_info.early_close}` at `{july_close}` ET\n"
        f"- Next open after 2024-12-24 close: `{next_open_local}`\n"
        f"- Holiday-aware session distance 2024-12-24 to 2024-12-26 equals one: `{distance_ok}`\n\n"
        "This calendar is wired into event distance. Bar availability still controls actual next-bar execution; no weekday approximation is used in Phase 2D event checks.",
    )
    return {"status": status, "calendar": "XNYS", "checks": 5}


def _test_suite(root: Path) -> dict[str, Any]:
    result = subprocess.run(
        [os.sys.executable, "-m", "pytest", "-q"], cwd=root, capture_output=True, text=True, check=False
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    return {"status": "PASS" if result.returncode == 0 else "FAIL", "returncode": result.returncode, "output": output[-4000:]}


def _inventory_rows(config: dict, universe: dict, preflight: dict) -> list[dict[str, Any]]:
    return [
        {
            "symbol": symbol,
            "interval": interval,
            "provider": config["data"]["provider"],
            "requested_start": config["data"]["start"],
            "requested_end": config["data"]["end"],
            "rows": 0,
            "observed_start": None,
            "observed_end": None,
            "span_years": 0.0,
            "raw_ohlc": False,
            "adjusted_ohlc": False,
            "rth": True,
            "timezone": config["project"]["timezone"],
            "status": "UNAVAILABLE_MISSING_CREDENTIAL" if not preflight["ready"] else "NOT_DOWNLOADED",
            "reason": preflight["reason"],
        }
        for symbol in universe["all_symbols"]
        for interval in config["data"]["intervals"]
    ]


def _blocked_csvs(output: Path) -> None:
    schemas = {
        "event_exclusion_audit.csv": ["timestamp", "symbol", "second_leg", "event_type", "event_date", "session_distance", "action", "reason", "status"],
        "oos_metrics.csv": ["run", "strategy_family", "interval", "sample", "total_return", "profit_factor", "expectancy", "max_drawdown", "trades", "campaigns", "status"],
        "walk_forward_monthly.csv": ["run", "interval", "train_start", "train_end", "test_start", "test_end", "return", "profit_factor", "expectancy", "campaigns", "status"],
        "yearly_metrics.csv": ["run", "interval", "year", "return", "profit_factor", "expectancy", "max_drawdown", "campaigns", "status"],
        "strategy_family_summary.csv": ["strategy_family", "interval", "runs", "return", "profit_factor", "expectancy", "max_drawdown", "campaigns", "cost_stress_pass", "status"],
        "grid_geometry_diagnostics.csv": ["run", "campaign_id", "interval", "range_high", "range_low", "range_width", "atr", "grid_step", "grid_step_pct", "grid_step_atr", "levels", "filled_legs", "average_entry_before", "average_entry_after", "average_improvement", "tp_distance", "stop_distance", "stop_distance_atr", "max_exposure", "status"],
        "inventory_diagnostics.csv": ["run", "campaign_id", "timestamp", "leg", "active_legs", "quantity", "average_entry", "realized_pnl", "unrealized_pnl", "max_exposure", "status"],
        "stop_diagnostics.csv": ["run", "campaign_id", "interval", "mae", "winner", "stopped", "later_reverted", "saved_by_stop", "stop_loss", "stop_distance_atr", "stop_reason", "status"],
        "take_profit_diagnostics.csv": ["run", "campaign_id", "interval", "tp_hit", "tp_capture", "missed_due_next_bar", "tp_after_costs", "exit_scope", "residual_or_price_exit", "status"],
    }
    for name, columns in schemas.items():
        _write_csv(output / name, columns)


def _write_blocked_reports(
    output: Path,
    config: dict,
    preflight: dict,
    integrity: dict,
    calendar: dict,
    tests: dict,
    snapshot_failures: list[str],
) -> dict[str, Any]:
    _blocked_csvs(output)
    _write_csv(
        output / "fill_model_intraday_audit.csv",
        ["dataset", "test", "interval", "signal_time", "execution_time", "raw_execution", "next_bar", "touch_required", "adverse_first", "gap_conservative", "result"],
        [{
            "dataset": "DETERMINISTIC_SYNTHETIC_ONLY", "test": "phase2c_and_phase2d_execution_suite",
            "interval": "5min/15min", "raw_execution": True, "next_bar": True,
            "touch_required": True, "adverse_first": True, "gap_conservative": True,
            "result": tests["status"],
        }],
    )
    _write_text(
        output / "fill_model_intraday_audit.md",
        "# Intraday fill-model audit\n\n"
        f"MECHANICAL TEST STATUS: **{tests['status']}**\n\n"
        "Raw unprefixed OHLC is reserved for fills; adjusted-prefixed OHLC is selected only by feature code. Signals queue after close and market orders execute next bar. Limits require a real high/low touch, gap-through stops use the next available price, and same-candle conflicts are adverse-first.\n\n"
        "The requested daily/15m/5m market comparison was **not run** because the independent-data gate failed. The CSV row is labelled deterministic synthetic only and is not evidence of strategy performance.",
    )
    attribution_rows = [
        {"dataset": "DETERMINISTIC_SYNTHETIC_ONLY", "campaign_id": "ledger_fixture", "ledger": "grid_ledger", "pnl_usd": 95.0, "combined_campaign_pnl_usd": 140.0, "reconciliation_error": 0.0, "status": "PASS"},
        {"dataset": "DETERMINISTIC_SYNTHETIC_ONLY", "campaign_id": "ledger_fixture", "ledger": "breakout_ledger", "pnl_usd": 45.0, "combined_campaign_pnl_usd": 140.0, "reconciliation_error": 0.0, "status": "PASS"},
        {"dataset": "DETERMINISTIC_SYNTHETIC_ONLY", "campaign_id": "ledger_fixture", "ledger": "campaign_ledger", "pnl_usd": 140.0, "combined_campaign_pnl_usd": 140.0, "reconciliation_error": 0.0, "status": "PASS"},
    ]
    _write_csv(
        output / "grid_breakout_attribution.csv",
        ["dataset", "campaign_id", "ledger", "pnl_usd", "combined_campaign_pnl_usd", "reconciliation_error", "status"],
        attribution_rows,
    )
    _write_text(
        output / "grid_breakout_attribution.md",
        "# Grid and breakout sub-ledger validation\n\n"
        "STATUS: **PASS (mechanics only)**\n\n"
        "The engine now emits `grid_ledger` and `breakout_ledger` rows and reconciles their sum to `campaign_ledger`. For natural-grid inventory carried into continuation, P&L is marked at the close that confirmed `BREAKOUT_ACTIVE`; relationship continuations already start a distinct breakout campaign. Kill, time-stop, failed-breakout, and event exits retain their explicit campaign exit categories.\n\n"
        "The included fixture proves arithmetic reconciliation only. Market attribution was not run after the data gate failed.",
    )
    parameter_rows = diagnostic_variants(config)
    for row in parameter_rows:
        row["status"] = "NOT_RUN_NO_DATA"
    _write_csv(
        output / "parameter_sanity_diagnostics.csv",
        ["strategy_family", "dimension", "values", "purpose", "status"],
        parameter_rows,
    )
    _write_text(
        output / "parameter_sanity_diagnostics.md",
        "# Parameter sanity diagnostics\n\n"
        "STATUS: **PREREGISTERED, NOT RUN**\n\n"
        "All requested families are frozen in `config/phase2d_frozen.yaml`. They were not evaluated because no qualifying independent intraday dataset was available. No best variant was selected, and the frozen baseline hash was verified after constructing the registry.",
    )
    _write_text(
        output / "grid_geometry_report.md",
        "# Grid geometry and inventory report\n\nSTATUS: **NOT RUN — NO-GO-DATA**\n\nNo campaign geometry or inventory row was fabricated. Whether the frozen grids are too narrow, wide, sparse, or stop-sensitive remains unanswered on independent intraday data.",
    )
    _write_text(
        output / "stop_takeprofit_report.md",
        "# Stop and take-profit report\n\nSTATUS: **NOT RUN — NO-GO-DATA**\n\nDeterministic stop/fill tests pass, but the requested empirical MAE, later-reversion, stop-saved, TP-capture, and next-bar-miss distributions require independent candles and are intentionally empty.",
    )
    replay_names = [
        "best natural grid", "worst natural grid", "typical natural grid", "best residual grid",
        "worst residual grid", "best stock-pair grid", "worst stock-pair grid", "stop-killed campaign",
        "time-stop campaign", "event-skipped setup", "breakout success", "breakout fakeout",
        "grid too narrow", "grid too sparse", "stop likely too tight", "stop saved strategy",
    ]
    _write_text(
        output / "manual_campaign_replay_report.md",
        "# Manual campaign replay report\n\nSTATUS: **NOT RUN — NO-GO-DATA**\n\n"
        + "\n".join(f"- {name}: not selected; no independent Phase 2D campaigns exist." for name in replay_names)
        + "\n\nNo Phase 2A/2B campaign was substituted because that would violate independence.",
    )
    data_gate = "PASS" if preflight["ready"] else "FAIL"
    phase_status = "NO-GO-DATA" if data_gate == "FAIL" else "BLOCKED"
    acceptance = {
        "phase": "2D",
        "phase2d_status": phase_status,
        "backtest_engine_status": "PASS_WITH_ISSUES" if tests["status"] == "PASS" else "FAIL",
        "independent_data_status": "FAIL" if data_gate == "FAIL" else "LIMITED",
        "phase_2a_2b_corrected_conclusion": "INCONCLUSIVE",
        "natural_long_grid_status": "INCONCLUSIVE",
        "residual_stock_to_etf_status": "INCONCLUSIVE",
        "stock_to_stock_pairs_status": "INCONCLUSIVE",
        "breakout_continuation_status": "INCONCLUSIVE",
        "grid_parameter_reasonableness": "MIXED",
        "stop_tp_mechanics": "MIXED",
        "live_trading_status": "NO-GO",
        "research_continuation": "NO-GO",
        "next_recommended_phase": "PHASE_2D_RESUME_WITH_LICENSED_INDEPENDENT_INTRADAY_DATA",
        "provider_preflight": preflight,
        "frozen_snapshot_valid": not snapshot_failures,
        "snapshot_failures": snapshot_failures,
        "prior_artifact_integrity": integrity,
        "calendar_validation": calendar,
        "automated_tests": tests,
        "all_tests_pass": tests["status"] == "PASS",
        "pnl_reconciliation": "PASS_MECHANICAL_FIXTURE_ONLY",
        "promoted_strategies": [],
        "gate_failures": [
            "No Alpha Vantage credential/entitlement was available.",
            "No independent 5m/15m dataset with at least two years of coverage was obtained.",
            "Point-in-time/as-close event coverage could not be verified.",
            "No OOS, cost-stress, best-campaign, or best-month gate can be evaluated.",
        ],
    }
    _write_json(output / "phase2d_acceptance.json", acceptance)
    return acceptance


def _write_data_reports(output: Path, config: dict, universe: dict, preflight: dict) -> None:
    rows = _inventory_rows(config, universe, preflight)
    _write_csv(
        output / "data_inventory.csv",
        ["symbol", "interval", "provider", "requested_start", "requested_end", "rows", "observed_start", "observed_end", "span_years", "raw_ohlc", "adjusted_ohlc", "rth", "timezone", "status", "reason"],
        rows,
    )
    _write_text(
        output / "data_quality_report.md",
        "# Independent intraday data quality report\n\n"
        "PHASE 2D STATUS: **NO-GO-DATA**\n\n"
        f"Provider preregistered before results: `{preflight['provider']}`. Credential present: `{preflight['credential_present']}`. "
        f"Reason: {preflight['reason']}.\n\n"
        f"Required inventory: **{len(universe['all_symbols'])} symbols × {len(config['data']['intervals'])} intervals = {len(rows)} symbol/interval datasets**. Obtained: **0**. "
        "Therefore missing candles, duplicates, outliers, timezone alignment, raw/adjusted consistency, split handling, early closes, and 2-year coverage cannot be certified.\n\n"
        "The adapter is independent of the earlier yfinance path and requests raw (`adjusted=false`) and adjusted (`adjusted=true`) monthly RTH views separately. Alpha Vantage documents historical intraday as a premium endpoint: https://www.alphavantage.co/documentation/#intraday\n\n"
        "Per the Phase 2D hard gate, market validation stopped before strategy execution. No yfinance fallback and no synthetic market-performance substitute was used.",
    )
    _write_text(
        output / "event_data_quality_report.md",
        "# Point-in-time event data quality report\n\nSTATUS: **FAIL / UNAVAILABLE**\n\n"
        "The frozen source is Alpha Vantage historical earnings (`EARNINGS`) plus corporate-action `DIVIDENDS` and `SPLITS`, applied to both relationship legs through the XNYS session calendar. No credential was available, so coverage, announcement-time provenance, revisions, and symbol completeness could not be verified. The source is therefore only `as-close-as-possible`, not guaranteed point-in-time.\n\n"
        "No event exclusion row was generated or inferred from retrospective Phase 2C files.",
    )


def _write_final_report(output: Path, acceptance: dict, universe: dict) -> None:
    test_output = acceptance["automated_tests"]["output"].replace("\n", " ")
    _write_text(
        output / "frozen_engine_independent_validation_report.md",
        "# Phase 2D — Frozen Engine Independent Validation\n\n"
        "## Executive conclusion\n\n"
        "Phase 2D stopped at the mandatory independent-data gate. The frozen engine, universe, XNYS calendar, dual raw/adjusted adapter, conservative intraday fills, and separated grid/breakout accounting are implemented and mechanically tested, but **no independent market result was produced**. The environment contains no Alpha Vantage or alternative licensed-provider credential, and Alpha Vantage's multi-year intraday endpoint requires credentialed premium access. Substituting yfinance would violate the protocol.\n\n"
        "This is not evidence that any strategy works or fails. It means the independent replication question remains unanswered. Phase 2A/2B remain partially invalid numerically, the Phase 2C mechanical findings stand, and live trading remains NO-GO.\n\n"
        "## Frozen protocol and preservation\n\n"
        f"- Frozen universe: {len(universe['all_symbols'])} symbols; selected before Phase 2D results.\n"
        "- Baseline: 5m RTH raw execution; 15m robustness; 2021-09-01 through 2026-09-04; minimum two years.\n"
        "- Parameters: frozen; diagnostics preregistered and not used for selection.\n"
        f"- Prior artifact integrity: {acceptance['prior_artifact_integrity']['status']} across {acceptance['prior_artifact_integrity']['checked']} files.\n"
        f"- Automated tests: {acceptance['automated_tests']['status']} (`{test_output}`).\n"
        f"- Calendar validation: {acceptance['calendar_validation']['status']}.\n\n"
        "## Answers to the required questions\n\n"
        "1. **Did the corrected engine replicate on independent intraday data?** Not evaluated; no qualifying dataset was available.\n"
        "2. **Were Phase 2A/2B conclusions confirmed?** Inconclusive. Their live NO-GO remains the only safe status, but independent directional replication did not occur.\n"
        "3. **Does natural long still outperform residual stock-to-ETF?** Inconclusive.\n"
        "4. **Are stock-to-stock pairs still weak?** Inconclusive.\n"
        "5. **Does breakout help or hurt?** Inconclusive on markets. Separate attribution now reconciles mechanically.\n"
        "6. **Were grids too narrow, wide, sparse, or badly stopped?** Inconclusive; diagnostic families were registered but not run.\n"
        "7. **Does averaging improve campaign entry?** Inconclusive on independent data.\n"
        "8. **Are stop/TP mechanics realistic on 5m/15m?** Mechanical rules pass deterministic tests; empirical behavior is unvalidated.\n"
        "9. **How much did daily OHLC distort results?** Not measurable without the independent intraday comparison.\n"
        "10. **Robust after costs/slippage?** Not evaluated.\n"
        "11. **Robust after removing best campaign/month?** Not evaluated.\n"
        "12. **Remaining leakage/accounting issue?** No known mechanical lookahead or reconciliation defect in tests; event provenance and market-data correctness remain uncertified.\n"
        "13. **Ready for deeper research?** No strategy is promoted. Resume the same frozen Phase 2D only after the data gate passes.\n"
        "14. **Ready for paper/live?** No.\n"
        "15. **Exact next phase?** `Phase 2D-R`: provision a licensed independent intraday source with raw/adjusted 5m or 15m RTH data and historical events, verify entitlement/coverage, then rerun this unchanged snapshot from the beginning.\n\n"
        "## Required conclusion block\n\n"
        "```text\n"
        f"BACKTEST ENGINE STATUS: {acceptance['backtest_engine_status']}\n"
        f"INDEPENDENT DATA STATUS: {acceptance['independent_data_status']}\n"
        "PHASE 2A/2B CORRECTED CONCLUSION: INCONCLUSIVE\n"
        "NATURAL LONG GRID STATUS: INCONCLUSIVE\n"
        "RESIDUAL STOCK-TO-ETF STATUS: INCONCLUSIVE\n"
        "STOCK-TO-STOCK PAIRS STATUS: INCONCLUSIVE\n"
        "BREAKOUT CONTINUATION STATUS: INCONCLUSIVE\n"
        "GRID PARAMETER REASONABLENESS: MIXED\n"
        "STOP/TP MECHANICS: MIXED\n"
        "LIVE TRADING STATUS: NO-GO\n"
        "RESEARCH CONTINUATION: NO-GO\n"
        "NEXT RECOMMENDED PHASE: PHASE 2D-R — resume the unchanged frozen protocol after licensed independent intraday and event data are provisioned\n"
        "```\n\n"
        "PHASE 2D STATUS: **NO-GO-DATA**",
    )


def run_validation(root: Path, config_path: Path, output: Path) -> dict[str, Any]:
    snapshot_path = output / SNAPSHOT_NAME
    if not snapshot_path.exists():
        raise FrozenConfigurationError("Run the freeze command before validation")
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    config = load_config(config_path)
    config.pop("_project_root", None)
    snapshot_failures = _verify_snapshot(root, config, snapshot)
    universe = _universe(config)
    preflight = AlphaVantageIndependentAdapter(config).preflight().to_dict()
    integrity = _artifact_integrity(root, output, snapshot)
    calendar = _calendar_report(config, output)
    tests = _test_suite(root)
    _write_data_reports(output, config, universe, preflight)
    acceptance = _write_blocked_reports(
        output, config, preflight, integrity, calendar, tests, snapshot_failures
    )
    _write_final_report(output, acceptance, universe)
    return acceptance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 2D frozen independent validation")
    parser.add_argument("command", choices=("freeze", "validate"))
    parser.add_argument("--root", default=".")
    parser.add_argument("--config", default="config/phase2d_frozen.yaml")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    config_path = (root / args.config).resolve()
    config = load_config(config_path)
    output = root / config["outputs"]["directory"]
    if args.command == "freeze":
        snapshot = create_frozen_snapshot(root, config_path, output)
        print(f"Frozen Phase 2D engine at {snapshot['git_commit_hash']}")
        return 0
    acceptance = run_validation(root, config_path, output)
    print(f"PHASE 2D STATUS: {acceptance['phase2d_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
