from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from residual_grid_research.models import Decision, StrategyState


_ALLOWED: dict[StrategyState, set[StrategyState]] = {
    StrategyState.SCAN: {StrategyState.CANDIDATE, StrategyState.FLAT, StrategyState.COOLDOWN},
    StrategyState.CANDIDATE: {StrategyState.ARMED, StrategyState.SCAN, StrategyState.COOLDOWN},
    StrategyState.ARMED: {StrategyState.GRID_ACTIVE, StrategyState.SCAN, StrategyState.KILL},
    StrategyState.GRID_ACTIVE: {
        StrategyState.WARNING,
        StrategyState.GRID_EXITING,
        StrategyState.BREAKOUT_SETUP,
        StrategyState.KILL,
    },
    StrategyState.WARNING: {
        StrategyState.GRID_ACTIVE,
        StrategyState.GRID_EXITING,
        StrategyState.BREAKOUT_SETUP,
        StrategyState.KILL,
    },
    StrategyState.GRID_EXITING: {StrategyState.FLAT, StrategyState.KILL},
    StrategyState.BREAKOUT_SETUP: {
        StrategyState.BREAKOUT_ACTIVE,
        StrategyState.GRID_EXITING,
        StrategyState.KILL,
    },
    StrategyState.BREAKOUT_ACTIVE: {StrategyState.GRID_EXITING, StrategyState.KILL},
    StrategyState.KILL: {StrategyState.COOLDOWN},
    StrategyState.COOLDOWN: {StrategyState.FLAT, StrategyState.SCAN},
    StrategyState.FLAT: {StrategyState.SCAN, StrategyState.CANDIDATE, StrategyState.COOLDOWN},
}


@dataclass
class StrategyStateMachine:
    strategy_name: str
    symbol: str
    state: StrategyState = StrategyState.SCAN
    decisions: list[Decision] = field(default_factory=list)

    def transition(
        self,
        timestamp: pd.Timestamp,
        new_state: StrategyState,
        reason: str,
        *,
        score: float | None = None,
        metadata: dict | None = None,
    ) -> Decision:
        if new_state == self.state:
            raise ValueError(f"State is already {new_state.value}")
        if new_state not in _ALLOWED[self.state]:
            raise ValueError(f"Illegal transition {self.state.value} -> {new_state.value}")
        decision = Decision(
            timestamp=pd.Timestamp(timestamp).to_pydatetime(),
            strategy=self.strategy_name,
            state_from=self.state,
            state_to=new_state,
            reason=reason,
            score=score,
            symbol=self.symbol,
            metadata=metadata or {},
        )
        self.state = new_state
        self.decisions.append(decision)
        return decision

