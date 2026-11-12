from __future__ import annotations

import math
from typing import Any, Iterable

import numpy as np
import pandas as pd


def _close_series(value: pd.DataFrame | pd.Series, name: str) -> pd.Series:
    series = value["close"] if isinstance(value, pd.DataFrame) else value
    result = pd.to_numeric(series, errors="coerce").rename(name)
    if (result.dropna() <= 0).any():
        raise ValueError(f"{name} contains non-positive prices; log relationship is undefined")
    return result


def rolling_relationship(
    asset_a: pd.DataFrame | pd.Series,
    asset_b: pd.DataFrame | pd.Series,
    *,
    beta_window: int = 60,
    z_window: int = 90,
    correlation_windows: Iterable[int] = (30, 60, 90, 120),
) -> pd.DataFrame:
    """Rolling OLS and residual z-score with parameters based strictly on prior bars.

    The current close is evaluated against alpha/beta and residual moments fitted
    through t-1. Orders generated from row t are therefore safe to execute at t+1.
    """
    a = _close_series(asset_a, "price_a")
    b = _close_series(asset_b, "price_b")
    aligned = pd.concat([a, b], axis=1, join="inner").dropna().sort_index()
    log_a = np.log(aligned["price_a"])
    log_b = np.log(aligned["price_b"])
    lag_a = log_a.shift(1)
    lag_b = log_b.shift(1)
    min_periods = beta_window
    mean_a = lag_a.rolling(beta_window, min_periods=min_periods).mean()
    mean_b = lag_b.rolling(beta_window, min_periods=min_periods).mean()
    covariance = lag_a.rolling(beta_window, min_periods=min_periods).cov(lag_b)
    variance = lag_b.rolling(beta_window, min_periods=min_periods).var(ddof=1)
    beta = covariance / variance.replace(0, np.nan)
    alpha = mean_a - beta * mean_b
    fitted_residual = log_a - alpha - beta * log_b
    residual_mean = fitted_residual.shift(1).rolling(z_window, min_periods=z_window).mean()
    residual_std = fitted_residual.shift(1).rolling(z_window, min_periods=z_window).std(ddof=1)
    result = aligned.copy()
    result["log_a"] = log_a
    result["log_b"] = log_b
    result["alpha"] = alpha
    result["beta"] = beta
    result["residual"] = fitted_residual
    result["residual_mean"] = residual_mean
    result["residual_std"] = residual_std
    result["z"] = (fitted_residual - residual_mean) / residual_std.replace(0, np.nan)
    result["r2"] = lag_a.rolling(beta_window, min_periods=min_periods).corr(lag_b).pow(2)
    beta_mean_abs = beta.shift(1).rolling(beta_window, min_periods=max(10, beta_window // 2)).mean().abs()
    result["beta_stability"] = (
        beta.shift(1).rolling(beta_window, min_periods=max(10, beta_window // 2)).std(ddof=1)
        / beta_mean_abs.replace(0, np.nan)
    )
    returns_a = aligned["price_a"].pct_change().shift(1)
    returns_b = aligned["price_b"].pct_change().shift(1)
    for window in correlation_windows:
        result[f"corr_{window}"] = returns_a.rolling(window, min_periods=window).corr(returns_b)
    return result.replace([np.inf, -np.inf], np.nan)


def _half_life(series: pd.Series) -> float | None:
    values = series.dropna().astype(float)
    if len(values) < 30:
        return None
    lagged = values.shift(1).dropna()
    delta = values.diff().dropna()
    lagged, delta = lagged.align(delta, join="inner")
    design = np.column_stack([np.ones(len(lagged)), lagged.to_numpy()])
    intercept, slope = np.linalg.lstsq(design, delta.to_numpy(), rcond=None)[0]
    _ = intercept
    if slope >= 0:
        return None
    value = -math.log(2) / slope
    return float(value) if np.isfinite(value) else None


def _reversion_durations(z: pd.Series, entry_z: float) -> list[int]:
    values = z.dropna()
    durations: list[int] = []
    active_sign = 0
    start_position = 0
    for position, value in enumerate(values):
        if active_sign == 0 and abs(value) >= entry_z:
            active_sign = 1 if value > 0 else -1
            start_position = position
        elif active_sign and (value * active_sign <= 0 or abs(value) <= 0.1):
            durations.append(position - start_position)
            active_sign = 0
    return durations


def _max_adverse_excursion(z: pd.Series, entry_z: float) -> float | None:
    values = z.dropna()
    active_sign = 0
    worst = 0.0
    for value in values:
        if active_sign == 0 and abs(value) >= entry_z:
            active_sign = 1 if value > 0 else -1
            worst = max(worst, abs(float(value)) - entry_z)
        elif active_sign:
            if value * active_sign <= 0 or abs(value) <= 0.1:
                active_sign = 0
            else:
                worst = max(worst, float(value) * active_sign - entry_z)
    return float(worst) if len(values) else None


def _adf(series: pd.Series) -> dict[str, float | None]:
    try:
        from statsmodels.tsa.stattools import adfuller
    except ImportError:
        return {"adf_statistic": None, "adf_pvalue": None}
    values = series.dropna()
    if len(values) < 30:
        return {"adf_statistic": None, "adf_pvalue": None}
    statistic, pvalue, *_ = adfuller(values, autolag="AIC")
    return {"adf_statistic": float(statistic), "adf_pvalue": float(pvalue)}


def mean_reversion_diagnostics(
    relationship: pd.DataFrame,
    *,
    entry_z: float = 1.4,
    kill_z: float = 2.8,
    include_adf: bool = True,
) -> dict[str, Any]:
    z = relationship["z"].dropna()
    residual = relationship["residual"].dropna()
    durations = _reversion_durations(z, entry_z)
    entry_crossings = ((z.abs() >= entry_z) & (z.abs().shift(1) < entry_z)).sum()
    kill_crossings = ((z.abs() >= kill_z) & (z.abs().shift(1) < kill_z)).sum()
    quantiles = z.quantile([0.01, 0.05, 0.5, 0.95, 0.99]) if len(z) else pd.Series(dtype=float)
    result: dict[str, Any] = {
        "observations": int(len(z)),
        "z_mean": float(z.mean()) if len(z) else None,
        "z_std": float(z.std(ddof=1)) if len(z) > 1 else None,
        "z_skew": float(z.skew()) if len(z) > 2 else None,
        "z_kurtosis": float(z.kurt()) if len(z) > 3 else None,
        "z_quantiles": {str(index): float(value) for index, value in quantiles.items()},
        "half_life_bars": _half_life(residual),
        "entry_crossings": int(entry_crossings),
        "crossings_per_year": float(entry_crossings / max(1, len(z)) * 252),
        "median_bars_to_reversion": float(np.median(durations)) if durations else None,
        "completed_reversions": len(durations),
        "failure_rate_beyond_kill": float(kill_crossings / entry_crossings) if entry_crossings else None,
        "max_abs_z": float(z.abs().max()) if len(z) else None,
        "max_adverse_excursion_z": _max_adverse_excursion(z, entry_z),
        "latest_corr_60": _last_finite(relationship.get("corr_60")),
        "latest_beta": _last_finite(relationship.get("beta")),
        "latest_beta_stability": _last_finite(relationship.get("beta_stability")),
    }
    result.update(_adf(residual) if include_adf else {"adf_statistic": None, "adf_pvalue": None})
    result["go_no_go"] = diagnostic_verdict(result)
    return result


def _last_finite(series: pd.Series | None) -> float | None:
    if series is None:
        return None
    clean = series.replace([np.inf, -np.inf], np.nan).dropna()
    return float(clean.iloc[-1]) if len(clean) else None


def diagnostic_verdict(metrics: dict[str, Any]) -> str:
    half_life = metrics.get("half_life_bars")
    failures = metrics.get("failure_rate_beyond_kill")
    crossings = metrics.get("crossings_per_year") or 0
    corr = metrics.get("latest_corr_60")
    structural_passes = [
        half_life is not None and 1 <= half_life <= 30,
        failures is not None and failures <= 0.35,
        crossings >= 4,
    ]
    correlation_passes = corr is not None and corr >= 0.60
    if correlation_passes and sum(structural_passes) >= 2:
        return "GO: relationship shows testable mean-reversion structure"
    if correlation_passes or sum(structural_passes) >= 2:
        return "REVIEW: mixed evidence; continue only with conservative validation"
    return "NO-GO: insufficient mean-reversion structure under MVP diagnostics"
