from __future__ import annotations

import numpy as np
import pandas as pd


LEGACY_INTRADAY_BASIS = "legacy_intraday_20_bar"
PRIOR_DAILY_BASIS = "prior_daily_sessions"


def prior_session_average_daily_dollar_volume(
    frame: pd.DataFrame,
    *,
    window_sessions: int = 20,
    timezone: str = "America/New_York",
) -> pd.Series:
    """Return lagged average daily dollar volume aligned to intraday bars.

    The daily observation is final session close times summed session volume.
    The rolling mean is shifted by one complete session before it is mapped
    back to intraday bars, so no current-session information can enter the
    current-session liquidity decision.

    A session with missing, non-finite, or negative volume fails closed and
    contributes ``NaN``. Early closes are handled as complete shorter sessions;
    their volume is never scaled to a hypothetical full day.
    """

    if window_sessions < 1:
        raise ValueError("window_sessions must be positive")
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError("frame index must be a DatetimeIndex")
    missing = {"close", "volume"}.difference(frame.columns)
    if missing:
        raise ValueError(f"frame missing required columns: {sorted(missing)}")
    if frame.empty:
        return pd.Series(index=frame.index, dtype=float, name=f"adv_dollar_{window_sessions}")

    ordered = frame.sort_index()
    index = ordered.index
    local_index = index.tz_localize(timezone) if index.tz is None else index.tz_convert(timezone)
    sessions = pd.Series(local_index.normalize(), index=index, name="session")
    working = pd.DataFrame(
        {
            "session": sessions,
            "close": pd.to_numeric(ordered["close"], errors="coerce"),
            "volume": pd.to_numeric(ordered["volume"], errors="coerce"),
        },
        index=index,
    )

    def valid_daily_volume(values: pd.Series) -> float:
        numeric = pd.to_numeric(values, errors="coerce")
        array = numeric.to_numpy(dtype=float)
        if numeric.isna().any() or not np.isfinite(array).all() or (numeric < 0).any():
            return float("nan")
        return float(numeric.sum())

    daily_close = working.groupby("session", sort=True)["close"].last()
    daily_volume = working.groupby("session", sort=True)["volume"].agg(valid_daily_volume)
    daily_dollar_volume = daily_close * daily_volume
    lagged_adv = daily_dollar_volume.rolling(
        window_sessions,
        min_periods=window_sessions,
    ).mean().shift(1)
    aligned = sessions.map(lagged_adv)
    aligned.index = index
    aligned.name = f"adv_dollar_{window_sessions}"
    return aligned.reindex(frame.index)


def liquidity_series(frame: pd.DataFrame, config: dict) -> pd.Series:
    """Compute the configured liquidity measure while preserving old configs."""

    features = config.get("features", {})
    basis = str(features.get("liquidity_basis", LEGACY_INTRADAY_BASIS))
    if basis == PRIOR_DAILY_BASIS:
        return prior_session_average_daily_dollar_volume(
            frame,
            window_sessions=int(features.get("liquidity_adv_window_sessions", 20)),
            timezone=str(config.get("project", {}).get("timezone", "America/New_York")),
        )
    if basis != LEGACY_INTRADAY_BASIS:
        raise ValueError(f"Unsupported liquidity_basis: {basis}")
    result = (frame["close"] * frame["volume"]).shift(1).rolling(20, min_periods=20).mean()
    result.name = "dollar_volume_20"
    return result
