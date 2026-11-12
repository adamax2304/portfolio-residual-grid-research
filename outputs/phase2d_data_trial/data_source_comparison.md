# Phase 2D-R0 — Free/cheap data source comparison

## Result

HF Data Library is the cheapest plausible **R-LITE** price source because its public catalog covers all 25 frozen symbols and its key is free. It does not qualify for full Phase 2D: prices are adjusted, the post-March-2022 segment is IEX-only, and no extended-hours data exists. Previously authenticated candle files were loaded from the local cache; no key was persisted.

| source | role | cost | coverage | raw_execution | events | limitations | classification |
|---|---|---|---|---|---|---|---|
| HF Data Library | intraday bars | FREE key | 25/25 catalog; bars cached | NO (adjusted bars) | NO | Post-Mar-2022 IEX-only (~2-3% consolidated volume); adjusted; RTH only; survivorship-biased universe | LIMITED |
| MarketParquet local | local Parquet bars | $79 one-time archive if purchased | local 5m files=0, local 15m files=0 | NO (split-adjusted) | NO | No local archive configured; 15m may require deterministic 5m resample | FAIL |
| HistoricalData.net free sample | format/adapter sample | FREE sample; full 1m archive $699 one-time | 2/25, Jul-Dec 2022 only | YES in sample | dividend/split columns | Only KO and SPY from frozen universe; ~6 months; cannot validate pairs/universe | FAIL |
| EarningsAPI free | earnings dates | FREE 100/day, 1000/month | not queried; key absent | N/A | earnings only | Free history most recent 24 months; not guaranteed point-in-time; no dividends/splits | FAIL |
| EODHD free events | dividends/splits | FREE 20/day | not queried; key absent | N/A | dividends/splits | Free history limited to past year; 25-symbol backfill exceeds one-day free quota | FAIL |

## Cheapest usable path

1. Use the free HF Data Library key only through the `HFDL_API_KEY` environment variable; never commit it.
2. Require 25/25 symbols, both 5m and 15m, at least two years per symbol, valid calendar-aware RTH timestamps, and >=80% bar density.
3. Use HF only for `Phase 2D-R-LITE`; never call it raw-price independent validation.
4. For a stronger low-cost archive, MarketParquet is listed at $79 one-time, but remains split-adjusted. HistoricalData.net's full stock minute archive is $699 one-time and includes raw plus adjusted values.
5. EarningsAPI free can supply up to the most recent 24 months of earnings after a free key is configured; EODHD free supplies only about one year of dividend/split history.

No strategy parameters or frozen-engine module changed. All R0 source additions are classified `DATA_ADAPTER_ONLY`, `REPORTING_ONLY`, or `TEST_ONLY`.
