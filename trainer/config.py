from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

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


class FailureWeightsConfig(BaseModel):
    all_colonists_incapacitated: float = Field(default=2.0, ge=0.0)
    starvation: float = Field(default=1.4, ge=0.0)
    medical_collapse: float = Field(default=1.2, ge=0.0)
    mood_collapse: float = Field(default=1.0, ge=0.0)
    severe_injury_burden: float = Field(default=1.0, ge=0.0)
    stalled_progress: float = Field(default=0.8, ge=0.0)
    severe_resource_depletion: float = Field(default=0.8, ge=0.0)
    high_failure_risk: float = Field(default=1.2, ge=0.0)


class FailureConfig(BaseModel):
    progress_window_steps: int = Field(default=4, ge=2)
    min_progress_delta: float = Field(default=0.04, ge=0.0, le=1.0)
    starvation_signal_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    medical_signal_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    mood_signal_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    injury_signal_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    resource_signal_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    high_risk_signal_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    weights: FailureWeightsConfig = Field(default_factory=FailureWeightsConfig)


class BackendEndpointConfig(BaseModel):
    timeout_seconds: int = 10


class RimAPIBackendConfig(BackendEndpointConfig):
    base_url: str = "http://127.0.0.1:8765"
    map_id: int = Field(default=0, ge=0)
    prefer_v2_colonists: bool = True
    start_new_game_on_reset: bool = False


class RimBridgeBackendConfig(BackendEndpointConfig):
    base_url: str | None = None
    host: str = "127.0.0.1"
    port: int | None = Field(default=None, ge=1, le=65535)
    token: str | None = None
    config_path: str | None = None
    transport: Literal["auto", "tcp"] = "auto"
    bridge_version: str = "psychic-chainsaw/0.1.0"
    launch_id: str | None = None

    @property
    def expanded_config_path(self) -> Path | None:
        if not self.config_path:
            return None
        expanded = os.path.expanduser(os.path.expandvars(self.config_path))
        return Path(expanded)

    def resolve_host_port(self) -> tuple[str, int | None]:
        if self.base_url:
            parsed = urlparse(self.base_url)
            if parsed.hostname:
                return parsed.hostname, parsed.port
        return self.host, self.port


class BackendsConfig(BaseModel):
    rimapi: RimAPIBackendConfig
    rimbridge: RimBridgeBackendConfig


class TrainerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bridge_backend: BackendName = "mock"
    app: AppConfig = Field(default_factory=AppConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    failure: FailureConfig = Field(default_factory=FailureConfig)
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
