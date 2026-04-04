from __future__ import annotations

from trainer.config import BackendEndpointConfig
from trainer.environment.base_env import BaseEnvironmentAdapter
from trainer.interfaces import EnvStepResult
from trainer.schemas.action import SharedAction
from trainer.schemas.observation import SharedObservation


class RimAPIAdapter(BaseEnvironmentAdapter):
    """Scaffold adapter for a future RIMAPI state/action bridge."""

    backend_name = "rimapi"

    def __init__(self, settings: BackendEndpointConfig) -> None:
        self.settings = settings

    def reset(self) -> SharedObservation:
        raise NotImplementedError("RIMAPI adapter scaffold is not implemented yet.")

    def step(self, action: SharedAction) -> EnvStepResult:
        raise NotImplementedError("RIMAPI adapter scaffold is not implemented yet.")
