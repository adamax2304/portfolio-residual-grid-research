from __future__ import annotations

from collections.abc import Callable, Iterable
from copy import deepcopy
from itertools import product
from typing import Any

import pandas as pd


def walk_forward_splits(
    index: pd.Index,
    *,
    train_months: int = 6,
    test_months: int = 1,
) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    dates = pd.DatetimeIndex(index).sort_values()
    if dates.empty:
        return []
    cursor = dates.min() + pd.DateOffset(months=train_months)
    result = []
    while cursor < dates.max():
        train_start = cursor - pd.DateOffset(months=train_months)
        train_end = cursor - pd.Timedelta(nanoseconds=1)
        test_start = cursor
        test_end = min(cursor + pd.DateOffset(months=test_months) - pd.Timedelta(nanoseconds=1), dates.max())
        result.append((train_start, train_end, test_start, test_end))
        cursor += pd.DateOffset(months=test_months)
    return result


def run_walk_forward(
    data: dict[str, pd.DataFrame],
    *,
    strategy_factory: Callable[[], Any],
    engine_factory: Callable[[], Any],
    train_months: int = 6,
    test_months: int = 1,
) -> pd.DataFrame:
    common = sorted(set.intersection(*(set(frame.index) for frame in data.values())))
    rows: list[dict[str, Any]] = []
    for train_start, train_end, test_start, test_end in walk_forward_splits(
        pd.DatetimeIndex(common), train_months=train_months, test_months=test_months
    ):
        # Include training history for indicator warm-up; score only the test segment.
        window = {symbol: frame.loc[train_start:test_end] for symbol, frame in data.items()}
        result = engine_factory().run(strategy_factory(), window)
        test_equity = result.equity_curve.loc[test_start:test_end]
        test_return = float(test_equity.iloc[-1] / test_equity.iloc[0] - 1) if len(test_equity) > 1 else 0.0
        rows.append({
            "train_start": train_start,
            "train_end": train_end,
            "test_start": test_start,
            "test_end": test_end,
            "test_return": test_return,
            "fill_count": sum(test_start <= pd.Timestamp(fill.timestamp) <= test_end for fill in result.fills),
        })
    return pd.DataFrame(rows)


def _set_path(config: dict, path: str, value: Any) -> None:
    cursor = config
    parts = path.split(".")
    for part in parts[:-1]:
        cursor = cursor[part]
    cursor[parts[-1]] = value


def run_sensitivity(
    base_config: dict,
    grid: dict[str, Iterable[Any]],
    runner: Callable[[dict], dict[str, Any]],
) -> pd.DataFrame:
    """Run a caller-supplied backtest over an explicit parameter product."""
    keys = list(grid)
    rows: list[dict[str, Any]] = []
    for values in product(*(grid[key] for key in keys)):
        config = deepcopy(base_config)
        parameters = dict(zip(keys, values))
        for path, value in parameters.items():
            _set_path(config, path, value)
        metrics = runner(config)
        rows.append({**parameters, **metrics})
    return pd.DataFrame(rows)

