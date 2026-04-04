from __future__ import annotations

from trainer.environment.base_env import BaseEnvironmentAdapter
from trainer.interfaces import EnvStepResult, SharedActionInput
from trainer.schemas.normalization import normalize_action, normalize_observation
from trainer.schemas.observation import SharedObservation


class MockEnvironmentAdapter(BaseEnvironmentAdapter):
    """Simple deterministic backend for local development and CI."""

    backend_name = "mock"

    def __init__(self, max_steps: int = 5) -> None:
        self.max_steps = max_steps
        self.current_step = 0
        self.food_reserves = 20.0
        self.game_speed = "normal"

    def reset(self) -> SharedObservation:
        self.current_step = 0
        self.food_reserves = 20.0
        self.game_speed = "normal"
        return self._make_observation()

    def step(self, action: SharedActionInput) -> EnvStepResult:
        typed_action = normalize_action(action)
        self.current_step += 1

        reward = 0.1
        action_type = typed_action.action_type

        if action_type == "set_food_priority":
            self.food_reserves += 1.5 if typed_action.level >= 3 else -1.0
            reward = 0.7 if typed_action.level >= 3 else -0.3
        elif action_type == "set_speed":
            self.game_speed = typed_action.speed
        elif action_type == "pause":
            self.game_speed = "paused"
        elif action_type == "resume":
            self.game_speed = "normal"
        elif action_type == "request_restart":
            self.current_step = self.max_steps

        self.food_reserves = max(self.food_reserves - 0.5, 0.0)
        observation = self._make_observation()
        done = self.current_step >= self.max_steps or self.food_reserves <= 0
        info = {"action_type": action_type, "backend": self.backend_name}
        return EnvStepResult(observation=observation, reward=reward, done=done, info=info)

    def _make_observation(self) -> SharedObservation:
        progress = min(self.current_step / max(self.max_steps, 1), 1.0)
        mood_risk = max(0.0, min(1.0, 0.6 - self.food_reserves / 40.0))
        health_risk = max(0.0, min(1.0, 0.5 - self.food_reserves / 50.0))

        payload = {
            "colonists": 3,
            "colonist_status_summary": "stable",
            "food_reserve": self.food_reserves,
            "medicine_reserves": 8.0,
            "colony_wealth": 1200.0,
            "mood_risk": mood_risk,
            "health_risk": health_risk,
            "injury_burden": 0.1,
            "threat_level": 0.2 if self.current_step % 2 == 0 else 0.1,
            "research_status": {
                "current_research": "microelectronics",
                "progress": progress,
                "is_active": True,
            },
            "run_time_seconds": float(self.current_step * 5),
            "step": self.current_step,
            "game_speed": self.game_speed,
            "progress_indicators": {
                "episode_progress": progress,
                "objective_progress": min(progress * 0.8, 1.0),
            },
            "failure_risk_indicators": {
                "starvation_risk": max(0.0, min(1.0, 1.0 - self.food_reserves / 30.0)),
                "raid_risk": 0.25,
                "mental_break_risk": mood_risk,
            },
        }
        return normalize_observation(payload)
