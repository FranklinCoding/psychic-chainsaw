from __future__ import annotations

from trainer.interfaces import EnvStepResult, SharedActionInput
from trainer.schemas.observation import SharedObservation


class BaseEnvironmentAdapter:
    """Optional convenience base class for adapter implementations."""

    backend_name = "base"

    def reset(self) -> SharedObservation:
        raise NotImplementedError

    def step(self, action: SharedActionInput) -> EnvStepResult:
        raise NotImplementedError

    def close(self) -> None:
        return None
