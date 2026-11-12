from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def _pct(value: Any) -> str:
    return "n/a" if value is None or pd.isna(value) else f"{float(value):.2%}"


def _num(value: Any, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "n/a"
    if value == float("inf"):
        return "∞"
    return f"{float(value):.{digits}f}"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "No results."
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def _metrics_table(metrics: dict[str, dict[str, Any]], baselines: dict[str, dict[str, Any]] | None = None) -> str:
    rows = []
    for name, item in metrics.items():
        base = (baselines or {}).get(name, {})
        rows.append([
            name,
            _pct(item.get("total_return")),
            _pct(item.get("annualized_return")),
            _pct(item.get("max_drawdown")),
            _num(item.get("profit_factor")),
            _pct(item.get("win_rate")),
            f"${float(item.get('expectancy_usd', 0)):,.2f}",
            _num(item.get("mean_holding_hours"), 1),
            item.get("number_of_trades", 0),
            _pct(item.get("exposure_pct")),
            _num(item.get("max_gross_leverage_used")),
            _num(item.get("max_net_beta_exposure")),
            _pct(base.get("buy_and_hold")),
            _pct(base.get("secondary_buy_and_hold")),
        ])
    return _table(
        ["Run", "Return", "Ann.", "Max DD", "PF", "Win", "Expectancy", "Avg hold h", "Trades", "Exposure", "Max gross", "Max |β|", "Stock B&H", "ETF/pair B&H"],
        rows,
    )


def write_real_data_report(
    path: str | Path,
    *,
    daily_start: str,
    daily_end: str,
    intraday_start: str,
    intraday_end: str,
    event_count: int,
    full_metrics: dict[str, dict[str, Any]],
    oos_metrics: dict[str, dict[str, Any]],
    intraday_metrics: dict[str, dict[str, Any]],
    full_baselines: dict[str, dict[str, Any]],
    oos_baselines: dict[str, dict[str, Any]],
    monthly: pd.DataFrame,
    sensitivity: pd.DataFrame,
    gates: dict[str, tuple[bool, list[str]]],
    sensitivity_targets: list[str],
    first_test: pd.Timestamp,
    diagnostics: dict[str, dict[str, Any]],
) -> Path:
    passed = [name for name, (ok, _) in gates.items() if ok]
    promising = [
        name for name, item in oos_metrics.items()
        if item.get("expectancy_usd", 0) > 0 and item.get("profit_factor", 0) > 1.15
    ]
    failed = [name for name in oos_metrics if name not in promising]
    lines = [
        "# Phase 2A — Real Historical Data Validation",
        "",
        "## Acceptance decision",
        "",
        (
            f"**{len(passed)} strategy run(s) passed every acceptance gate:** {', '.join(passed)}. This result still requires independent replication before any live integration."
            if passed
            else "**No strategy run passed every acceptance gate. Live integration is not recommended.**"
        ),
        "",
        "The acceptance decision uses out-of-sample results only. Positive-looking synthetic results are not considered evidence.",
        "",
        "## Data and separation from synthetic validation",
        "",
        "- Synthetic validation remains in `outputs/research_report.md` and was not overwritten.",
        f"- Real adjusted daily OHLCV: {daily_start} through {daily_end}, Yahoo Finance via yfinance, cached under `data/real/raw/yahoo/`.",
        f"- Limited 15-minute adjusted OHLCV check: {intraday_start} through {intraday_end}; this short slice is not the main acceptance evidence.",
        f"- Historical event rows applied: {event_count}, from `data/real/events/historical_events.csv`.",
        "- Signals use closed candles and execute at the next candle open with commission, spread, slippage, and short-borrow placeholders.",
        "- Fill prices are clamped to the candle high/low. Ambiguous stop/target candles resolve adverse-first.",
        "",
        "## Pair-discovery diagnostics",
        "",
    ]
    diag_rows = [[
        name,
        _num(item.get("latest_corr_60")),
        _num(item.get("half_life_bars"), 1),
        _num(item.get("crossings_per_year"), 1),
        _pct(item.get("failure_rate_beyond_kill")),
        item.get("go_no_go", "n/a"),
    ] for name, item in diagnostics.items()]
    lines.append(_table(["Relationship", "Corr 60", "Half-life", "Crossings/yr", "Kill failure", "Verdict"], diag_rows))
    lines += [
        "",
        "## In-sample/full-period descriptive results",
        "",
        "These full-period figures are descriptive and are not the acceptance result.",
        "",
        _metrics_table(full_metrics, full_baselines),
        "",
        "## Out-of-sample 6-month / 1-month walk-forward results — main result",
        "",
        f"The first OOS month begins {first_test.date()}. Parameters were fixed before this run. Each one-month bucket uses only information available at that time; the preceding six months serve as calibration/warm-up. Campaigns are not optimized on the combined period.",
        "",
        _metrics_table(oos_metrics, oos_baselines),
        "",
        "Monthly bucket details are in `outputs/real_data_walk_forward_monthly.csv`.",
        "",
        "## MAE/MFE and regime attribution",
        "",
    ]
    regime_rows = []
    for name, item in oos_metrics.items():
        regimes = item.get("performance_by_regime", {})
        regime_rows.append([
            name,
            f"${float(item.get('average_mae_usd', 0)):,.2f}",
            f"${float(item.get('average_mfe_usd', 0)):,.2f}",
            _num(item.get("worst_mae_r")),
            _num(item.get("best_mfe_r")),
            "; ".join(f"{key}: {value.get('trades', 0)} / ${value.get('pnl_usd', 0):,.0f}" for key, value in regimes.items()),
        ])
    lines.append(_table(["Run", "Avg MAE", "Avg MFE", "Worst MAE R", "Best MFE R", "Regime trades / P&L"], regime_rows))
    lines += [
        "",
        "## Limited 15-minute execution check",
        "",
        "Yahoo-backed intraday history is limited to roughly 60 days. These results test candle-level mechanics and filters but cannot satisfy the requested 6m/1m walk-forward design.",
        "",
        _metrics_table(intraday_metrics),
        "",
        "## Sensitivity analysis",
        "",
        f"One-at-a-time sweeps were run on the strongest default OOS member of each family: {', '.join(sensitivity_targets)}. This covers every requested parameter value without selecting a full-period optimum. The full table is `outputs/real_data_sensitivity.csv`.",
        "",
    ]
    sensitivity_rows = []
    if not sensitivity.empty:
        for (name, dimension), frame in sensitivity.groupby(["run", "dimension"]):
            viable = ((frame["expectancy_usd"] > 0) & (frame["profit_factor"] > 1.0) & (frame["max_drawdown"] > -0.15)).mean()
            sensitivity_rows.append([
                name,
                dimension,
                len(frame),
                _pct(viable),
                _pct(frame["total_return"].min()),
                _pct(frame["total_return"].max()),
            ])
    lines.append(_table(["Run", "Dimension", "Variants", "Viable", "Worst return", "Best return"], sensitivity_rows))
    lines += ["", "## Acceptance gates by strategy", ""]
    gate_rows = [[name, "PASS" if ok else "FAIL", "—" if ok else "; ".join(reasons)] for name, (ok, reasons) in gates.items()]
    lines.append(_table(["Run", "Decision", "Failed conditions"], gate_rows))
    lines += [
        "",
        "## Strategies that appear promising but did not necessarily pass",
        "",
        *(f"- {name}" for name in promising),
    ]
    if not promising:
        lines.append("- None met both positive OOS expectancy and PF > 1.15.")
    lines += ["", "## Strategies that failed the preliminary profitability screen", ""]
    lines.extend([f"- {name}" for name in failed] or ["- None."])
    lines += [
        "",
        "## Known limitations",
        "",
        "- Yahoo Finance/yfinance is a convenient research fallback, not an exchange-grade licensed backtest feed. Corporate-action corrections can be revised after the fact.",
        "- The earnings dataset is retrieved retrospectively and is not a point-in-time announcement archive; dates are usable for exclusion windows, but revision history is unavailable.",
        "- Only about 60 days of 15-minute history was available. Main OOS conclusions therefore use daily candles, which cannot reproduce intraday grid sequencing.",
        "- Historical borrow availability and actual borrow fees are unavailable; short legs use the configured flat placeholder.",
        "- Bid/ask quotes and queue position are unavailable. Spread and slippage are modeled conservatively, and fills are bounded by candle ranges.",
        "- The controlled universe is curated and contains current survivors; results remain exposed to selection and survivorship bias.",
        "- One-at-a-time sensitivity detects local fragility but does not exhaust the full parameter interaction product.",
        "- A single three-year market sample is not enough to establish production readiness.",
        "",
        "## Final recommendation",
        "",
        (
            "Do not add live execution yet. Replicate passing runs on an independent licensed intraday dataset with point-in-time events and borrow data before considering a paper-trading gate."
            if passed
            else "Do not add Bybit, MEXC, broker routing, or any live-trading integration. The Phase 2A acceptance gate was not met."
        ),
    ]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
