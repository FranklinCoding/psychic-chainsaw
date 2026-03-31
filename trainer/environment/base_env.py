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

    def close(self) -> None:
        return None
