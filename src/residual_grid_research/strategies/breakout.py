from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True, slots=True)
class BreakoutAssessment:
    direction: int
    score: float
    confirmed: bool
    failed: bool
    reasons: tuple[str, ...]


class BreakoutEngine:
    """Shared, deterministic breakout confirmation and failure logic."""

    def __init__(self, config: dict) -> None:
        self.config = config["strategy"]["breakout"]

    def assess(
        self,
        history: pd.DataFrame,
        *,
        range_high: float,
        range_low: float,
        atr: float,
    ) -> BreakoutAssessment:
        mode = str(self.config.get("confirmation_mode", "closes"))
        required_closes = 1 if mode == "one_close" else 2 if mode in {"two_closes", "closes"} else 1
        required_closes = int(self.config.get("confirmation_closes", required_closes)) if mode == "closes" else required_closes
        needed = max(3, required_closes + (1 if mode == "retest" else 0))
        if len(history) < needed or any(pd.isna(v) for v in (range_high, range_low, atr)):
            return BreakoutAssessment(0, 0.0, False, False, ("insufficient history",))
        recent = history.iloc[-needed:]
        latest = recent.iloc[-1]
        buffer = float(self.config["atr_buffer"]) * atr
        up = latest["close"] > range_high + buffer
        down = latest["close"] < range_low - buffer
        direction = 1 if up else -1 if down else 0
        if direction == 0:
            return BreakoutAssessment(0, 0.0, False, False, ("price inside range",))
        level = range_high if direction > 0 else range_low
        confirming = recent["close"].tail(required_closes)
        closes = int((confirming > level).sum()) if direction > 0 else int((confirming < level).sum())
        consecutive_closes = closes == required_closes
        price_points = 30.0
        close_points = 25.0 if consecutive_closes else 0.0
        retest_ok = True
        if mode == "retest":
            prior = recent.iloc[-2]
            if direction > 0:
                retest_ok = bool(prior["close"] > level and latest["low"] <= level + buffer and latest["close"] > level)
            else:
                retest_ok = bool(prior["close"] < level and latest["high"] >= level - buffer and latest["close"] < level)
            close_points = 25.0 if retest_ok else 0.0
        volume_points = 20.0 if float(latest.get("volume_ratio", 0)) >= float(self.config["volume_ratio"]) else 0.0
        adx_points = 15.0 if float(latest.get("adx_14", 0)) >= 23 else 0.0
        body = abs(float(latest["close"]) - float(latest["open"]))
        range_size = max(1e-12, float(latest["high"]) - float(latest["low"]))
        quality_points = 10.0 if body / range_size >= 0.5 else 0.0
        score = price_points + close_points + volume_points + adx_points + quality_points
        reasons = (
            f"direction={direction}",
            f"confirming_closes={closes}",
            f"volume_ratio={float(latest.get('volume_ratio', 0)):.2f}",
            f"adx={float(latest.get('adx_14', 0)):.2f}",
        )
        return BreakoutAssessment(
            direction,
            score,
            score >= float(self.config["minimum_score"]) and retest_ok and consecutive_closes,
            False,
            reasons,
        )

    def failed(self, history: pd.DataFrame, direction: int, level: float) -> bool:
        bars = int(self.config["failed_breakout_bars"])
        if direction == 0 or len(history) < bars:
            return False
        recent = history["close"].iloc[-bars:]
        return bool((recent < level).any()) if direction > 0 else bool((recent > level).any())
