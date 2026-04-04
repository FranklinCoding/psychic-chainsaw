from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

GameSpeed = Literal["paused", "normal", "fast", "superfast"]
CombatPosture = Literal["defensive", "neutral", "aggressive"]


class SetSpeedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal["set_speed"]
    speed: GameSpeed


class SetWorkPrioritiesAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal["set_work_priorities"]
    priorities: dict[str, int] = Field(default_factory=dict)

    @field_validator("priorities")
    @classmethod
    def validate_priority_levels(cls, priorities: dict[str, int]) -> dict[str, int]:
        for work_type, level in priorities.items():
            if level < 0 or level > 4:
                raise ValueError(
                    f"Work priority for '{work_type}' must be between 0 and 4 inclusive."
                )
        return priorities


class ChooseResearchAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal["choose_research"]
    research_id: str = Field(min_length=1)


class SetFoodPriorityAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal["set_food_priority"]
    level: int = Field(ge=0, le=5)


class SetMedicalPriorityAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal["set_medical_priority"]
    level: int = Field(ge=0, le=5)


class SetCombatPostureAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal["set_combat_posture"]
    posture: CombatPosture


class EnforceColonistCapAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal["enforce_colonist_cap"]
    cap: int = Field(ge=1)


class RequestRestartAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal["request_restart"]
    reason: str | None = None


class PauseAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal["pause"]


class ResumeAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal["resume"]


SharedAction = Annotated[
    SetSpeedAction
    | SetWorkPrioritiesAction
    | ChooseResearchAction
    | SetFoodPriorityAction
    | SetMedicalPriorityAction
    | SetCombatPostureAction
    | EnforceColonistCapAction
    | RequestRestartAction
    | PauseAction
    | ResumeAction,
    Field(discriminator="action_type"),
]

SHARED_ACTION_ADAPTER: TypeAdapter[SharedAction] = TypeAdapter(SharedAction)
