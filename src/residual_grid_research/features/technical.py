from __future__ import annotations

import numpy as np
import pandas as pd


def true_range(frame: pd.DataFrame) -> pd.Series:
    previous_close = frame["close"].shift(1)
    return pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    return true_range(frame).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def adx(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    up = frame["high"].diff()
    down = -frame["low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=frame.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=frame.index)
    average_range = atr(frame, period).replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / average_range
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False, min_periods=period).mean() / average_range
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def fractal_pivots(frame: pd.DataFrame, window: int = 5) -> tuple[pd.Series, pd.Series]:
    width = 2 * window + 1
    pivot_high = frame["high"].eq(frame["high"].rolling(width, center=True).max())
    pivot_low = frame["low"].eq(frame["low"].rolling(width, center=True).min())
    # A centered pivot is not knowable until `window` bars later.
    return pivot_high.shift(window, fill_value=False), pivot_low.shift(window, fill_value=False)


def add_technical_features(
    frame: pd.DataFrame,
    *,
    atr_period: int = 14,
    pivot_window: int = 5,
    range_lookback: int = 60,
) -> pd.DataFrame:
    result = frame.copy().sort_index()
    result["atr_14"] = atr(result, atr_period)
    result["adx_14"] = adx(result, atr_period)
    result["atr_20_median"] = result["atr_14"].shift(1).rolling(20, min_periods=10).median()
    result["atr_ratio"] = result["atr_14"] / result["atr_20_median"].replace(0, np.nan)
    result["range_high"] = result["high"].shift(1).rolling(range_lookback, min_periods=range_lookback).max()
    result["range_low"] = result["low"].shift(1).rolling(range_lookback, min_periods=range_lookback).min()
    result["range_width"] = result["range_high"] - result["range_low"]
    result["range_width_atr"] = result["range_width"] / result["atr_14"].replace(0, np.nan)
    result["range_position"] = (
        (result["close"] - result["range_low"]) / result["range_width"].replace(0, np.nan)
    )
    pivot_high, pivot_low = fractal_pivots(result, pivot_window)
    result["pivot_high"] = pivot_high
    result["pivot_low"] = pivot_low
    result["volume_median_20"] = result["volume"].shift(1).rolling(20, min_periods=10).median()
    result["volume_ratio"] = result["volume"] / result["volume_median_20"].replace(0, np.nan)
    result["return_20"] = result["close"].pct_change(20)
    result = add_liquidity_sweep_features(result)
    return result.replace([np.inf, -np.inf], np.nan)


def add_liquidity_sweep_features(frame: pd.DataFrame, *, reclaim_bars: int = 3) -> pd.DataFrame:
    """Add causal candle-only sweep/reclaim approximations.

    A sweep candle must take a previously-known 60-bar boundary and show either
    elevated volume or true-range expansion.  A reclaim is emitted only on a
    later candle (one through ``reclaim_bars`` bars afterward), so a strategy
    can never enter on the sweep candle itself.
    """
    result = frame.copy()
    if "range_low" not in result or "range_high" not in result:
        return result
    candle_tr = true_range(result)
    tr_reference = candle_tr.shift(1).rolling(20, min_periods=10).median()
    participation = (
        result.get("volume_ratio", pd.Series(0.0, index=result.index)).fillna(0) >= 1.20
    ) | (candle_tr / tr_reference.replace(0, np.nan) >= 1.25)
    bullish_sweep = (result["low"] < result["range_low"]) & participation
    bearish_sweep = (result["high"] > result["range_high"]) & participation
    bullish_reclaim = pd.Series(False, index=result.index)
    bearish_reclaim = pd.Series(False, index=result.index)
    for lag in range(1, max(1, int(reclaim_bars)) + 1):
        bullish_reclaim |= bullish_sweep.shift(lag, fill_value=False) & (
            result["close"] > result["range_low"].shift(lag)
        )
        bearish_reclaim |= bearish_sweep.shift(lag, fill_value=False) & (
            result["close"] < result["range_high"].shift(lag)
        )
    result["bullish_sweep"] = bullish_sweep.fillna(False)
    result["bearish_sweep"] = bearish_sweep.fillna(False)
    result["bullish_sweep_reclaim"] = bullish_reclaim.fillna(False)
    result["bearish_sweep_reclaim"] = bearish_reclaim.fillna(False)
    result["true_range_expansion"] = (candle_tr / tr_reference.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)
    return result
