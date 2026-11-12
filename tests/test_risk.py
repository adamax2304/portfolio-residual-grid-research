import numpy as np

from residual_grid_research.risk import RiskManager


def test_full_grid_loss_respects_campaign_budget(config):
    manager = RiskManager(config)
    std = 0.04
    levels = [1.4, 1.7, 2.0, 2.2]
    kill = 2.8
    notionals = manager.relationship_grid_notionals(
        residual_std=std, grid_levels=levels, kill_z=kill, equity=100_000
    )
    losses = np.expm1(std * (kill - np.asarray(levels)))
    worst_case = float(np.dot(notionals, losses))
    assert worst_case <= 100_000 * config["risk"]["max_risk_per_trade_pct"] + 1e-8
    assert sum(notionals) <= 100_000 * config["risk"]["max_effective_leverage_start"]


def test_config_rejects_bad_layer_weights(tmp_path):
    from residual_grid_research.config import ConfigError, load_config
    import yaml
    from pathlib import Path

    source = Path(__file__).parents[1] / "config" / "default.yaml"
    value = yaml.safe_load(source.read_text(encoding="utf-8"))
    value["risk"]["layer_weights"] = [1, 1, 1, 1]
    target = tmp_path / "bad.yaml"
    target.write_text(yaml.safe_dump(value), encoding="utf-8")
    try:
        load_config(target)
    except ConfigError:
        pass
    else:
        raise AssertionError("invalid weights should fail")

