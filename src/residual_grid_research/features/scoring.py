from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class CandidateScore:
    total: float
    relationship: float
    mean_reversion: float
    opportunity: float
    structure: float
    event_safety: float
    liquidity_costs: float
    regime: float
    passed: bool


def _scale(value: float, poor: float, good: float) -> float:
    if not np.isfinite(value):
        return 0.0
    if good == poor:
        return float(value >= good)
    return float(np.clip((value - poor) / (good - poor), 0, 1))


def score_candidate(
    *,
    correlation: float,
    beta_stability: float,
    half_life_bars: float | None,
    crossings_per_year: float,
    z_abs: float,
    near_structure: bool,
    event_safe: bool,
    liquidity_ok: bool,
    costs_ok: bool,
    regime_ok: bool,
    threshold: float = 70,
) -> CandidateScore:
    corr_part = _scale(correlation, 0.50, 0.85)
    stability_part = 1 - _scale(beta_stability, 0.10, 0.50)
    relationship = 20 * (0.7 * corr_part + 0.3 * stability_part)
    if half_life_bars is None:
        half_life_score = 0.0
    elif 1 <= half_life_bars <= 20:
        half_life_score = 1.0
    else:
        half_life_score = max(0.0, 1 - abs(half_life_bars - 10) / 50)
    mean_reversion = 20 * (0.6 * half_life_score + 0.4 * _scale(crossings_per_year, 2, 12))
    opportunity = 15 * _scale(z_abs, 1.0, 2.2)
    structure = 15.0 if near_structure else 0.0
    event_safety = 15.0 if event_safe else 0.0
    liquidity_costs = 10.0 if liquidity_ok and costs_ok else 0.0
    regime = 5.0 if regime_ok else 0.0
    total = relationship + mean_reversion + opportunity + structure + event_safety + liquidity_costs + regime
    return CandidateScore(
        total=round(total, 4),
        relationship=relationship,
        mean_reversion=mean_reversion,
        opportunity=opportunity,
        structure=structure,
        event_safety=event_safety,
        liquidity_costs=liquidity_costs,
        regime=regime,
        passed=total >= threshold,
    )

