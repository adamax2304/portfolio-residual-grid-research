# Intraday fill-model audit

MECHANICAL TEST STATUS: **PASS**

Raw unprefixed OHLC is reserved for fills; adjusted-prefixed OHLC is selected only by feature code. Signals queue after close and market orders execute next bar. Limits require a real high/low touch, gap-through stops use the next available price, and same-candle conflicts are adverse-first.

The requested daily/15m/5m market comparison was **not run** because the independent-data gate failed. The CSV row is labelled deterministic synthetic only and is not evidence of strategy performance.
