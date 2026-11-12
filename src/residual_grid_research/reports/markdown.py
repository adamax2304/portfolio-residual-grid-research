from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from residual_grid_research.models import BacktestResult


def _pct(value: Any) -> str:
    return "n/a" if value is None or pd.isna(value) else f"{float(value):.2%}"


def _num(value: Any, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "n/a"
    if value == float("inf"):
        return "∞"
    return f"{float(value):.{digits}f}"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def write_research_report(
    path: str | Path,
    *,
    diagnostics: dict[str, dict[str, Any]],
    results: list[BacktestResult],
    baselines: dict[str, dict[str, Any]],
    selection_bias: dict[str, Any] | None = None,
    data_source: str,
    event_coverage: str,
    config_path: str,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Residual Grid + Breakout Continuation Research Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Executive verdict",
        "",
    ]
    edge_results = [baselines.get(result.strategy_name, {}).get("edge_found", False) for result in results]
    synthetic = "synthetic" in data_source.lower()
    if synthetic:
        lines.append("This run validates software behavior on synthetic data only. It makes **no market-edge claim**, regardless of simulated returns.")
    elif results and any(edge_results):
        lines.append("At least one tested run beat all available mandatory baselines net of modeled costs. This is a research signal, not authorization for live trading.")
    else:
        lines.append("No tested run beat all mandatory baselines net of modeled costs. Edge is **not established**.")
    lines += [
        "",
        "## Scope and methodology",
        "",
        f"- Data source: {data_source}",
        "- Price basis: total-return adjusted on every relationship leg.",
        "- Execution: signals at bar close, fills at the next bar open; no lookahead.",
        "- Ambiguous same-bar stop/target: adverse outcome first by default.",
        "- Core intraday session: 09:30–16:00 America/New_York; open/close confirmation buffers are configurable.",
        f"- Event coverage: {event_coverage}",
        f"- Configuration: `{config_path}`",
        "- Live order routing: deliberately absent.",
        "",
        "## Phase 1a — relationship diagnostics",
        "",
    ]
    diag_rows = []
    for name, item in diagnostics.items():
        diag_rows.append([
            name,
            item.get("observations", 0),
            _num(item.get("latest_corr_60")),
            _num(item.get("half_life_bars"), 1),
            _num(item.get("crossings_per_year"), 1),
            _pct(item.get("failure_rate_beyond_kill")),
            item.get("go_no_go", "n/a"),
        ])
    lines.append(_table(["Relationship", "N", "Corr 60", "Half-life", "Crossings/year", "Kill failure", "Verdict"], diag_rows) if diag_rows else "No diagnostics were run.")
    lines += ["", "## Strategy results", ""]
    metric_rows = []
    for result in results:
        m = result.metrics
        metric_rows.append([
            result.strategy_name,
            _pct(m.get("total_return")),
            _pct(m.get("annualized_return")),
            _pct(m.get("max_drawdown")),
            _num(m.get("sharpe")),
            _num(m.get("sortino")),
            _num(m.get("profit_factor")),
            _pct(m.get("win_rate")),
            m.get("fill_count", 0),
            m.get("kill_count", 0),
            f"${m.get('cost_drag_usd', 0):,.2f}",
        ])
    lines.append(_table(
        ["Strategy", "Return", "Annualized", "Max DD", "Sharpe", "Sortino", "PF", "Win rate", "Fills", "Kills", "Cost drag"],
        metric_rows,
    ) if metric_rows else "No backtests were run.")
    lines += ["", "### Execution and outcome detail", ""]
    detail_rows = []
    for result in results:
        m = result.metrics
        sensitivity = m.get("slippage_sensitivity_return", {})
        detail_rows.append([
            result.strategy_name,
            _num(m.get("expectancy_r")),
            _num(m.get("mean_holding_hours"), 1),
            _pct(m.get("exposure_pct")),
            _num(m.get("turnover"), 2),
            _pct(m.get("mean_reversion_success_rate")),
            _pct(m.get("breakout_success_rate")),
            _pct(sensitivity.get("0.5x")),
            _pct(sensitivity.get("2.0x")),
        ])
    lines.append(_table(
        ["Strategy", "Expectancy R", "Mean hold h", "Exposure", "Turnover", "MR success", "Breakout success", "Return @ 0.5x slip", "Return @ 2x slip"],
        detail_rows,
    ) if detail_rows else "No execution details were produced.")
    lines += ["", "### Best and worst realized trade legs", ""]
    trade_rows = []
    for result in results:
        trade_rows.append([
            result.strategy_name,
            ", ".join(f"${value:,.2f}" for value in result.metrics.get("best_5_trade_legs_usd", [])) or "n/a",
            ", ".join(f"${value:,.2f}" for value in result.metrics.get("worst_5_trade_legs_usd", [])) or "n/a",
        ])
    lines.append(_table(["Strategy", "Best 5", "Worst 5"], trade_rows) if trade_rows else "No realized trades.")
    lines += ["", "## Mandatory baseline comparison", ""]
    baseline_rows = []
    for result in results:
        base = baselines.get(result.strategy_name, {})
        baseline_rows.append([
            result.strategy_name,
            _pct(result.metrics.get("total_return")),
            _pct(base.get("buy_and_hold")),
            _pct(base.get("spy")),
            _pct(base.get("naive_two_level_mean_reversion")),
            "YES" if base.get("edge_found") else "NO",
        ])
    lines.append(_table(["Strategy", "Strategy net", "Buy & hold", "SPY", "Naive MR", "Beat all?"], baseline_rows) if baseline_rows else "No baseline comparisons were run.")
    lines += ["", "## Selection-bias check", ""]
    if selection_bias:
        lines.append(_table(
            ["Universe", "Relationships", "GO", "GO rate", "Backtests", "Avg net return", "Beat-all rate"],
            [
                ["Curated", selection_bias.get("curated_count", 0), selection_bias.get("curated_go", 0), _pct(selection_bias.get("curated_go_rate")), selection_bias.get("curated_backtests", 0), _pct(selection_bias.get("curated_average_return")), _pct(selection_bias.get("curated_edge_rate"))],
                ["Blind expansion", selection_bias.get("blind_count", 0), selection_bias.get("blind_go", 0), _pct(selection_bias.get("blind_go_rate")), selection_bias.get("blind_backtests", 0), _pct(selection_bias.get("blind_average_return")), _pct(selection_bias.get("blind_edge_rate"))],
            ],
        ))
    else:
        lines.append("Not available for this run; no generalizable edge claim is permitted.")
    lines += [
        "",
        "## Risk, implementation, and interpretation notes",
        "",
        "- Grid size is solved against every configured layer being filled and liquidated at the kill threshold.",
        "- Gross, net, and realized exposures are accounted for; a hedge is not treated as risk-free.",
        "- Commission, spread, slippage, placeholder borrow, and placeholder overnight financing are charged as configured.",
        "- Historical hard-to-borrow status and true borrow rates are unavailable. All short-leg results are less reliable and must not be presented on equal footing with long-only results.",
        "- AI research hooks are advisory, event-scoped, cached, and unable to override deterministic risk decisions.",
        "- The manually curated relationships are correlated by construction. Blind-expansion results are required before generalizing.",
        "- Any future point-in-time universe must retain delisted/acquired constituents to avoid survivorship bias.",
        "",
        "## Warnings emitted during the run",
        "",
    ]
    warning_lines = [warning for result in results for warning in result.warnings]
    lines.extend([f"- {warning}" for warning in warning_lines] or ["- None."])
    lines += [
        "",
        "## Reproducibility",
        "",
        "Re-run through the CLI using the recorded configuration and data cache. Cached provider files are intentionally not committed. Reports are deterministic for a fixed dataset/configuration; synthetic demos additionally use the configured seed.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
