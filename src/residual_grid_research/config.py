from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when configuration violates a safety invariant."""


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if overrides:
        config = _merge(config, overrides)
    validate_config(config)
    config["_config_path"] = str(path.resolve())
    config["_project_root"] = str(path.resolve().parent.parent)
    return config


def validate_config(config: dict[str, Any]) -> None:
    required = {"project", "data", "universe", "features", "strategy", "risk", "costs"}
    missing = required.difference(config)
    if missing:
        raise ConfigError(f"Missing top-level sections: {sorted(missing)}")
    if config["project"]["starting_capital_usd"] <= 0:
        raise ConfigError("starting_capital_usd must be positive")
    if not 0 < config["risk"]["max_risk_per_trade_pct"] <= 0.1:
        raise ConfigError("max_risk_per_trade_pct must be in (0, 0.1]")
    weights = config["risk"]["layer_weights"]
    if len(weights) != 4 or abs(sum(weights) - 1.0) > 1e-9 or any(w <= 0 for w in weights):
        raise ConfigError("layer_weights must contain four positive values summing to 1")
    levels = config["strategy"]["residual"]["grid_levels"]
    if sorted(levels) != levels:
        raise ConfigError("residual grid_levels must be increasing")
    if config["strategy"]["residual"]["kill_z"] <= levels[-1]:
        raise ConfigError("residual kill_z must lie beyond the final grid level")
    if config["costs"]["partial_fill_ratio"] <= 0 or config["costs"]["partial_fill_ratio"] > 1:
        raise ConfigError("partial_fill_ratio must be in (0, 1]")


def project_path(config: dict[str, Any], *parts: str) -> Path:
    return Path(config["_project_root"], *parts)

