from __future__ import annotations

from enum import Enum

import pandas as pd

from .technical import add_technical_features


class MarketRegime(str, Enum):
    RANGE_OK = "RANGE_OK"
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    PANIC_SELL = "PANIC_SELL"
    VOL_EXPANSION = "VOL_EXPANSION"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"
    EVENT_RISK = "EVENT_RISK"
    UNKNOWN = "UNKNOWN"


def classify_regime(
    market: pd.DataFrame,
    *,
    market_adx_max: float = 25,
    atr_expansion_max: float = 1.5,
) -> pd.Series:
    features = add_technical_features(market)

    def classify(row: pd.Series) -> str:
        if row[["adx_14", "atr_ratio", "return_20"]].isna().any():
            return MarketRegime.UNKNOWN.value
        if row["return_20"] <= -0.12 and row["atr_ratio"] > atr_expansion_max:
            return MarketRegime.PANIC_SELL.value
        if row["atr_ratio"] > atr_expansion_max:
            return MarketRegime.VOL_EXPANSION.value
        if row["adx_14"] < market_adx_max:
            return MarketRegime.RANGE_OK.value
        return MarketRegime.TREND_UP.value if row["return_20"] >= 0 else MarketRegime.TREND_DOWN.value

    return features.apply(classify, axis=1).rename("regime")


def regime_allows_grid(regime: str | MarketRegime) -> bool:
    value = regime.value if isinstance(regime, MarketRegime) else str(regime)
    return value not in {
        MarketRegime.PANIC_SELL.value,
        MarketRegime.VOL_EXPANSION.value,
        MarketRegime.EVENT_RISK.value,
        MarketRegime.UNKNOWN.value,
    }

