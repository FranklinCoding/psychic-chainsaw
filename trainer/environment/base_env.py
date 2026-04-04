from __future__ import annotations

from trainer.interfaces import EnvStepResult
from trainer.schemas.action import SharedAction
from trainer.schemas.observation import SharedObservation


class BaseEnvironmentAdapter:
    """Optional convenience base class for adapter implementations."""

    backend_name = "base"

    def reset(self) -> SharedObservation:
        raise NotImplementedError

    def step(self, action: SharedAction) -> EnvStepResult:
        raise NotImplementedError

    def close(self) -> None:
        return None
