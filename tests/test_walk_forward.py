import pandas as pd

from residual_grid_research.backtest.walk_forward import walk_forward_splits


def test_walk_forward_windows_are_ordered_and_nonoverlapping_tests():
    index = pd.bdate_range("2023-01-02", "2024-12-31")
    splits = walk_forward_splits(index, train_months=6, test_months=1)
    assert splits
    assert all(train_start < train_end < test_start <= test_end for train_start, train_end, test_start, test_end in splits)
    assert all(splits[i][3] < splits[i + 1][2] for i in range(len(splits) - 1))
