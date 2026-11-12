from __future__ import annotations

import pandas as pd

from residual_grid_research.phase3a import (
    _bucket_metrics,
    _diagnostic_flags,
    _signal_time,
    _status_summary,
)


def _campaigns() -> pd.DataFrame:
    rows = []
    for number in range(32):
        pnl = 10.0 if number % 2 == 0 else -5.0
        rows.append({
            "campaign_id": f"c{number}", "strategy_family": "residual_grid",
            "pair": "AAA/ETF" if number < 16 else "BBB/ETF", "timeframe": "5min",
            "start_timestamp": pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=number * 3),
            "net_pnl": pnl, "filled_levels": 4, "mae": -8.0, "mfe": 12.0,
            "cost_total": 1.0, "exit_reason": "residual TP1" if pnl > 0 else "residual kill",
            "market_regime": "RANGE_OK", "hedge_leg_pnl": -1.0, "stock_leg_pnl": pnl + 1.0,
            "grid_step_atr": 0.6,
        })
    return pd.DataFrame(rows)


def test_signal_time_uses_campaign_encoded_causal_timestamp() -> None:
    fallback = pd.Timestamp("2024-01-03", tz="America/New_York")
    parsed = _signal_time("residual_grid:AAA:2024-01-02T14:30:00-05:00", fallback)
    assert parsed == pd.Timestamp("2024-01-02T14:30:00-05:00")


def test_bucket_metrics_and_sample_gate() -> None:
    campaigns = _campaigns()
    metrics = _bucket_metrics(campaigns)
    flags = _diagnostic_flags(metrics, campaigns)
    assert metrics["campaigns"] == 32
    assert metrics["profit_factor"] == 2.0
    assert "SUFFICIENT_SAMPLE" in flags
    assert metrics["symbols"] == 2
    assert metrics["months"] > 1


def test_status_summary_never_promotes_live() -> None:
    campaigns = _campaigns().assign(
        residual_z_score=-1.6, breakout_flag=False, breakout_pnl=0.0,
        later_reverted_after_stop=False, r_multiple=-0.1,
        cost_as_pct_expected_tp=0.1,
    )
    conditional = pd.DataFrame([{
        "strategy_family": "residual_grid", "conditional_edge_eligible": False,
        "profit_factor": 2.0, "expectancy": 2.5,
    }])
    counterfactuals = pd.DataFrame([{
        "primary_failure_mode": "NO_MEAN_REVERSION", "net_pnl": -5.0,
    }])
    summary = _status_summary(campaigns, conditional, counterfactuals)
    assert summary["conditional_edge_found"] == "UNDERPOWERED"
    assert summary["main_loss_driver"] == "NO_MEAN_REVERSION"

