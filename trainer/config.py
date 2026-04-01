from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

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


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config/default.yaml"
PROFILE_DIR = REPO_ROOT / "config/profiles"


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Path | str = DEFAULT_CONFIG_PATH, profile: str | None = None) -> TrainerConfig:
    config_path = Path(path)
    raw = _read_yaml(config_path)

    if profile:
        profile_path = PROFILE_DIR / f"{profile}.yaml"
        if not profile_path.exists():
            raise FileNotFoundError(f"Config profile not found: {profile_path}")
        profile_raw = _read_yaml(profile_path)
        raw = _deep_merge(raw, profile_raw)

    return TrainerConfig.model_validate(raw)
