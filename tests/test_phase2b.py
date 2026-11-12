from __future__ import annotations

import pandas as pd

from residual_grid_research.config import load_config
from residual_grid_research.features.technical import add_liquidity_sweep_features
from residual_grid_research.phase2b import enrich_campaigns, phase2b_acceptance


def test_sweep_reclaim_is_never_emitted_on_sweep_candle():
    index = pd.date_range("2025-01-01", periods=6, freq="B")
    frame = pd.DataFrame(
        {
            "open": [105, 105, 105, 100, 100, 101],
            "high": [106, 106, 106, 101, 102, 102],
            "low": [104, 104, 104, 99, 100, 100],
            "close": [105, 105, 105, 99.5, 101, 101],
            "volume": [100] * 6,
            "volume_ratio": [1, 1, 1, 2, 1, 1],
            "range_low": [100] * 6,
            "range_high": [110] * 6,
        },
        index=index,
    )
    result = add_liquidity_sweep_features(frame)
    assert bool(result.loc[index[3], "bullish_sweep"])
    assert not bool(result.loc[index[3], "bullish_sweep_reclaim"])
    assert bool(result.loc[index[4], "bullish_sweep_reclaim"])


def test_campaign_enrichment_attributes_mode_direction_and_exit():
    campaigns = pd.DataFrame(
        [{"run": "residual_grid:A/B", "group_id": "residual_grid:A:1", "entry_time": "2025-01-01", "exit_time": "2025-01-03", "pnl_usd": -5}]
    )
    fills = pd.DataFrame(
        [
            {"run": "residual_grid:A/B", "group_id": "residual_grid:A:1", "timestamp": "2025-01-02", "side": "SELL", "reason": "residual grid layer 1", "metadata": "{'direction': -1}"},
            {"run": "residual_grid:A/B", "group_id": "residual_grid:A:1", "timestamp": "2025-01-03", "side": "BUY", "reason": "residual time stop", "metadata": "{'close_all': True}"},
        ]
    )
    result = enrich_campaigns(campaigns, fills).iloc[0]
    assert result["campaign_mode"] == "grid_mean_reversion"
    assert result["direction"] == "short_residual"
    assert result["exit_category"] == "time_stop"


def test_underpowered_exception_requires_every_other_research_gate(tmp_path):
    config = load_config("config/phase2b_real.yaml")
    expanded = pd.DataFrame(
        [{
            "run": "natural_long_grid:X", "trade_legs": 35, "campaigns": 25,
            "profit_factor": 2.0, "expectancy_usd": 100.0,
            "top_campaign_net_profit_share": 0.20, "max_drawdown": -0.02,
            "oos_return": 0.05, "local_parameter_pass_rate": 1.0,
            "strict_2x_cost_expectancy_usd": 80.0, "strict_2x_cost_profit_factor": 1.8,
            "strict_fill_expectancy_usd": 70.0, "strict_fill_profit_factor": 1.6,
            "positive_regimes": 2, "twelve_month_warmup_expectancy_usd": 90.0,
            "twelve_month_warmup_profit_factor": 1.7,
        }]
    )
    breakout = pd.DataFrame([{"run": "natural_long_grid:X", "sample": "phase2b_expanded"}])
    gate = phase2b_acceptance(expanded, breakout, config)["natural_long_grid:X"]
    assert gate["passed"]
    assert gate["underpowered"]
    assert gate["promotion_type"] == "UNDERPOWERED_RESEARCH_CANDIDATE"

    expanded.loc[0, "top_campaign_net_profit_share"] = 0.30
    failed = phase2b_acceptance(expanded, breakout, config)["natural_long_grid:X"]
    assert not failed["passed"]
    assert "campaign_concentration" in failed["failed"]
