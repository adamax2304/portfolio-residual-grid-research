# Residual Grid Research

A standalone, deterministic research system for testing:

1. stock-to-ETF residual grids;
2. stock-to-stock spread grids;
3. natural long range grids;
4. confirmed breakout continuation after a range or spread invalidates.

This repository deliberately contains **no broker/exchange adapter and no live-order path**. It is a research/backtest project. AI hooks are advisory, event-scoped, cached, and cannot create or override entries, exits, stops, sizes, or kills.

## What is implemented

- Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED` loader with full-history caching and consistent total-return price adjustment.
- Alpha Vantage month-sliced adjusted 5-minute loader with regular-session filtering.
- Earnings/dividend/split ingestion plus normalized imported historical event calendars.
- Data-quality reports and deterministic synthetic fixtures for offline verification.
- Strictly lagged rolling return correlations, log-price OLS alpha/beta, residuals, z-scores, R², and beta stability.
- Half-life, threshold-crossing, reversion-time, extreme-failure, maximum-z, and optional ADF diagnostics.
- ATR, ADX, confirmed fractal pivots, range quality, demand/supply proximity, volume, liquidity, and market-regime features.
- Candidate scoring with the requested 20/20/15/15/15/10/5 weights.
- Explicit strategy state machine: `SCAN → CANDIDATE → ARMED → GRID_ACTIVE → WARNING / GRID_EXITING / BREAKOUT_SETUP → BREAKOUT_ACTIVE / KILL → COOLDOWN → FLAT`.
- Stock/ETF, pair, and natural long-grid strategies, including deterministic layered entries and partial exits.
- Grid-aware risk sizing against the fully loaded stack at the kill threshold.
- Portfolio leverage/open-position gates; daily/weekly loss kills; per-symbol monthly kill caps; cooldowns.
- Next-bar-open event-driven fills, commissions, spread, slippage, partial fills, borrow placeholder, and overnight-cost placeholder.
- Conservative `adverse_first` same-bar stop/target resolver plus the `tp_first` sensitivity variant.
- Shared breakout scoring and failed-breakout handling.
- Walk-forward splits and configurable sensitivity-grid runner.
- Mandatory buy-and-hold, SPY, and naive two-level mean-reversion baselines.
- Markdown reports with a plain edge/no-edge verdict and a curated-vs-blind selection-bias check.
- SQLite-backed event-level research-agent cache.
- Unit and integration tests for no-lookahead, state transitions, data adjustment, sizing, execution timing, cache behavior, and reports.

## Setup (PowerShell)

```powershell
cd C:\Users\adama\Documents\residual_grid_research
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[research,test]"
```

For Alpha Vantage downloads, set the key in the shell (do not commit it):

```powershell
$env:ALPHA_VANTAGE_API_KEY = "your-key"
```

## First run without paid data

This validates the whole pipeline against a reproducible fixture. Its P&L is **not market evidence**.

```powershell
residual-grid demo
```

The report is written to `outputs/research_report.md`.

The same run also writes auditable sidecars beside the report:

- `research_report_trades.csv` — every simulated fill;
- `research_report_decisions.csv` — every state transition and its reason;
- `research_report_equity.csv` — aligned equity curves for all configured runs;
- `research_report_diagnostics.json` — machine-readable Phase 1a output.

## Phase 1a with market data

```powershell
residual-grid fetch-daily
residual-grid diagnose
```

`fetch-daily` uses all configured curated, blind-expansion, natural-grid, and benchmark symbols. Pass symbols explicitly to limit a pull.

## Daily all-mode research report

```powershell
residual-grid research --events data\historical_events.csv
```

The optional event file schema is:

```csv
symbol,date,event_type,severity,description
CSCO,2025-02-12,EARNINGS,HIGH_IMPACT,Fiscal Q2 earnings
VZ,2025-01-10,EX_DIVIDEND,MEDIUM_IMPACT,Quarterly dividend
```

Alpha Vantage's earnings-calendar endpoint is forward-looking. For historical earnings-aware backtests, import a point-in-time historical event file. If it is absent, the generated report marks event-filtered conclusions as provisional.

## Phase 1c intraday cache

```powershell
residual-grid fetch-intraday CSCO XLK SPY --start 2025-09-01 --end 2026-09-01
```

Each calendar month is cached separately. Requests use `adjusted=true`, `extended_hours=false`, and the configured interval. Core input remains 09:30–16:00 ET; the configurable first/last ten-minute buffer is intended for breakout confirmation and feature seeding in experiment code.

To run the configured research universe from those caches:

```powershell
residual-grid research --intraday --start 2025-09-01 --end 2026-09-01 --events data\historical_events.csv
```

Current provider events can be downloaded separately (historical earnings still require a point-in-time archive):

```powershell
residual-grid fetch-events CSCO XLK SPY
```

## Walk-forward and sensitivity experiments

```powershell
residual-grid walk-forward --mode residual CSCO XLK --train-months 6 --test-months 1
residual-grid sensitivity --mode residual CSCO XLK --path strategy.residual.entry_z --values 1.2 1.4 1.6 1.8
```

Use `--synthetic` on either command for a software-only dry run. `sensitivity` accepts any numeric dotted configuration path, making the complete YAML sensitivity grid directly executable without hard-coded experiment branches.

## Configuration

All MVP decisions are in `config/default.yaml`, including:

- $100,000 capital and 2x starting effective leverage;
- 60-bar beta, 90-bar z-score, and 30/60/90/120 correlations;
- residual levels 1.4/1.7/2.0/2.2 and 2.8 kill;
- pair 3.0 kill;
- natural-grid 0.55 ATR step and 0.5 ATR stop buffer;
- 1% fully-loaded campaign risk, 2.5% daily loss, and 6% weekly loss;
- front-light 20/25/25/30 layer weights;
- realistic but replaceable cost and placeholder borrow assumptions;
- the complete sensitivity grid from the specification.

Copy the YAML to create an experiment. Keep the default file unchanged for reproducibility:

```powershell
Copy-Item config\default.yaml config\experiment.yaml
residual-grid --config config\experiment.yaml demo
```

## Programmatic use

```python
from residual_grid_research.backtest import BacktestEngine
from residual_grid_research.config import load_config
from residual_grid_research.data import make_synthetic_universe
from residual_grid_research.strategies import ResidualGridStrategy

config = load_config("config/default.yaml")
data = make_synthetic_universe(["CSCO", "XLK", "SPY"])
strategy = ResidualGridStrategy(config, "CSCO", "XLK")
result = BacktestEngine(config).run(strategy, data)
print(result.metrics)
```

## Test suite

```powershell
pytest
```

## Research interpretation rules

- “Edge found” is emitted only when net strategy return beats the underlying buy-and-hold return, SPY, and the naive mean-reversion baseline over the same sample.
- Synthetic runs prove software behavior only.
- Short results always carry an unmodeled hard-to-borrow/true-borrow-history warning.
- Curated relationships are not treated as generalizable. The configured blind sector-mapped expansion is compared separately.
- A future automated universe must use point-in-time membership to avoid survivorship bias.
- Backtest outputs are research artifacts, not investment advice.

## Phase 2A real-data validation

The controlled Phase 2A universe and conservative assumptions are recorded in `config/phase2a_real.yaml`. Real-data caches and reports use separate paths and never overwrite the synthetic validation artifacts.

```powershell
residual-grid --config config\phase2a_real.yaml phase2a-fetch
residual-grid --config config\phase2a_real.yaml phase2a-run
residual-grid --config config\phase2a_real.yaml phase2a-report
```

The final command rebuilds only the Markdown report from completed sidecars. The full run produces `outputs/real_data_research_report.md` plus separate full-period, OOS, monthly walk-forward, sensitivity, intraday, fill, campaign, equity, exposure, baseline, and acceptance-gate sidecars.

The current fallback provider is Yahoo Finance through `yfinance`: adjusted daily data supports the three-year main study, while 15-minute data is limited to the trailing 60 days and is used only for candle-execution checks. A licensed deeper intraday feed remains necessary before paper or live trading.

## Phase 2B edge triage

Phase 2B preserves every Phase 2A artifact and writes only below `outputs/phase2b/`. It expands the controlled large/mid-cap universe, screens economically related pairs before testing, runs one-at-a-time signal-density diagnostics, compares breakout enabled versus disabled, and prototypes causal liquidity sweep/reclaim entry filters.

```powershell
residual-grid --config config\phase2b_real.yaml phase2b-fetch
residual-grid --config config\phase2b_real.yaml phase2b-run
residual-grid --config config\phase2b_real.yaml phase2b-report
```

This remains research-only. The workflow contains no exchange, broker, order-routing, or live-trading integration.

## Phase 2D frozen validation

Phase 2D uses an independent Alpha Vantage intraday adapter, raw OHLC for
execution, adjusted OHLC only for indicators, and the XNYS exchange calendar.
Historical intraday access requires `ALPHA_VANTAGE_API_KEY` with sufficient
entitlement. Freeze only after committing the exact engine and configuration:

```powershell
python -m residual_grid_research.phase2d freeze
python -m residual_grid_research.phase2d validate
```

If qualifying 5m/15m data are unavailable, validation stops with
`PHASE 2D STATUS: NO-GO-DATA`; it never falls back to the Phase 2A/2B yfinance
path or invents market results.
