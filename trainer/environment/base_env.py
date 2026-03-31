from __future__ import annotations

from typing import Any, Mapping

from trainer.interfaces import EnvStepResult


class BaseEnvironmentAdapter:
    """Optional convenience base class for adapter implementations."""

    backend_name = "base"

    def reset(self) -> Mapping[str, Any]:
        raise NotImplementedError

    def step(self, action: Mapping[str, Any]) -> EnvStepResult:
        raise NotImplementedError

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def reset_run(self) -> Mapping[str, Any]:
        return self.reset()

    def get_observation(self) -> Mapping[str, Any]:
        raise NotImplementedError

    def apply_action(self, action: Mapping[str, Any]) -> EnvStepResult:
        return self.step(action)

    def is_terminal(self) -> bool:
        return False

    def get_terminal_reason(self) -> str:
        return "unknown"

    def close(self) -> None:
        self.disconnect()
