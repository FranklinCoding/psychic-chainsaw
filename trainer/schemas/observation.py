from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResearchStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_research: str | None = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    is_active: bool = False


class ProgressIndicators(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_progress: float = Field(default=0.0, ge=0.0, le=1.0)
    objective_progress: float = Field(default=0.0, ge=0.0, le=1.0)


class FailureRiskIndicators(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starvation_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    raid_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    mental_break_risk: float = Field(default=0.0, ge=0.0, le=1.0)


class SharedObservation(BaseModel):
    """Bridge-agnostic state passed between trainers and environments."""

    model_config = ConfigDict(extra="forbid")

    colonist_count: int = Field(ge=0)
    colonist_status_summary: str = "stable"
    food_reserves: float = Field(ge=0.0)
    medicine_reserves: float = Field(ge=0.0)
    colony_wealth: float = Field(ge=0.0)
    mood_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    health_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    injury_burden: float = Field(default=0.0, ge=0.0, le=1.0)
    threat_level: float = Field(default=0.0, ge=0.0, le=1.0)

    research_status: ResearchStatus = Field(default_factory=ResearchStatus)

    run_time_seconds: float = Field(default=0.0, ge=0.0)
    step_count: int = Field(default=0, ge=0)
    game_speed: Literal["paused", "normal", "fast", "superfast"] = "normal"

    progress_indicators: ProgressIndicators = Field(default_factory=ProgressIndicators)
    failure_risk_indicators: FailureRiskIndicators = Field(default_factory=FailureRiskIndicators)
