from __future__ import annotations

from trainer.config import BackendEndpointConfig
from trainer.environment.base_env import BaseEnvironmentAdapter
from trainer.interfaces import EnvStepResult
from trainer.schemas.action import SharedAction
from trainer.schemas.observation import SharedObservation


class RimBridgeServerAdapter(BaseEnvironmentAdapter):
    """Scaffold adapter for a future RimBridgeServer state/action bridge."""

    backend_name = "rimbridge"

    def __init__(self, settings: BackendEndpointConfig) -> None:
        self.settings = settings

    def reset(self) -> SharedObservation:
        raise NotImplementedError("RimBridgeServer adapter scaffold is not implemented yet.")

    def step(self, action: SharedAction) -> EnvStepResult:
        raise NotImplementedError("RimBridgeServer adapter scaffold is not implemented yet.")
