from __future__ import annotations

from trainer.config import TrainerConfig
from trainer.environment.mock_env import MockEnvironmentAdapter
from trainer.environment.rimapi.adapter import RimAPIAdapter
from trainer.environment.rimbridge.adapter import RimBridgeServerAdapter
from trainer.interfaces import EnvironmentAdapter


def create_environment(config: TrainerConfig) -> EnvironmentAdapter:
    backend = config.bridge_backend
    if backend == "mock":
        return MockEnvironmentAdapter()
    if backend == "rimapi":
        return RimAPIAdapter(settings=config.backends.rimapi)
    if backend == "rimbridge":
        return RimBridgeServerAdapter(settings=config.backends.rimbridge)

    raise ValueError(f"Unsupported backend: {backend}")
