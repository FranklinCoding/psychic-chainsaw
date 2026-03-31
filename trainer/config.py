from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

BackendName = Literal["mock", "rimapi", "rimbridge"]


class AppConfig(BaseModel):
    log_level: str = "INFO"
    save_logs: bool = True


class TrainingConfig(BaseModel):
    training_mode: bool = True
    evaluation_mode: bool = False
    checkpoint_frequency: int = 10
    max_run_duration_minutes: int = 60
    auto_restart_delay_seconds: int = 2


class PolicyConfig(BaseModel):
    max_colonists: int = 6
    failure_threshold: float = 0.7
    exploration: float = 0.1
    learning_rate: float = 0.001
    colony_strategy_focus: str = "survival"
    min_food_reserve: int = 20
    min_medicine_reserve: int = 5
    acceptable_injury_threshold: float = 0.4
    combat_stance: str = "balanced"


class BackendEndpointConfig(BaseModel):
    base_url: str
    timeout_seconds: int = 10


class BackendsConfig(BaseModel):
    rimapi: BackendEndpointConfig
    rimbridge: BackendEndpointConfig


class TrainerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bridge_backend: BackendName = "mock"
    app: AppConfig = Field(default_factory=AppConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    backends: BackendsConfig


DEFAULT_CONFIG_PATH = Path("config/default.yaml")


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> TrainerConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return TrainerConfig.model_validate(raw)
