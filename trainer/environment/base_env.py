from __future__ import annotations

from trainer.interfaces import EnvStepResult
from trainer.schemas import EnvironmentAction, Observation


class BaseEnvironmentAdapter:
    """Optional convenience base class for adapter implementations."""

    backend_name = "base"

    def reset(self) -> Observation:
        raise NotImplementedError

    def step(self, action: EnvironmentAction) -> EnvStepResult:
        raise NotImplementedError

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def reset_run(self) -> Observation:
        return self.reset()

    def get_observation(self) -> Observation:
        raise NotImplementedError

    def apply_action(self, action: EnvironmentAction) -> EnvStepResult:
        return self.step(action)

    def is_terminal(self) -> bool:
        return False

    def get_terminal_reason(self) -> str:
        return "unknown"

    def close(self) -> None:
        self.disconnect()
