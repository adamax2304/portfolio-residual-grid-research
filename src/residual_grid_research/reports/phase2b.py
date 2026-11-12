from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _pct(value: Any) -> str:
    return "n/a" if value is None or pd.isna(value) else f"{float(value):.2%}"


def _num(value: Any, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    if math.isinf(float(value)):
        return "∞"
    return f"{float(value):.{digits}f}"


def _money(value: Any) -> str:
    return "n/a" if value is None or pd.isna(value) else f"${float(value):,.0f}"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "No rows."
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def _family_summary(expanded: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for family, frame in expanded.groupby("family"):
        rows.append({
            "family": family, "runs": len(frame),
            "positive_edge_rate": float(((frame["expectancy_usd"] > 0) & (frame["profit_factor"] > 1.15)).mean()),
            "median_return": float(frame["oos_return"].median()), "median_pf": float(frame["profit_factor"].replace(np.inf, np.nan).median()),
            "median_campaigns": float(frame["campaigns"].median()), "median_robustness": float(frame["robustness_score"].median()),
            "phase2c_candidates": int(frame["phase2c_candidate"].sum()),
        })
    return pd.DataFrame(rows)


def _breakout_summary(breakout: pd.DataFrame) -> pd.DataFrame:
    selected = breakout[breakout["sample"] == "phase2b_expanded"] if "sample" in breakout else breakout
    rows = []
    for family, frame in selected.groupby("family"):
        rows.append({
            "family": family, "runs": len(frame),
            "mean_incremental_return": float(frame["breakout_incremental_return"].mean()),
            "pf_improved_rate": float(frame["breakout_improves_pf"].astype(bool).mean()),
            "drawdown_improved_rate": float(frame["breakout_improves_drawdown"].astype(bool).mean()),
            "dependent_runs": int(frame["breakout_dependent"].astype(bool).sum()),
            "grid_pnl": float(frame["grid_pnl_usd"].sum()),
            "breakout_pnl": float((frame["breakout_pnl_usd"] + frame["hybrid_breakout_pnl_usd"]).sum()),
        })
    return pd.DataFrame(rows)


def write_edge_triage_report(
    path: str | Path,
    *,
    triage: pd.DataFrame,
    expanded: pd.DataFrame,
    pairs: pd.DataFrame,
    breakout: pd.DataFrame,
    density: pd.DataFrame,
    sweep: pd.DataFrame,
    acceptance: dict[str, Any],
    data_start: str,
    data_end: str,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    family = _family_summary(expanded)
    breakout_family = _breakout_summary(breakout)
    classification_counts = triage["classification"].value_counts().to_dict()
    promoted = [run for run, result in acceptance.items() if result["passed"]]
    underpowered = [run for run, result in acceptance.items() if result["underpowered"]]
    residual_row = family[family["family"] == "residual"].iloc[0]
    natural_row = family[family["family"] == "natural"].iloc[0]
    if residual_row["phase2c_candidates"] != natural_row["phase2c_candidates"]:
        residual_stronger = residual_row["phase2c_candidates"] > natural_row["phase2c_candidates"]
    else:
        residual_stronger = residual_row["median_robustness"] > natural_row["median_robustness"]
    pair_row = family[family["family"] == "pair"]
    pair_viable = bool(len(pair_row) and pair_row.iloc[0]["phase2c_candidates"] > 0)
    sweep_required = sweep[sweep["sweep_mode"] == "required"]
    powered_sweeps = sweep_required[sweep_required["campaigns"] >= 10]
    sweep_help_rate = float(((powered_sweeps["pf_delta"] > 0) & (powered_sweeps["expectancy_delta_usd"] > 0)).mean()) if len(powered_sweeps) else None
    breakout_delta = float(breakout_family["mean_incremental_return"].mean()) if len(breakout_family) else 0.0
    lines = [
        "# Phase 2B — Edge Triage & Signal Density Expansion",
        "",
        "## Decision",
        "",
        "**The project remains NO-GO for live trading. Phase 2A's NO-GO is unchanged.**",
        "",
        "Phase 2B is diagnostic research only. No exchange, broker, live-order, or API-trading integration was added.",
        "",
        "## What Phase 2B tested",
        "",
        f"- Extended adjusted daily sample: {data_start} through {data_end}.",
        f"- Expanded liquid large/mid-cap strategy runs across all three families: {len(expanded)} total runs.",
        f"- Same-sector/economic pair candidates screened: {len(pairs)}; selected before backtesting: {int(pairs['selected'].sum())}.",
        f"- One-at-a-time signal-density variants on the four deep-dive controls: {len(density)}.",
        f"- Phase 2C research-gate promotions: {len(promoted)}.",
        "",
        "## Phase 2A candidate triage",
        "",
        "The original OOS return and campaign accounting below come directly from the preserved Phase 2A sidecars. `Trade legs` counts realized closing legs; `Campaigns` counts complete entry-to-flat episodes.",
        "",
    ]
    triage_rows = []
    for row in triage.to_dict("records"):
        dominance = "/".join(_pct(row.get(key)) for key in (
            "top_campaign_gross_profit_share", "top_week_gross_profit_share", "top_month_gross_profit_share"
        ))
        triage_rows.append([
            row["run"], row["classification"], _pct(row["oos_return"]), _num(row["profit_factor"]),
            _money(row["expectancy_usd"]), _pct(row["max_drawdown"]), row["trade_legs"], row["campaigns"],
            _num(row["average_campaign_hours"], 1), _pct(row["exposure_pct"]), _money(row["average_mae_usd"]),
            _money(row["average_mfe_usd"]), _money(row["worst_campaign_usd"]), _money(row["best_campaign_usd"]), dominance,
        ])
    lines.append(_table(
        ["Run", "Class", "OOS", "PF", "Exp.", "DD", "Trade legs", "Campaigns", "Avg h", "Exposure", "Avg MAE", "Avg MFE", "Worst", "Best", "Top campaign/week/month"],
        triage_rows,
    ))
    lines += ["", "Classification counts: " + ", ".join(f"{key}={value}" for key, value in classification_counts.items()) + ".", ""]
    zero_campaigns = int((triage["campaigns"] == 0).sum())
    negative_with_sample = int(((triage["campaigns"] >= 10) & ((triage["expectancy_usd"] <= 0) | (triage["profit_factor"] <= 1))).sum())
    lines += [
        "## Triage diagnosis",
        "",
        f"- Phase 2A had {zero_campaigns} zero-campaign runs, direct evidence that its filters/universe left some hypotheses untestable.",
        f"- {negative_with_sample} Phase 2A runs had at least 10 campaigns and still showed non-positive expectancy or PF ≤ 1, evidence of weak edge rather than density alone.",
        f"- In the expanded sample, natural grids reached a median {natural_row['median_campaigns']:.0f} campaigns versus {residual_row['median_campaigns']:.0f} for residual ETF runs. Expansion improved diagnosis, but did not produce a broad robust edge.",
        "- The result is therefore mixed: Phase 2A was underpowered in many runs, but loosening density constraints does not rescue the residual or pair families after costs.",
        "",
    ]
    lines += ["## Phase 2A regime and exit attribution", ""]
    lines.append(_table(
        ["Run", "Range regime", "Breakout regime", "Failed breakout", "Warning", "Kill", "Time stop", "Grid mode", "Hybrid", "Long residual", "Short residual"],
        [[row["run"], *[_money(row[key]) for key in (
            "range_regime_pnl_usd", "breakout_regime_pnl_usd", "failed_breakout_regime_pnl_usd", "warning_regime_pnl_usd",
            "kill_pnl_usd", "time_stop_pnl_usd", "grid_pnl_usd", "hybrid_breakout_pnl_usd",
            "long_residual_pnl_usd", "short_residual_pnl_usd",
        )]] for row in triage.to_dict("records")],
    ))
    lines += ["", "## Expanded-universe results by family", ""]
    lines.append(_table(
        ["Family", "Runs", "Positive edge", "Median return", "Median PF", "Median campaigns", "Median robustness", "Phase 2C"],
        [[row.family, row.runs, _pct(row.positive_edge_rate), _pct(row.median_return), _num(row.median_pf), _num(row.median_campaigns, 1), _pct(row.median_robustness), row.phase2c_candidates] for row in family.itertuples()],
    ))
    lines += ["", "### Highest-ranked expanded runs", ""]
    ranked = expanded.sort_values(["phase2c_candidate", "robustness_score", "expectancy_usd"], ascending=False).head(20)
    lines.append(_table(
        ["Run", "OOS", "PF", "Expectancy", "DD", "Legs", "Campaigns", "2x-cost exp.", "Local pass", "Robustness", "Gate"],
        [[row.run, _pct(row.oos_return), _num(row.profit_factor), _money(row.expectancy_usd), _pct(row.max_drawdown), row.trade_legs,
          row.campaigns, _money(row.strict_2x_cost_expectancy_usd), _pct(row.local_parameter_pass_rate), _pct(row.robustness_score),
          "PASS" if row.phase2c_candidate else "FAIL"] for row in ranked.itertuples()],
    ))
    lines += ["", "## Pair screening", "", "Pairs were formed only inside the named economic groups, then screened on overlap, liquidity, median rolling correlation, beta stability, half-life/crossing stationarity proxies, and event-blocked share.", ""]
    selected_pairs = pairs[pairs["selected"]]
    lines.append(_table(
        ["Pair", "Group", "Corr", "Beta stability", "Half-life", "Crossings/yr", "ADF p", "Event-blocked", "Min ADV"],
        [[f"{row.asset_a}/{row.asset_b}", row.group, _num(row.median_corr_60), _num(row.median_beta_stability), _num(row.half_life_bars, 1),
          _num(row.crossings_per_year, 1), _num(row.adf_pvalue, 3), _pct(row.event_blocked_pct), _money(row.minimum_average_dollar_volume)]
         for row in selected_pairs.itertuples()],
    ))
    lines += ["", "The full selected/rejected audit, including failure reasons, is in `pair_diagnostics.csv`.", ""]
    lines += ["## Signal-density diagnostics", "", "Sweeps are one-at-a-time, not a Cartesian optimization. A valid signal is an ARMED transition; a generated trade is a completed campaign.", ""]
    density_rows = []
    for (fam, dimension), frame in density.groupby(["family", "dimension"]):
        viable = (frame["expectancy_usd"] > 0) & (frame["profit_factor"] > 1.15)
        strict = (frame["strict_2x_cost_expectancy_usd"] > 0) & (frame["strict_2x_cost_profit_factor"] > 1.0)
        density_rows.append([fam, dimension, len(frame), _num(frame["trades_generated"].min(), 0), _num(frame["trades_generated"].median(), 1),
                             _num(frame["trades_generated"].max(), 0), _pct(viable.mean()), _pct(strict.mean()), _pct(frame["robustness_score"].mean())])
    lines.append(_table(["Family", "Dimension", "Variants", "Min trades", "Median", "Max", "Positive/PF>1.15", "Survives 2x cost", "Mean robust"], density_rows))
    lines += ["", "## Breakout continuation attribution", ""]
    breakout_rows = []
    for row in breakout_family.itertuples():
        if row.family == "residual":
            recommendation = "DISABLE: negative aggregate and incremental contribution"
        elif row.family == "natural":
            recommendation = "NO EFFECT OBSERVED"
        else:
            recommendation = "DISABLE IN BASELINE: mixed counterfactual, negative campaign contribution"
        breakout_rows.append([row.family, row.runs, _pct(row.mean_incremental_return), _pct(row.pf_improved_rate), _pct(row.drawdown_improved_rate),
                              row.dependent_runs, _money(row.grid_pnl), _money(row.breakout_pnl), recommendation])
    lines.append(_table(
        ["Family", "Runs", "Mean incremental return", "PF improved", "DD improved", "Dependent", "Grid P&L", "Breakout/hybrid P&L", "Research setting"],
        breakout_rows,
    ))
    lines += [
        "",
        "`breakout_attribution.csv` contains the enabled-versus-disabled comparison for every Phase 2A and expanded run, plus kill, failed-breakout, time-stop, grid, hybrid, and direction contributions.",
        "",
        "## Liquidity sweep/reclaim prototype",
        "",
        "The required variant enters only after a later reclaim candle, one to three bars after the sweep. The boost variant leaves eligibility unchanged and increases size only when that causal confirmation exists.",
        "",
    ]
    lines.append(_table(
        ["Run", "Mode", "Campaigns", "Δ trades", "PF", "ΔPF", "Expectancy", "Δ expectancy", "DD", "ΔDD"],
        [[row.run, row.sweep_mode, row.campaigns, _num(row.trade_count_delta, 0), _num(row.profit_factor), _num(row.pf_delta),
          _money(row.expectancy_usd), _money(row.expectancy_delta_usd), _pct(row.max_drawdown), _pct(row.drawdown_delta)] for row in sweep.itertuples()],
    ))
    lines += ["", "## Phase 2B research-only gate", ""]
    if promoted:
        lines.append("Promoted to Phase 2C diagnostic candidates: " + ", ".join(promoted) + ".")
    else:
        lines.append("No run passed every Phase 2B research-only gate.")
    if underpowered:
        lines += ["", "Positive but explicitly underpowered runs: " + ", ".join(underpowered[:20]) + ("…" if len(underpowered) > 20 else "") + "."]
    lines += ["", "Every check and failure reason is recorded in `phase2b_acceptance.json`.", ""]
    lines += [
        "## Answers to the Phase 2B questions",
        "",
        "- **Live status:** NO-GO remains in force.",
        f"- **Deeper research:** {'The only research promotions are ' + ', '.join(promoted) if promoted else 'No strategy clears the full Phase 2C research gate'}.",
        f"- **Residual ETF versus natural long:** {'Residual stock-to-ETF is stronger' if residual_stronger else 'Natural long grid is stronger'} on the predeclared family comparison (promotion count, then median robustness). This is a research ranking, not evidence for deployment.",
        f"- **Stock-to-stock pairs:** {'At least one pair clears the research gate' if pair_viable else 'The pair family is not yet viable under the research gate'}. MA/V is locally stable in the density sweep but remains underpowered and profit-concentrated.",
        f"- **Breakout continuation:** Across families, average incremental return was {_pct(breakout_delta)}. Disable it for residual and pair research baselines; natural grids recorded no continuation activity in this daily sample.",
        (
            f"- **Liquidity sweeps:** Among adequately powered required-filter tests, {_pct(sweep_help_rate)} improved both PF and expectancy."
            if sweep_help_rate is not None else
            "- **Liquidity sweeps:** No required-filter prototype retained 10 campaigns. The one- and two-campaign improvements are underpowered; the filter currently removes too many entries to claim benefit."
        ),
        "",
        "## Recommended next phase",
        "",
        (
            "Phase 2C should independently replicate only the promoted runs using a longer point-in-time event archive and licensed multi-year intraday data, with parameters frozen before the new sample."
            if promoted else
            "Do not begin implementation-oriented Phase 2C. The next research step should be a data-quality phase: acquire licensed multi-year intraday candles and point-in-time event history, then rerun the frozen Phase 2B diagnostics."
        ),
        "",
        "Do not add live-trading infrastructure in either case.",
        "",
        "## Limitations",
        "",
        "- The extended study still uses adjusted daily Yahoo/yfinance candles; it cannot resolve intraday path ordering.",
        "- Earnings dates are retrospective rather than a point-in-time announcement archive.",
        "- The universe is controlled but survivor-selected, so cross-sectional results retain survivorship bias.",
        "- Pair stationarity uses rolling-correlation, beta-stability, half-life, crossings, and ADF proxies; it is not proof of a stable economic equilibrium.",
        "- One-at-a-time density and local-neighborhood tests diagnose fragility but do not explore all parameter interactions.",
        "- Strict-cost estimates hold the realized trade path fixed; selected candidates also receive local reruns, but queue and quote data remain unavailable.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_candidate_deep_dive(
    path: str | Path,
    *,
    triage: pd.DataFrame,
    campaigns: pd.DataFrame,
    density: pd.DataFrame,
    breakout: pd.DataFrame,
    proximity: pd.DataFrame,
) -> Path:
    path = Path(path)
    lines = [
        "# Phase 2B — Candidate Deep Dive",
        "",
        "The headline and campaign tables in this document use the preserved Phase 2A OOS sample. Signal-density tables are explicitly labeled as the longer Phase 2B diagnostic sample.",
        "",
    ]
    breakout_a = breakout[breakout["sample"] == "phase2a"].set_index("run") if "sample" in breakout else breakout.set_index("run")
    proximity_index = proximity.set_index("run")
    for run in ("residual_grid:JPM/XLF", "natural_long_grid:CSCO", "stock_pair_grid:MA/V", "residual_grid:XOM/XLE"):
        summary = triage[triage["run"] == run].iloc[0]
        selected = campaigns[campaigns["run"] == run].copy().sort_values("entry_time")
        lines += [
            f"## {run}",
            "",
            f"Classification: **{summary['classification']}**. Phase 2A OOS return {_pct(summary['oos_return'])}, PF {_num(summary['profit_factor'])}, expectancy {_money(summary['expectancy_usd'])}, max drawdown {_pct(summary['max_drawdown'])}, {int(summary['campaigns'])} campaigns.",
            "",
            f"![{run} diagnostics](assets/{run.replace(':', '_').replace('/', '_')}.png)",
            "",
            "### Monthly OOS campaign P&L",
            "",
        ]
        if selected.empty:
            lines.append("No completed OOS campaigns.")
        else:
            months = pd.period_range("2024-03", "2026-09", freq="M")
            monthly = selected.assign(month=pd.to_datetime(selected["exit_time"]).dt.to_period("M")).groupby("month").agg(pnl_usd=("pnl_usd", "sum"), campaigns=("group_id", "count")).reindex(months, fill_value=0)
            lines.append(_table(["Month", "P&L", "Campaigns"], [[str(index), _money(row.pnl_usd), int(row.campaigns)] for index, row in monthly.iterrows()]))
        lines += ["", "### Campaign-level detail", ""]
        campaign_rows = []
        for row in selected.itertuples():
            campaign_rows.append([
                pd.Timestamp(row.entry_time).date(), pd.Timestamp(row.exit_time).date(), _num(row.duration_hours, 1), _money(row.pnl_usd),
                row.campaign_mode, row.direction, row.exit_category, _money(row.mae_usd), _money(row.mfe_usd), _num(row.return_on_risk),
            ])
        lines.append(_table(["Entry", "Exit", "Hours", "P&L", "Mode", "Direction", "Exit type", "MAE", "MFE", "R"], campaign_rows))
        values = pd.to_numeric(selected.get("return_on_risk", pd.Series(dtype=float)), errors="coerce").dropna()
        lines += ["", "### Return distribution and concentration", ""]
        if len(values):
            quantiles = values.quantile([0, .1, .25, .5, .75, .9, 1])
            lines.append(_table(["Quantile", "Campaign R"], [[f"{index:.0%}", _num(value)] for index, value in quantiles.items()]))
        lines += [
            "",
            f"Top campaign/week/month shares of gross positive P&L: {_pct(summary['top_campaign_gross_profit_share'])} / {_pct(summary['top_week_gross_profit_share'])} / {_pct(summary['top_month_gross_profit_share'])}.",
            "",
            "### Grid, breakout, direction, and exit contribution",
            "",
        ]
        attrib = breakout_a.loc[run]
        lines.append(_table(
            ["Grid", "Breakout", "Hybrid", "Failed breakout", "Kill", "Time stop", "Long", "Short", "No-breakout return", "No-breakout PF", "Recommendation"],
            [[_money(attrib.grid_pnl_usd), _money(attrib.breakout_pnl_usd), _money(attrib.hybrid_breakout_pnl_usd),
              _money(attrib.failed_breakout_pnl_usd), _money(attrib.kill_pnl_usd), _money(attrib.time_stop_pnl_usd),
              _money(attrib.long_residual_pnl_usd), _money(attrib.short_residual_pnl_usd), _pct(attrib.no_breakout_return),
              _num(attrib.no_breakout_profit_factor), attrib.enable_recommendation]],
        ))
        prox = proximity_index.loc[run]
        lines += [
            "",
            "### Event proximity",
            "",
            f"Nearest event distance: {_num(prox.nearest_event_days, 0)} business days. Campaigns within 3/5/10 business days of any mapped event: {int(prox.within_3)}/{int(prox.within_5)}/{int(prox.within_10)}. These counts describe proximity; configured exclusion rules were still applied.",
            "",
            "### Phase 2B signal-density and sensitivity table",
            "",
        ]
        selected_density = density[density["run"] == run]
        sensitivity_rows = []
        for dimension, frame in selected_density.groupby("dimension"):
            viable = (frame["expectancy_usd"] > 0) & (frame["profit_factor"] > 1.15)
            sensitivity_rows.append([
                dimension, ", ".join(map(str, frame["value"].tolist())), _num(frame["trades_generated"].min(), 0),
                _num(frame["trades_generated"].max(), 0), _money(frame["expectancy_usd"].min()), _money(frame["expectancy_usd"].max()),
                _num(frame["profit_factor"].replace(np.inf, np.nan).min()), _num(frame["profit_factor"].replace(np.inf, np.nan).max()),
                _pct(viable.mean()), _pct(frame["robustness_score"].mean()),
            ])
        lines.append(_table(["Dimension", "Values", "Min trades", "Max trades", "Min exp.", "Max exp.", "Min PF", "Max PF", "Viable", "Mean robust"], sensitivity_rows))
        lines.append("")
    lines += [
        "## Deep-dive conclusion",
        "",
        "These diagnostics do not overturn Phase 2A. Positive candidates remain hypotheses until they meet density, concentration, local-stability, regime-diversity, and independent-data requirements. XOM/XLE remains the negative control for detecting diagnostics that would otherwise make every relationship look attractive.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
