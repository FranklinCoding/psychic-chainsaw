from __future__ import annotations

from typing import Any, Mapping

from trainer.config import BackendEndpointConfig
from trainer.environment.base_env import BaseEnvironmentAdapter
from trainer.interfaces import EnvStepResult


class RimAPIAdapter(BaseEnvironmentAdapter):
    """Scaffold adapter for a future RIMAPI state/action bridge."""

    backend_name = "rimapi"

    def __init__(self, settings: BackendEndpointConfig) -> None:
        self.settings = settings

    def reset(self) -> Mapping[str, Any]:
        raise NotImplementedError("RIMAPI adapter scaffold is not implemented yet.")

    def step(self, action: Mapping[str, Any]) -> EnvStepResult:
        raise NotImplementedError("RIMAPI adapter scaffold is not implemented yet.")
