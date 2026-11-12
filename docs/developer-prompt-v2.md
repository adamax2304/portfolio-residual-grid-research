# Developer Prompt v2: Residual Grid + Breakout Continuation Trading Research System

**Status:** revised version. This version resolves the open ambiguities and the data-source question left unresolved in v1 (formerly §26 "Final check before coding"). It keeps the same overall design intact, adds explicit MVP defaults, a resolved data-source plan, and a phased build order so a first go/no-go signal on edge is achievable in the first working session instead of at the end of a multi-week build.

## Changelog from v1

- **Data source resolved** (§0.1): Alpha Vantage Standard plan as primary source for daily + 5-minute intraday history, going back 1+ year via month-sliced intraday queries. Free tier confirmed insufficient (see below). Polygon.io Starter listed as a backup/cross-check source.
- **Phased delivery plan added** (§0.2): Phase 1a (statistical diagnostics only, daily bars, same day) → Phase 1b (long-only daily backtest, no AI agents) → Phase 1c (intraday, short legs, breakout module, AI agents, walk-forward).
- **This stays a standalone system** (§1.1): no shared code, database, or process with any other existing trading system. Explicit design boundary.
- **All parameter ranges resolved to single MVP defaults**, with ranges kept only in the sensitivity-testing section (§14.9) — a developer should never have to guess which number in a range to hard-code.
- **Adjustment methodology fixed** (§2.1.1): total-return (split + dividend) adjusted prices required on both legs of every pair, consistently.
- **Session-window filter added** (§2.1.2): regular trading hours only for core calculations; no-trade buffer around open/close.
- **Grid risk sizing fixed** (§13.1): position size is now computed against the worst-case fully-loaded grid at the kill z-score, not against a single layer.
- **Starting capital fixed** (§2.3): $100,000 default notional base so dollar-denominated metrics are computable.
- **AI agent invocation rule added** (§16.0): agents run per discrete event (per earnings date / per news item / once per symbol-day for regime), never per bar, with cached output — this was previously unspecified and would have been extremely expensive to run naively across years of 5-minute bars.
- **Baseline/benchmark comparison made mandatory** (§14.7, §21): every report must show the strategy against buy-and-hold, a naive 2-level mean-reversion baseline, and SPY, so "edge found" is falsifiable.
- **Selection-bias caution added** (§3.3, §22): the curated pair/ETF list in §20 is a reasonable pilot but is itself correlated-by-construction; a blind sector-mapped expansion is required before treating results as generalizable edge.
- **Survivorship-bias caution added** (§3.1) for any future automated universe screening.
- **Borrow/short-availability data gap documented explicitly** (§2.2) rather than left implicit — there is no clean historical source for this; it is modeled as a flat placeholder and flagged as an unmodeled risk in short-leg results.
- **§26 rewritten** from "questions to confirm before coding" into a resolved decisions log.

---

## 0. High-level objective

Build a Python-based research system that can test and compare three trading modes:

1. **Stock-to-ETF residual grid + breakout continuation** — e.g. CSCO vs XLK/QQQ, MO vs XLP, VZ vs XLC, JPM vs XLF, XOM vs XLE. Trades the stock's residual deviation relative to its sector/benchmark ETF.
2. **Stock-to-stock spread grid + breakout continuation** — e.g. VZ/T, KO/PEP, XOM/CVX, JPM/BAC, MA/V. Trades relative mispricing between two correlated stocks.
3. **Natural long grid + breakout continuation on a single stock** — buys lower levels inside a range, takes profit into the mid/upper range, switches to breakout continuation if the range breaks upward.

**Core research question:** which mode has the best risk-adjusted edge after realistic costs, slippage, false breakouts, stop logic, and market-regime filters?

**Scope decision (unchanged from v1):** this phase is research/backtest only. Do not connect Bybit or MEXC. Do not place live orders. Exchange adapters come only after evidence of edge.

## 0.1 Data source decision (RESOLVED)

This was the single biggest gap in v1 — the plan required 1–3 years of 5-minute OHLCV across dozens of tickers/ETFs but never named a source, and free public sources cannot supply that depth.

**Primary source: Alpha Vantage, Standard plan ($49.99/month, 75 requests/minute, no daily cap).**

Verified against current Alpha Vantage documentation:

- `TIME_SERIES_INTRADAY` supports `interval=5min` (also 1/15/30/60min) and a `month=YYYY-MM` parameter that pulls a full historical month of intraday bars, going back to January 2000. `adjusted=true` (default) returns split- and dividend-adjusted values; `adjusted=false` returns raw. `extended_hours` toggles pre/post-market inclusion.
- This endpoint, and `outputsize=full` on `TIME_SERIES_DAILY` / `TIME_SERIES_DAILY_ADJUSTED`, are marked **Premium** — the free tier (25 requests/day) only returns the most recent ~100 data points, which is not usable for backtesting. A paid plan is required; there is no way around this on Alpha Vantage.
- At 75 requests/minute, pulling 12 months of 5-minute history (12 requests per symbol, one per month-slice) for a 20–30 symbol/ETF universe is on the order of 250–360 requests — a few minutes of continuous calls, not a multi-day job.
- **This account is already connected as an MCP tool in the working environment** — it can be used directly for exploratory pulls without separate integration work, and the same API key is what the backtest data pipeline should use.
- Weekly/monthly time series are free and unrestricted, but not useful at grid-relevant resolution.

**Backup / cross-check source: Polygon.io, Starter plan (~$29/month at last check — reconfirm current terms at polygon.io/pricing, third-party trackers show slightly different numbers as of mid-2026).** Unlimited calls, several years of daily and minute aggregates, 15-minute delayed (irrelevant for backtesting, only matters for live). Use to spot-check a handful of symbols against Alpha Vantage for split/dividend handling discrepancies — do not build the primary pipeline against two providers at once.

**Not recommended for this project:** free-tier yfinance/Stooq-style sources. They are fine for daily bars but only return roughly the trailing 60 days of 5-minute intraday history, which does not meet the 1-year requirement.

**Not resolved — explicitly flagged as an unmodeled gap, not a silent omission:** historical borrow cost / hard-to-borrow flags for short legs. No accessible source was found for this. See §2.2 and §13.

## 0.2 Delivery phases (RESOLVED)

v1 asked for a system this complex to produce an edge signal "today," which is not achievable for the full spec as written. This phasing reconciles the two by sequencing scope rather than cutting it.

**Phase 1a — statistical go/no-go (same working session).**
Daily adjusted bars only (`TIME_SERIES_DAILY_ADJUSTED`, `outputsize=full`) for the §20 curated universe. Compute §4 (rolling beta/correlation/residual/z-score) and run the §4.5 mean-reversion diagnostics only — no backtest engine, no grid, no AI agents. Output: does a statistical mean-reversion structure exist at all (z-score distribution, half-life, crossing frequency)? This answers "is there anything here worth building further" without touching intraday data or cost modeling.

**Phase 1b — long-only daily backtest (next).**
Full backtest engine (§14) and state machine (§8) for Strategy 1 (residual ETF, **long-only**) and Strategy 3 (natural long grid, long-only by construction) on daily bars. No AI agents — earnings/event no-trade windows come from a deterministic date filter (Alpha Vantage `EARNINGS_CALENDAR`/`DIVIDENDS`/`SPLITS`, or a manually curated list). No breakout continuation module yet — pure grid mean-reversion first. Baseline/benchmark comparison is mandatory here (§14.7, §21). Also run the blind universe-expansion check (§3.3) to test for selection bias in the curated pair list.

**Phase 1c — full feature set.**
Switch to 5-minute intraday bars. Add Strategy 2 (stock-stock pairs — this strategy is short-legged by construction and is deferred to this phase), add short legs to Strategy 1, add the breakout continuation module (§15), add the AI agents (§16, with the invocation rule in §16.0). Add walk-forward and parameter sensitivity (§14.8/§14.9).

**Phase 2 — production module**, gated on Phase 1c showing durable edge. Stays a separate, standalone codebase (§1.1).

---

## 1. Non-negotiable design principle

AI agents must not directly decide live entries, exits, sizing, or stops. All trading decisions in backtest and later live execution are produced by deterministic code: deterministic signal rules, deterministic state machine, deterministic risk manager, deterministic sizing, deterministic kill-switches, deterministic order simulation.

AI agents may only: classify news/events, summarize why a setup exists, explain post-trade errors, flag contradictions, produce human-readable reports, recommend that deterministic modules disable trading under certain conditions. If the deterministic risk manager says KILL, AI cannot override it.

### 1.1 Independence from existing systems (NEW)

This is a standalone repository. Do not import, extend, or share runtime state, database, or process with any other trading system already in use. If a shared pattern is genuinely useful (e.g. a state-machine design), copy and adapt it as a reference — do not create a shared dependency between this system and any other one, so that neither can destabilize the other.

---

## 2. Data requirements

### 2.1 Required market data

- Daily adjusted OHLCV, full history (25+ years available, use 3 years as the working window) — Phase 1a/1b.
- 5-minute intraday OHLCV, 1 year minimum via month-sliced Alpha Vantage queries — Phase 1c.

### 2.1.1 Adjustment methodology (RESOLVED)

Use **total-return adjusted** prices (split **and** dividend adjusted, `adjusted=true`) consistently on both legs of every pair. This matters specifically for dividend-paying names in this universe (MO, VZ, JPM, and dividend-heavy ETFs like XLU/XLP) — using split-only adjustment would introduce artificial discontinuities in the residual/spread at ex-dividend dates. Never mix adjusted and unadjusted series across the two legs of a pair or residual.

### 2.1.2 Session window (RESOLVED)

Core calculations (z-score, ADX, ATR, structure detection, breakout confirmation) use **regular trading hours only** (9:30–16:00 ET), `extended_hours=false`. A configurable no-trade buffer excludes the first and last `no_trade_window_minutes` (default: 10) of the session from breakout-confirmation logic and from ATR/ADX seeding, since open/close volatility and volume spikes are a common source of false breakout signals on 5-minute bars. Pre/post-market data may be pulled separately later for a dedicated session-behavior study but is out of scope for the core grid logic.

### 2.2 Required event data

Earnings dates, dividend/ex-dividend dates, splits/corporate actions, company news, macro calendar if available, US market holidays — sourced from Alpha Vantage's `EARNINGS_CALENDAR`, `DIVIDENDS`, `SPLITS` endpoints for MVP.

**Explicitly unresolved (flag, don't silently omit):** historical borrow cost and hard-to-borrow status for short legs. No clean accessible historical source was identified. Model as a flat configurable placeholder rate (§2.3) and mark every short-leg backtest result with a note that borrow risk is unmodeled — do not present short-leg P&L as equally reliable to long-only results until a real borrow-cost feed is integrated.

### 2.3 Cost assumptions

Configurable: commission per trade, spread cost, slippage in bps, borrow/funding placeholder for short legs, overnight holding cost placeholder, minimum order size, partial fill approximation.

**Starting capital (RESOLVED):** `starting_capital_usd: 100000` default, configurable. All position sizing is expressed as % of this base unless explicitly overridden, so that dollar-denominated report metrics (§14.7) are computable.

---

## 3. Universe construction

### 3.1 Candidate stock filters

Average daily dollar volume ≥ $50M, price ≥ $5, no earnings within 5–10 trading days (default: 7), no recent material one-sided event, enough historical bars for rolling beta/correlation/z-score and walk-forward.

**Survivorship-bias caution (NEW):** the current §20 list is manually curated and not subject to this issue. If universe construction is later automated (screening today's index membership and applying it retroactively), that will overstate historical edge by excluding names that were delisted, acquired, or dropped from an index. This is a Phase 1c+ concern — flagged here so it isn't rediscovered the hard way later.

### 3.2 ETF mapping

Manual config, unchanged from v1:

```
stock_etf_map:
  CSCO: [XLK, QQQ]
  VZ: [XLC]
  MO: [XLP]
  JPM: [XLF]
  XOM: [XLE]
```

### 3.3 Stock-to-stock pair discovery and selection-bias check (RESOLVED)

Initial whitelist unchanged:

```
stock_pairs:
  - [VZ, T]
  - [KO, PEP]
  - [XOM, CVX]
  - [JPM, BAC]
  - [MA, V]
  - [HD, LOW]
```

**This list is hand-picked because the correlation is already well known — that is fine for a pilot, but it is a form of selection bias.** Before treating any positive result on this list as generalizable edge, run a second, blind pass: expand to a broader sector-mapped set of pairs not individually pre-vetted by the developer's intuition (e.g. all same-GICS-subindustry pairs above a liquidity floor), and check whether the statistical/backtest results hold up outside the hand-picked names. This check belongs in Phase 1b, alongside the walk-forward split.

---

## 4. Core calculations

### 4.1 Returns and log prices

Use total-return adjusted prices (§2.1.1). `log_A = ln(price_A)`, `log_B = ln(price_B)`.

### 4.2 Rolling correlation — MVP defaults (RESOLVED)

Compute over 30/60/90/120-bar windows. **MVP hard default:** `corr_60 >= 0.65` (stock-to-ETF), `corr_60 >= 0.75` (stock-to-stock). The wider ranges from v1 (0.60–0.70 / 0.70–0.80) move to the §14.9 sensitivity grid only — the code should not branch on a range.

### 4.3 Rolling beta / hedge ratio

Rolling OLS. **MVP default beta window: 60 trading days** (90/120 reserved for sensitivity testing). Store beta, alpha, R², residual std, beta stability.

### 4.4 Residual/spread formula

Unchanged formulas:
```
residual = ln(stock_price) - alpha - beta * ln(ETF_price)
spread = ln(stock_A_price) - alpha - beta * ln(stock_B_price)
z = (residual - rolling_mean(residual, z_window)) / rolling_std(residual, z_window)
```
**MVP default `z_window`: 90 trading days** (60–120 range reserved for sensitivity testing). No lookahead: compute using only bars strictly before the current one.

### 4.5 Mean reversion diagnostics

Z-score distribution, half-life estimate, frequency of threshold crossings, median time to reversion, failure rate beyond kill z-score, max adverse excursion, optional ADF/cointegration as a diagnostic (not a hard entry rule — a pair can pass ADF historically and still break on news or fundamentals). **This is the entire scope of Phase 1a.**

---

## 5. Market-structure module

Unchanged from v1: deterministic swing highs/lows (fractal pivots), recent range high/low, ATR-based buffers, touch/rejection counts, distance to support/resistance, optional volume profile / anchored VWAP.

### 5.2 Demand/supply zone approximation

Zone width default: **0.5 ATR** (0.3–0.7 range reserved for sensitivity testing).

### 5.3 Range quality score — MVP defaults (RESOLVED)

```
ADX_14 < 23                          # was 22-25
range_width >= 3 * ATR_14
range_width <= 10 * ATR_14           # was 8-12
ATR_current <= 1.4 * ATR_20_median
```

---

## 6. News, earnings, and event filters

Hard no-trade conditions unchanged: earnings within next 5 trading days (any leg), earnings within previous 1–2 trading days, pending corporate action, ex-dividend window for short legs, material news, stale/missing data, abnormal spread/volume.

News severity classes and NO_TRADE triggers unchanged (`NOISE` / `LOW_IMPACT` / `MEDIUM_IMPACT` / `HIGH_IMPACT` / `UNKNOWN_BUT_RISKY`). See §16.0 for the invocation-frequency fix that makes this affordable to run.

---

## 7. Market regime module

Inputs: SPY, QQQ, sector ETF, VIX proxy, benchmark ETF for the hedge leg. States: `RANGE_OK / TREND_UP / TREND_DOWN / PANIC_SELL / VOL_EXPANSION / LOW_LIQUIDITY / EVENT_RISK / UNKNOWN`.

**MVP defaults (RESOLVED):**
```
market_adx_14 < 25              # pure grid gate
ATR_current <= 1.5 * ATR_20_median
```
Breakout continuation may be allowed in trend regimes if confirmed (Phase 1c).

---

## 8. Strategy state machine

Unchanged from v1: `SCAN → CANDIDATE → ARMED → GRID_ACTIVE → WARNING → GRID_EXITING → BREAKOUT_SETUP → BREAKOUT_ACTIVE → KILL → COOLDOWN → FLAT`, with the state definitions and transition triggers as specified in v1 §8.2. No changes to the state machine logic itself — only the sizing and cooldown numbers below.

**Cooldown default:** 1–3 trading days after KILL (unchanged), **plus a new cap:** `max_kills_per_symbol_per_month: 4` (configurable) — controls turnover/cost drag from repeated arm/kill cycles in choppy markets. Track via the "number of kills" metric already required in §14.7.

---

## 9. Strategy 1: Stock-to-ETF residual grid + breakout continuation

**Phase 1b scope: long-only.** Short-side logic below is fully specified for Phase 1c but is not built until Phase 1c.

### 9.2 Entry gates — MVP defaults (RESOLVED)

Long residual setup:
```
corr_60 >= 0.65
beta positive and stable
residual_z <= -1.4
price near demand/support/lower range
no clean structure breakdown
ETF not in panic breakdown
regime not PANIC_SELL or VOL_EXPANSION
no earnings/event/news block
spread/costs acceptable
```
Short residual setup (Phase 1c): same structure, `corr_60 >= 0.70`, `residual_z >= +1.4`.

### 9.3 Grid levels in z-score

Unchanged: 4 levels at z = -1.4 / -1.7 / -2.0 / -2.2 (long) mirrored for short, 25% size each, level 4 optional and structure-gated.

### 9.4–9.7

Unchanged from v1 (beta-neutral and dollar-neutral sizing modes both backtested; TP1/TP2/TP3 at z = ±0.8/±0.4/0; hard exit at `abs(z) >= 2.8` — resolved from the 2.7–3.0 range — worsening, structure failure, ETF panic, `corr_60 < 0.55`, beta instability, time stop **5 trading days** (resolved from 3–7 range), high-impact news, max loss exceeded).

### 9.7 Breakout continuation

Deferred to Phase 1c (§0.2). Logic unchanged from v1 once built.

---

## 10. Strategy 2: Stock-to-stock spread grid + breakout continuation

**Phase 1c only** — this strategy requires short legs on both sides by construction (long A / short B or the reverse), so it cannot be meaningfully tested long-only. Fully specified here for when Phase 1c begins.

Entry gates (MVP defaults, resolved): `corr_60 >= 0.75`, `corr_90 >= 0.65`, beta stable, both legs liquid, neither leg has near-term earnings, no high-impact news on either leg, spread has mean-reverted historically, z-score between entry and extreme zone.

Grid levels, TP structure, and stops otherwise unchanged from v1 §10.3–§10.6, with the same range-to-default resolution pattern as §9 (`z_stop` default **3.0**, resolved from 2.8–3.2; `corr_60` kill threshold **0.55**, resolved from 0.55–0.60).

---

## 11. Strategy 3: Natural long grid + breakout continuation

Long-only by construction — in scope from Phase 1b.

### 11.2 Entry gates — MVP defaults (RESOLVED)

```
price within lower 35% of detected range     # was 30-40%
price near demand/support zone
ADX_14 < 23  OR  range_quality_score high
ATR not expanding sharply
no clean breakdown below demand
SPY/QQQ/sector ETF not in panic selloff
no earnings/news block
range_width >= 3 * ATR_14
expected grid step > costs * safety_multiple
```

### 11.3–11.6

Grid construction, profit-taking, and stops unchanged from v1, with `grid_step = max(0.55 * ATR_14, min_step_after_costs)` (resolved from the 0.45–0.65 range) and hard stop at close below `range_low` by **0.5 ATR** (resolved from 0.4–0.6), two consecutive closes below demand, ATR expansion > **1.5x** median (resolved from 1.4–1.6x).

Breakout continuation (§11.6) is deferred to Phase 1c along with the shared breakout module (§15), same as Strategy 1.

---

## 12. Liquidity sweep reversal as entry enhancer

Unchanged from v1: optional sizing multiplier (0.5x / 1.0x / 1.25–1.5x based on sweep/reclaim confirmation), not mandatory for any trade. In scope starting Phase 1c alongside the breakout module, since it shares the same confirmation infrastructure.

---

## 13. Position sizing and risk management

### 13.1 Risk-first sizing — grid-aware fix (RESOLVED)

v1 left an unresolved conflict between "size from max acceptable loss" (risk-first) and "25/25/25/25% of a layer_size" (grid layering). The fix: **size the first layer from the worst-case fully-loaded grid, not from a single layer.**

```
worst_case_notional = sum(layer_notional for all layers up to max_layers)
worst_case_loss_at_kill = worst_case_notional * expected_adverse_move_to_kill_z
layer_1_size = solve for layer size such that:
    worst_case_loss_at_kill <= max_risk_per_trade_pct * starting_capital_usd
```
This means `layer_1_size` is smaller than it would be if sized against itself alone — by design, since a grid that adds on adverse moves must budget for all layers being filled before the kill triggers.

Defaults: `max_risk_per_trade_pct: 1.0%`, `max_daily_loss_pct: 2.5%`, `max_weekly_loss_pct: 6%`, `max_gross_leverage: 6.0`, `max_effective_leverage_start: 2.0` (Phase 1b/1c starting point — test 1x/2x/3x/4x/6x per §14.9), `max_open_positions: 4`, all against `starting_capital_usd: 100000` (§2.3).

### 13.2–13.4

Unchanged from v1: gross/net/beta-adjusted exposure tracking for pairs (never treat a hedged pair as risk-free); natural long grid capped at lower leverage (2–4x tested, 6x only as stress test); both equal (25/25/25/25) and front-light (20/25/25/30) layer sizing tested; no martingale sizing.

---

## 14. Backtest engine requirements

### 14.1–14.2

Unchanged: event-driven, chronological, no-lookahead on beta/z-score/structure/news/breakout confirmation.

### 14.3 Intraday fill modeling — ambiguity resolved

v1 left the same-bar stop+TP case as an "or" choice between two options. **Resolved default: assume the adverse outcome first** (stop fills before TP) whenever both are touched in the same bar. Run the alternative (TP-first) as an explicit sensitivity variant in §14.9, not as a developer's coin-flip during implementation.

### 14.4–14.6

Unchanged: costs/slippage applied on every fill per the §2.3 formulas; adjusted data used throughout (§2.1.1) and logged as such; never mix adjusted/unadjusted between legs.

### 14.7 Required metrics — baseline comparison added (RESOLVED)

All metrics from v1 unchanged (total/annualized return, max drawdown, profit factor, win rate, expectancy in R, Sharpe/Sortino, holding time, turnover, exposure, kill count, breakout/mean-reversion success rate, cost drag, slippage sensitivity, best/worst 5 trades), **plus, mandatory for every report:**

- Buy-and-hold return of the underlying stock over the same window.
- Static SPY return over the same window.
- A naive 2-level mean-reversion baseline (single entry at z_entry, single exit at z=0, no grid, no breakout) on the same universe.

A strategy is only reported as having found edge if it beats all three baselines net of costs. If it doesn't, the report says so plainly rather than only presenting the strategy's own numbers in isolation.

### 14.8–14.9

Walk-forward (6m train / 1m test rolling monthly, plus 3m/1m and 12m/1m variants) and parameter sensitivity grids — unchanged, and this is now explicitly where all the ranges resolved to single defaults elsewhere in this document live:

```
correlation threshold: 0.60, 0.65, 0.70, 0.75, 0.80
z_entry: 1.2, 1.4, 1.6, 1.8
z_add_step: 0.25, 0.30, 0.40
z_stop: 2.5, 2.7, 3.0, 3.2
z_exit: 0.0, 0.3, 0.5, 0.8
ATR grid step: 0.45, 0.55, 0.65
max holding days: 3, 5, 7, 10
leverage: 1x, 2x, 3x, 4x, 6x
same-bar stop/TP resolution: adverse-first (default) vs TP-first (variant)
```
Deferred to Phase 1c (requires the full backtest engine and, for meaningful walk-forward, intraday data).

---

## 15. Breakout continuation engine

Unchanged from v1 (§15.1–15.4: breakout types, confirmation score, conversion rules per strategy, failed-breakout handling). In scope from Phase 1c.

---

## 16. Initial AI agents for research phase

### 16.0 Invocation frequency and caching (NEW — resolves a real cost/latency problem)

v1 never specified how often these agents run. Naively calling an LLM once per bar, across years of 5-minute bars and dozens of symbols, is not viable even on local infrastructure. **Rule: agents run once per discrete event, never once per bar.**

- Data Quality Agent: once per symbol per data pull (not per bar).
- Event/News Agent: once per news item / once per earnings date, not continuously.
- Regime Agent: once per symbol-day (or once per market-wide regime check per day), not per bar.
- Strategy Reviewer / Post-Trade Analyst: once per candidate setup / once per closed trade — these are naturally event-scoped already.

All outputs are cached (e.g. a local table keyed by symbol + date) and reused by the backtest loop rather than recomputed. In scope starting Phase 1c.

### 16.1–16.5

Agent purposes and output schemas (Data Quality, Event/News, Regime, Strategy Reviewer, Post-Trade Analyst) unchanged from v1.

---

## 17. Scoring model

Unchanged from v1: 0–100 candidate scores with the weighting given in v1 §17.1–17.2 (correlation/beta 20, mean-reversion history 20, z-opportunity 15, structure 15, event/news safety 15, liquidity/costs 10, regime 5 for residual candidates). `candidate_score >= 70` required to trade.

---

## 18. Project structure

Unchanged from v1 — same `residual_grid_research/` layout (config/, data/, src/{data,features,strategies,risk,backtest,agents,reports}/, notebooks/, outputs/, tests/). Confirmed standalone per §1.1.

---

## 19. Acceptance criteria — revised for phased scope (RESOLVED)

**Phase 1a complete when:** daily adjusted data loads for the §20 universe; rolling beta/correlation/residual/z-score compute correctly with no lookahead; §4.5 diagnostics run and produce a clear go/no-go read on mean-reversion structure.

**Phase 1b complete when:** the backtest engine runs Strategy 1 (long-only) and Strategy 3 on daily bars with realistic costs; earnings/event no-trade flags apply from deterministic date data; trade logs and a Markdown report are produced, including the mandatory baseline comparison (§14.7) and the blind-expansion selection-bias check (§3.3).

**Phase 1c complete when:** all of v1's original acceptance criteria are met — intraday data, all three strategies including short legs, breakout continuation, AI agents with the §16.0 invocation rule, costs/slippage, walk-forward, and the full comparison table.

---

## 20. First research experiments

Unchanged from v1 — same residual ETF candidates, stock-stock pairs, and natural-long-grid screening approach (§20.1–20.3). Use these for Phase 1a/1b; use the blind-expansion set (§3.3) as a second pass, not a replacement.

---

## 21. Report format

All 17 items from v1 unchanged, **plus:**

18. Baseline/benchmark comparison (buy-and-hold, SPY, naive 2-level mean reversion) — mandatory, per §14.7.
19. Selection-bias check: performance on the curated §20 list vs. the blind sector-mapped expansion (§3.3).

---

## 22. Special cautions

All 10 items from v1 unchanged, **plus:**

11. Do not size grid layers independently of the full-stack exposure at the kill z-score (§13.1).
12. Do not call AI agents inside the per-bar backtest loop — event-level only, cached (§16.0).
13. Do not report "edge found" without the mandatory baseline comparison beating costs (§14.7).
14. Do not treat the curated pair/ETF list (§20) as sufficient evidence against selection bias on its own — run the blind expansion check (§3.3) before drawing conclusions.
15. Do not integrate this codebase into any other existing trading system or share its runtime/database with one (§1.1).
16. Do not backtest short-leg P&L as if borrow cost were fully modeled — it isn't (§2.2); flag it in every short-leg report.

---

## 23. Expected final deliverables from developer

Unchanged from v1 (research repository, config-driven parameters, data pipeline, residual/spread modules, three strategy modules, shared state machine, shared risk/kill-switch module, shared breakout module, event-driven backtester, walk-forward engine, Markdown report generator, unit tests for no-lookahead and state transitions, initial backtest reports) — delivered across the phases in §0.2 rather than all at once.

---

## 24. Plain-English summary of desired behavior

Unchanged from v1 — the twelve-point behavior summary (scan → check relationship is real → check structure → check news/regime → arm only at a real opportunity zone → add only at predefined levels → take profit gradually → stop adding under pressure → kill immediately on invalidation → convert to continuation on confirmed breakout → record every decision → prove edge before any exchange integration) still describes the target system correctly. This document only changes *how* and *in what order* that system gets built and confirmed.

---

## 25. Developer implementation priority — revised to match the phased plan

1. **Phase 1a:** Alpha Vantage data loader (daily, adjusted) → residual/spread calculator → mean-reversion diagnostics (§4.5). Stop here and review before continuing.
2. **Phase 1b:** Candidate scanner/scoring → state machine → backtest engine (daily, long-only) → Strategy 1 (long-only) and Strategy 3 → deterministic news/event/regime filters (no AI yet) → baseline comparison → selection-bias check.
3. **Phase 1c:** Switch data pipeline to intraday (5-min, month-sliced Alpha Vantage) → add short legs to Strategy 1 → Strategy 2 (pairs) → breakout continuation module → liquidity sweep enhancer → AI agents (with §16.0 invocation rule) → walk-forward and sensitivity engine → full reports/dashboards.

Do not build Bybit/MEXC execution until Phase 1c shows durable edge, and do not integrate this codebase into any other existing system at any phase (§1.1).

---

## 26. Resolved decisions log (replaces v1's "final check before coding")

v1 ended with seven open questions. They're resolved here so the developer isn't blocked:

1. **Historical intraday data source:** Alpha Vantage, Standard plan ($49.99/mo), already connected. Backup/cross-check: Polygon.io Starter (~$29/mo, reconfirm current pricing before committing). See §0.1.
2. **Starting universe:** the §20 curated list for Phase 1a/1b; blind sector-mapped expansion added in Phase 1c to check for selection bias (§3.3).
3. **Short legs:** not simulated in Phase 1a/1b (long-only). Simulated in Phase 1c for Strategy 1 and Strategy 2, with borrow cost explicitly flagged as an unmodeled risk (§2.2).
4. **Capital and leverage:** `starting_capital_usd: 100000` default; leverage tested at 1x/2x/3x/4x/6x (§13.1, §14.9), with 2x as the Phase 1b/1c working default.
5. **Cost/slippage defaults:** as specified in §2.3, sensitivity-tested per §14.9.
6. **Macro calendar:** out of scope for Phase 1 entirely; revisit in Phase 2.
7. **Report format:** Markdown, matching §21. Convert to HTML only if requested later — no dual-format requirement for Phase 1.
