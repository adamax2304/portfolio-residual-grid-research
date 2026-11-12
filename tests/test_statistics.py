import numpy as np
import pandas as pd

from residual_grid_research.features.statistics import rolling_relationship


def _series(seed: int = 1):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2020-01-01", periods=350)
    b = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(index)))), index=index)
    residual = np.zeros(len(index))
    for i in range(1, len(index)):
        residual[i] = 0.8 * residual[i - 1] + rng.normal(0, 0.01)
    a = pd.Series(50 * np.exp(0.9 * np.log(b / b.iloc[0]) + residual), index=index)
    return a, b


def test_rolling_coefficients_use_strictly_prior_bars():
    a, b = _series()
    original = rolling_relationship(a, b)
    changed = a.copy()
    at = a.index[250]
    changed.loc[at:] *= 4
    modified = rolling_relationship(changed, b)
    assert original.at[at, "alpha"] == modified.at[at, "alpha"]
    assert original.at[at, "beta"] == modified.at[at, "beta"]
    assert original.at[at, "corr_60"] == modified.at[at, "corr_60"]
    assert original.at[at, "z"] != modified.at[at, "z"]


def test_future_values_do_not_change_past_features():
    a, b = _series()
    original = rolling_relationship(a, b)
    changed = b.copy()
    changed.iloc[300:] *= 0.25
    modified = rolling_relationship(a, changed)
    pd.testing.assert_series_equal(original.loc[: b.index[299], "z"], modified.loc[: b.index[299], "z"])

