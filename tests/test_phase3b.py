from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from residual_grid_research.config import load_config
from residual_grid_research.features.liquidity import (
    LEGACY_INTRADAY_BASIS,
    PRIOR_DAILY_BASIS,
    liquidity_series,
    prior_session_average_daily_dollar_volume,
)
from residual_grid_research.models import Position, StrategyState
from residual_grid_research.phase3b import (
    _apply_variant,
    _family_status,
    _jobs,
    _stop_status,
    _validate_registry,
    variant_registry,
)
from residual_grid_research.strategies.natural_grid import NaturalLongGridStrategy


ROOT = Path(__file__).parents[1]


def _intraday_frame() -> pd.DataFrame:
    index = pd.DatetimeIndex(
        [
            "2025-01-02 09:30", "2025-01-02 09:35",
            "2025-01-03 09:30", "2025-01-03 09:35",
            "2025-01-06 09:30",
            "2025-01-07 09:30", "2025-01-07 09:35",
        ],
        tz="America/New_York",
    )
    return pd.DataFrame(
        {
            "close": [10.0, 11.0, 20.0, 21.0, 30.0, 40.0, 41.0],
            "volume": [100.0, 100.0, 200.0, 200.0, 300.0, 400.0, 400.0],
        },
        index=index,
    )


def test_daily_adv_uses_prior_completed_sessions_only_and_handles_early_close():
    frame = _intraday_frame()
    adv = prior_session_average_daily_dollar_volume(frame, window_sessions=2)
    expected_day3 = ((11.0 * 200.0) + (21.0 * 400.0)) / 2
    day3 = frame.index.normalize() == pd.Timestamp("2025-01-06", tz="America/New_York")
    assert np.allclose(adv.loc[day3], expected_day3)

    changed = frame.copy()
    changed.loc[day3, "volume"] = 999_999_999.0
    changed_adv = prior_session_average_daily_dollar_volume(changed, window_sessions=2)
    assert np.allclose(changed_adv.loc[day3], adv.loc[day3])

    expected_day4 = ((21.0 * 400.0) + (30.0 * 300.0)) / 2
    day4 = frame.index.normalize() == pd.Timestamp("2025-01-07", tz="America/New_York")
    assert np.allclose(adv.loc[day4], expected_day4)


def test_missing_daily_volume_fails_closed():
    frame = _intraday_frame()
    frame.loc[pd.Timestamp("2025-01-03 09:35", tz="America/New_York"), "volume"] = np.nan
    adv = prior_session_average_daily_dollar_volume(frame, window_sessions=2)
    day3 = frame.index.normalize() == pd.Timestamp("2025-01-06", tz="America/New_York")
    assert adv.loc[day3].isna().all()


def test_configured_liquidity_basis_does_not_compare_intraday_volume_to_daily_threshold():
    frame = _intraday_frame()
    config = load_config(ROOT / "config" / "phase3b_redesign.yaml")
    corrected = liquidity_series(frame, config)
    expected = prior_session_average_daily_dollar_volume(frame, window_sessions=20)
    pd.testing.assert_series_equal(corrected, expected)

    legacy = deepcopy(config)
    legacy["features"]["liquidity_basis"] = LEGACY_INTRADAY_BASIS
    legacy_result = liquidity_series(frame, legacy)
    expected_legacy = (frame["close"] * frame["volume"]).shift(1).rolling(20, min_periods=20).mean()
    pd.testing.assert_series_equal(legacy_result, expected_legacy.rename("dollar_volume_20"))
    assert config["features"]["liquidity_basis"] == PRIOR_DAILY_BASIS


def test_symbol_failing_adv_is_excluded_before_signal_generation():
    config = load_config(ROOT / "config" / "phase3b_redesign.yaml")
    strategy = NaturalLongGridStrategy(config, "CSCO")
    timestamp = pd.Timestamp("2025-01-06 10:00", tz="America/New_York")
    strategy.prepared = pd.DataFrame(
        {
            "close": [50.0], "atr_14": [1.0], "adx_14": [10.0], "atr_ratio": [1.0],
            "range_high": [55.0], "range_low": [48.0], "range_position": [0.20],
            "range_width_atr": [7.0], "market_regime": ["RANGE_OK"],
            "dollar_volume_20": [49_999_999.0],
        },
        index=[timestamp],
    )
    portfolio = SimpleNamespace(equity=100_000.0, positions={}, prices={"CSCO": 50.0})
    assert strategy.on_bar(timestamp, portfolio) == []
    assert strategy.machine.state == StrategyState.SCAN
    assert not strategy.decisions


def test_intrabar_and_close_confirmation_stops_are_distinct():
    base = load_config(ROOT / "config" / "phase3b_redesign.yaml")
    timestamp = pd.Timestamp("2025-01-06 10:00", tz="America/New_York")
    portfolio = SimpleNamespace(
        equity=100_000.0,
        positions={"CSCO": Position("CSCO", quantity=100.0, average_price=50.0)},
        prices={"CSCO": 49.0},
    )

    intrabar = deepcopy(base)
    intrabar["strategy"]["natural"]["stop_trigger_mode"] = "intrabar"
    strategy = NaturalLongGridStrategy(intrabar, "CSCO")
    strategy.machine.state = StrategyState.GRID_ACTIVE
    strategy.campaign.group_id = "intrabar"
    strategy.campaign.stop_price = 48.0
    orders = strategy.protective_orders_at_bar(
        timestamp, portfolio, {"CSCO": pd.Series({"open": 49.0, "high": 50.0, "low": 47.5, "close": 49.0})}
    )
    assert len(orders) == 1
    assert orders[0].requested_price == 48.0
    assert strategy.machine.state == StrategyState.KILL

    close = deepcopy(base)
    close["strategy"]["natural"].update(
        {"stop_trigger_mode": "close_confirmation", "stop_confirmation_closes": 2, "catastrophic_stop_atr": 2.5}
    )
    strategy = NaturalLongGridStrategy(close, "CSCO")
    strategy.machine.state = StrategyState.GRID_ACTIVE
    strategy.campaign.group_id = "close"
    strategy.campaign.stop_price = 48.0
    strategy.campaign.catastrophic_stop_price = 45.0
    assert strategy.protective_orders_at_bar(
        timestamp, portfolio, {"CSCO": pd.Series({"open": 49.0, "high": 50.0, "low": 47.5, "close": 49.0})}
    ) == []
    assert strategy.machine.state == StrategyState.GRID_ACTIVE


def test_phase3b_variants_are_preregistered_and_cannot_enable_breakout():
    config = load_config(ROOT / "config" / "phase3b_redesign.yaml")
    _validate_registry(config)
    original = deepcopy(config)
    for variant, item in variant_registry().items():
        source = item.get("alias_of", variant)
        changed = _apply_variant(config, source, 50_000_000.0)
        assert changed["strategy"]["breakout"]["enabled"] is False
        if item["family"] == "residual_grid":
            assert changed["strategy"]["residual"] == config["strategy"]["residual"]
    assert config == original


def test_phase3b_job_matrix_is_fixed_before_results():
    config = load_config(ROOT / "config" / "phase3b_redesign.yaml")
    jobs = _jobs(config)
    hypothesis_jobs = [job for job in jobs if not job["variant"].startswith("LQ_STRESS_")]
    stress_jobs = [job for job in jobs if job["variant"].startswith("LQ_STRESS_")]
    # 10 natural variants × 11 symbols × 2 timeframes; 6 executable pair
    # variants × 7 pairs × 2; one residual confirmation × 11 × 2.
    assert len(hypothesis_jobs) == 220 + 84 + 22
    # Four extra ADV thresholds × (11 natural + 7 pairs) × two timeframes.
    assert len(stress_jobs) == 144
    assert {job["threshold"] for job in stress_jobs} == {10_000_000.0, 25_000_000.0, 100_000_000.0, None}


def test_no_liquidity_gate_variant_is_explicit_and_does_not_mutate_threshold():
    config = load_config(ROOT / "config" / "phase3b_redesign.yaml")
    changed = _apply_variant(config, "H1_CORRECTED_BASELINE", None)
    assert changed["features"]["liquidity_gate_enabled"] is False
    assert changed["universe"]["min_average_daily_dollar_volume"] == 50_000_000
    assert config["features"]["liquidity_gate_enabled"] is True


def test_dst_crossing_replay_bounds_slice_safely_in_utc():
    index = pd.date_range(
        "2025-10-31 09:30", "2025-11-03 10:00", freq="30min", tz="America/New_York"
    )
    frame = pd.DataFrame({"close": np.arange(len(index), dtype=float)}, index=index)
    frame.index = frame.index.tz_convert("UTC")
    start = pd.Timestamp("2025-10-31T15:30:00-04:00").tz_convert("UTC")
    end = pd.Timestamp("2025-11-03T10:00:00-05:00").tz_convert("UTC")
    sliced = frame.loc[start:end]
    assert not sliced.empty
    assert str(sliced.index.tz) == "UTC"


def test_reporting_classifies_sufficient_uniformly_negative_family_as_abandon():
    summary = pd.DataFrame(
        {
            "strategy_family": ["stock_pair_grid", "stock_pair_grid"],
            "campaign_count": [355, 376],
            "profit_factor": [0.47, 0.46],
            "expectancy": [-73.57, -71.29],
            "research_gate": [False, False],
        }
    )
    assert _family_status(summary, "stock_pair_grid") == "ABANDON"


def test_reporting_does_not_call_close_confirmation_improved_when_intrabar_is_better():
    diagnostics = pd.DataFrame(
        {"hypothesis": ["H3", "H3", "H3"], "stop_later_reverted_rate": [0.2, 0.3, 0.25]}
    )
    summary = pd.DataFrame(
        {
            "hypothesis": ["H3", "H3", "H3"],
            "variant": ["H3_INTRABAR", "H3_CLOSE1", "H3_CLOSE2"],
            "profit_factor": [1.05, 0.90, 1.01],
            "expectancy": [14.8, -13.8, 3.0],
        }
    )
    assert _stop_status(diagnostics, summary) == "MIXED"
