from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


def _ratio_field(default: float = 0.0) -> Any:
    return Field(default=default, ge=0.0, le=1.0)


class SharedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GameSpeed(str, Enum):
    paused = "paused"
    normal = "normal"
    fast = "fast"
    superfast = "superfast"


class PriorityLevel(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"
    critical = "critical"


class CombatPosture(str, Enum):
    avoid = "avoid"
    balanced = "balanced"
    aggressive = "aggressive"


class ColonistStatusSummary(SharedModel):
    healthy: int = Field(default=0, ge=0)
    injured: int = Field(default=0, ge=0)
    downed: int = Field(default=0, ge=0)
    mental_break_risk: int = Field(default=0, ge=0)


class ResearchState(SharedModel):
    current_project: str | None = None
    progress: float = _ratio_field()
    completed: bool = False


class ProgressIndicators(SharedModel):
    run_completion: float = _ratio_field()
    colony_development: float = _ratio_field()
    research_completion: float = _ratio_field()


class FailureRiskIndicators(SharedModel):
    starvation: float = _ratio_field()
    medical: float = _ratio_field()
    mood_break: float = _ratio_field()
    restart: float = _ratio_field()


class BridgeCapabilities(SharedModel):
    can_set_speed: bool = False
    can_restart_run: bool = False
    can_start_new_game: bool = False
    can_read_colonists: bool = False
    can_read_resources: bool = False
    can_set_work_priorities: bool = False
    can_choose_research: bool = False
    can_control_alert_posture: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class Observation(SharedModel):
    colonist_count: int = Field(ge=0)
    colonist_status_summary: ColonistStatusSummary
    food: int = Field(ge=0)
    medicine: int = Field(ge=0)
    colony_wealth: float = Field(ge=0.0)
    mood_risk: float = _ratio_field()
    health_risk: float = _ratio_field()
    injury_burden: float = _ratio_field()
    threat_level: float = _ratio_field()
    research_state: ResearchState
    step_count: int = Field(ge=0)
    run_time_seconds: int = Field(default=0, ge=0)
    game_speed: GameSpeed = GameSpeed.normal
    progress: ProgressIndicators
    failure_risk: FailureRiskIndicators
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmptyPayload(SharedModel):
    pass


class ResourcePriorityPayload(SharedModel):
    priority: PriorityLevel


class SpeedPayload(SharedModel):
    speed: GameSpeed


class WorkPriorityAssignment(SharedModel):
    work_type: str = Field(min_length=1)
    priority: int = Field(ge=1, le=4)


class WorkPriorityPayload(SharedModel):
    priorities: list[WorkPriorityAssignment] = Field(default_factory=list)


class ResearchChoicePayload(SharedModel):
    project: str = Field(min_length=1)


class CombatPosturePayload(SharedModel):
    posture: CombatPosture


class ColonistCapPayload(SharedModel):
    colonist_cap: int = Field(ge=0)


class RestartPayload(SharedModel):
    reason: str | None = None


class BaseAction(SharedModel):
    type: str


class WaitAction(BaseAction):
    type: Literal["wait"] = "wait"
    payload: EmptyPayload = Field(default_factory=EmptyPayload)


class SetSpeedAction(BaseAction):
    type: Literal["set_speed"] = "set_speed"
    payload: SpeedPayload


class SetWorkPrioritiesAction(BaseAction):
    type: Literal["set_work_priorities"] = "set_work_priorities"
    payload: WorkPriorityPayload


class ChooseResearchAction(BaseAction):
    type: Literal["choose_research"] = "choose_research"
    payload: ResearchChoicePayload


class SetFoodPriorityAction(BaseAction):
    type: Literal["set_food_priority"] = "set_food_priority"
    payload: ResourcePriorityPayload


class SetMedicalPriorityAction(BaseAction):
    type: Literal["set_medical_priority"] = "set_medical_priority"
    payload: ResourcePriorityPayload


class SetCombatPostureAction(BaseAction):
    type: Literal["set_combat_posture"] = "set_combat_posture"
    payload: CombatPosturePayload


class EnforceColonistCapAction(BaseAction):
    type: Literal["enforce_colonist_cap"] = "enforce_colonist_cap"
    payload: ColonistCapPayload


class RequestRestartAction(BaseAction):
    type: Literal["request_restart"] = "request_restart"
    payload: RestartPayload = Field(default_factory=RestartPayload)


class PauseAction(BaseAction):
    type: Literal["pause"] = "pause"
    payload: EmptyPayload = Field(default_factory=EmptyPayload)


class ResumeAction(BaseAction):
    type: Literal["resume"] = "resume"
    payload: EmptyPayload = Field(default_factory=EmptyPayload)


EnvironmentAction = Annotated[
    Union[
        WaitAction,
        SetSpeedAction,
        SetWorkPrioritiesAction,
        ChooseResearchAction,
        SetFoodPriorityAction,
        SetMedicalPriorityAction,
        SetCombatPostureAction,
        EnforceColonistCapAction,
        RequestRestartAction,
        PauseAction,
        ResumeAction,
    ],
    Field(discriminator="type"),
]


_ACTION_ADAPTER = TypeAdapter(EnvironmentAction)


def validate_observation(observation: Observation | dict[str, Any]) -> Observation:
    return observation if isinstance(observation, Observation) else Observation.model_validate(observation)


def validate_action(action: EnvironmentAction | dict[str, Any]) -> EnvironmentAction:
    return _ACTION_ADAPTER.validate_python(action)
