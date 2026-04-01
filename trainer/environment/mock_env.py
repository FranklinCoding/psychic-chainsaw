from __future__ import annotations

from trainer.environment.base_env import BaseEnvironmentAdapter
from trainer.interfaces import EnvStepResult
from trainer.schemas import (
    BridgeCapabilities,
    ChooseResearchAction,
    ColonistStatusSummary,
    CombatPosture,
    EnforceColonistCapAction,
    EnvironmentAction,
    FailureRiskIndicators,
    GameSpeed,
    Observation,
    PauseAction,
    PriorityLevel,
    ProgressIndicators,
    RequestRestartAction,
    ResearchState,
    ResumeAction,
    SetCombatPostureAction,
    SetFoodPriorityAction,
    SetMedicalPriorityAction,
    SetSpeedAction,
    SetWorkPrioritiesAction,
    WaitAction,
    validate_action,
)


def _clamp_ratio(value: float) -> float:
    return max(0.0, min(1.0, value))


class MockEnvironmentAdapter(BaseEnvironmentAdapter):
    """Simple deterministic backend for local development and CI."""

    backend_name = "mock"

    def __init__(self, max_steps: int = 8, initial_colonist_cap: int = 6) -> None:
        self.max_steps = max_steps
        self.initial_colonist_cap = initial_colonist_cap
        self.connected = False
        self._capabilities = BridgeCapabilities(
            can_set_speed=True,
            can_restart_run=True,
            can_start_new_game=True,
            can_read_colonists=True,
            can_read_resources=True,
            can_set_work_priorities=True,
            can_choose_research=True,
            can_control_alert_posture=True,
            metadata={"mode": "mock"},
        )
        self._terminal_reason = "not_started"
        self._work_priorities: dict[str, int] = {}
        self.reset_run()

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def reset_run(self) -> Observation:
        self.current_step = 0
        self.colonists = 3
        self.food = 16
        self.medicine = 5
        self.game_speed = GameSpeed.normal
        self.food_priority = PriorityLevel.normal
        self.medical_priority = PriorityLevel.normal
        self.combat_posture = CombatPosture.balanced
        self.colonist_cap = self.initial_colonist_cap
        self.research_project = "battery"
        self.research_progress = 0.2
        self.injury_burden = 0.15
        self.paused = False
        self._work_priorities = {}
        self._terminal_reason = "in_progress"
        return self.get_observation()

    def _starvation_risk(self) -> float:
        return _clamp_ratio((12 - self.food) / 12)

    def _medical_shortage_risk(self) -> float:
        return _clamp_ratio((3 - self.medicine) / 3)

    def _threat_level(self) -> float:
        posture_modifier = {
            CombatPosture.avoid: -0.05,
            CombatPosture.balanced: 0.0,
            CombatPosture.aggressive: 0.08,
        }[self.combat_posture]
        return _clamp_ratio(0.1 + (self.current_step * 0.07) + posture_modifier)

    def _health_risk(self) -> float:
        return _clamp_ratio((self.injury_burden * 0.7) + (self._medical_shortage_risk() * 0.3))

    def _mood_risk(self) -> float:
        return _clamp_ratio(
            (self._starvation_risk() * 0.5) + (self._threat_level() * 0.25) + (self.injury_burden * 0.25)
        )

    def _colony_wealth(self) -> float:
        return float((self.colonists * 400) + (self.food * 14) + (self.medicine * 30) + int(self.research_progress * 200))

    def _progress(self) -> ProgressIndicators:
        cap = max(self.colonist_cap, 1)
        colony_development = _clamp_ratio(
            ((self.colonists / cap) * 0.6) + (min(self.food / 20, 1.0) * 0.2) + (min(self.medicine / 5, 1.0) * 0.2)
        )
        return ProgressIndicators(
            run_completion=_clamp_ratio(self.current_step / max(self.max_steps, 1)),
            colony_development=colony_development,
            research_completion=self.research_progress,
        )

    def _failure_risk(self) -> FailureRiskIndicators:
        starvation = self._starvation_risk()
        medical = self._health_risk()
        mood_break = self._mood_risk()
        return FailureRiskIndicators(
            starvation=starvation,
            medical=medical,
            mood_break=mood_break,
            restart=max(starvation, medical, mood_break),
        )

    def _status_summary(self) -> ColonistStatusSummary:
        injured = min(self.colonists, int(round(self.injury_burden * self.colonists)))
        downed = min(max(self.colonists - injured, 0), 1 if self._health_risk() > 0.85 else 0)
        healthy = max(self.colonists - injured - downed, 0)
        mental_break_risk = min(self.colonists, 1 if self._mood_risk() > 0.65 else 0)
        return ColonistStatusSummary(
            healthy=healthy,
            injured=injured,
            downed=downed,
            mental_break_risk=mental_break_risk,
        )

    def get_observation(self) -> Observation:
        threat_level = self._threat_level()
        return Observation(
            colonist_count=self.colonists,
            colonist_status_summary=self._status_summary(),
            food=self.food,
            medicine=self.medicine,
            colony_wealth=self._colony_wealth(),
            mood_risk=self._mood_risk(),
            health_risk=self._health_risk(),
            injury_burden=self.injury_burden,
            threat_level=threat_level,
            research_state=ResearchState(
                current_project=self.research_project,
                progress=self.research_progress,
                completed=self.research_progress >= 1.0,
            ),
            step_count=self.current_step,
            run_time_seconds=self.current_step * 15,
            game_speed=self.game_speed,
            progress=self._progress(),
            failure_risk=self._failure_risk(),
            metadata={
                "backend": self.backend_name,
                "colonist_cap": self.colonist_cap,
                "food_priority": self.food_priority.value,
                "medical_priority": self.medical_priority.value,
                "combat_posture": self.combat_posture.value,
                "paused": self.paused,
                "supports_pause_resume": True,
                "work_priorities": dict(self._work_priorities),
                "terminal_reason": self._terminal_reason,
                "capabilities": self.get_capabilities().model_dump(mode="python"),
            },
        )

    def get_capabilities(self) -> BridgeCapabilities:
        return self._capabilities

    def _apply_food_priority(self, priority: PriorityLevel) -> float:
        self.food_priority = priority
        food_gain = {
            PriorityLevel.low: 0,
            PriorityLevel.normal: 1,
            PriorityLevel.high: 4,
            PriorityLevel.critical: 5,
        }[priority]
        self.food += food_gain
        return 0.2 if priority in {PriorityLevel.low, PriorityLevel.normal} else 0.9

    def _apply_medical_priority(self, priority: PriorityLevel) -> float:
        self.medical_priority = priority
        if self.medicine <= 0:
            return 0.0

        relief = {
            PriorityLevel.low: 0.0,
            PriorityLevel.normal: 0.04,
            PriorityLevel.high: 0.12,
            PriorityLevel.critical: 0.18,
        }[priority]
        medicine_cost = 1 if priority in {PriorityLevel.high, PriorityLevel.critical} else 0
        self.medicine = max(0, self.medicine - medicine_cost)
        self.injury_burden = _clamp_ratio(self.injury_burden - relief)
        return 0.15 if relief <= 0 else 0.5

    def _advance_world(self) -> None:
        if self.current_step == 4 and self.colonists < self.colonist_cap and self.food >= 10:
            self.colonists += 1

        self.food = max(0, self.food - 2)
        self.research_progress = _clamp_ratio(self.research_progress + 0.05)
        self.injury_burden = _clamp_ratio(self.injury_burden + max(self._threat_level() - 0.4, 0.0) * 0.08)

    def _update_terminal_state(self) -> None:
        if self._terminal_reason == "restart_requested":
            return
        if self.current_step >= self.max_steps:
            self._terminal_reason = "max_steps_reached"
        else:
            self._terminal_reason = "in_progress"

    def apply_action(self, action: EnvironmentAction) -> EnvStepResult:
        validated_action = validate_action(action)
        self.current_step += 1
        reward = 0.05

        if isinstance(validated_action, RequestRestartAction):
            self._terminal_reason = "restart_requested"
        else:
            self._advance_world()

            if isinstance(validated_action, WaitAction):
                reward += 0.1
            elif isinstance(validated_action, SetSpeedAction):
                self.game_speed = validated_action.payload.speed
                self.paused = self.game_speed == GameSpeed.paused
                reward += 0.05
            elif isinstance(validated_action, SetFoodPriorityAction):
                reward += self._apply_food_priority(validated_action.payload.priority)
            elif isinstance(validated_action, SetMedicalPriorityAction):
                reward += self._apply_medical_priority(validated_action.payload.priority)
            elif isinstance(validated_action, SetCombatPostureAction):
                self.combat_posture = validated_action.payload.posture
                reward += 0.15
            elif isinstance(validated_action, ChooseResearchAction):
                if validated_action.payload.project != self.research_project:
                    self.research_project = validated_action.payload.project
                    self.research_progress = 0.1
                else:
                    self.research_progress = _clamp_ratio(self.research_progress + 0.1)
                reward += 0.3
            elif isinstance(validated_action, SetWorkPrioritiesAction):
                self._work_priorities = {
                    assignment.work_type: assignment.priority for assignment in validated_action.payload.priorities
                }
                if any(assignment.work_type == "doctor" and assignment.priority <= 2 for assignment in validated_action.payload.priorities):
                    self.injury_burden = _clamp_ratio(self.injury_burden - 0.05)
                if any(assignment.work_type == "grower" and assignment.priority <= 2 for assignment in validated_action.payload.priorities):
                    self.food += 1
                reward += 0.25
            elif isinstance(validated_action, EnforceColonistCapAction):
                self.colonist_cap = validated_action.payload.colonist_cap
                reward += 0.1
            elif isinstance(validated_action, PauseAction):
                self.paused = True
                self.game_speed = GameSpeed.paused
                reward += 0.05
            elif isinstance(validated_action, ResumeAction):
                self.paused = False
                if self.game_speed == GameSpeed.paused:
                    self.game_speed = GameSpeed.normal
                reward += 0.05

            self._update_terminal_state()

        observation = self.get_observation()
        info = {
            "backend": self.backend_name,
            "terminal_reason": self._terminal_reason,
            "action_type": validated_action.type,
        }
        return EnvStepResult(observation=observation, reward=reward, done=self.is_terminal(), info=info)

    def reset(self) -> Observation:
        return self.reset_run()

    def step(self, action: EnvironmentAction) -> EnvStepResult:
        return self.apply_action(action)

    def is_terminal(self) -> bool:
        return self._terminal_reason != "in_progress"

    def get_terminal_reason(self) -> str:
        return self._terminal_reason

    def close(self) -> None:
        self.disconnect()
