import pandas as pd
import pytest

from residual_grid_research.models import StrategyState
from residual_grid_research.strategies.state_machine import StrategyStateMachine


def test_valid_grid_and_kill_lifecycle():
    machine = StrategyStateMachine("test", "XYZ")
    at = pd.Timestamp("2025-01-02")
    for state in (
        StrategyState.CANDIDATE,
        StrategyState.ARMED,
        StrategyState.GRID_ACTIVE,
        StrategyState.WARNING,
        StrategyState.KILL,
        StrategyState.COOLDOWN,
        StrategyState.FLAT,
        StrategyState.SCAN,
    ):
        machine.transition(at, state, "test")
    assert machine.state == StrategyState.SCAN
    assert len(machine.decisions) == 8


def test_illegal_transition_is_rejected():
    machine = StrategyStateMachine("test", "XYZ")
    with pytest.raises(ValueError):
        machine.transition(pd.Timestamp("2025-01-02"), StrategyState.BREAKOUT_ACTIVE, "skip")

