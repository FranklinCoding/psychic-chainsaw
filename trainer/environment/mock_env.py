from __future__ import annotations

from typing import Any, Mapping

from trainer.environment.base_env import BaseEnvironmentAdapter
from trainer.interfaces import EnvStepResult


class MockEnvironmentAdapter(BaseEnvironmentAdapter):
    """Simple deterministic backend for local development and CI."""

    backend_name = "mock"

    def __init__(self, max_steps: int = 8) -> None:
        self.max_steps = max_steps
        self.current_step = 0
        self.colonists = 0
        self.food = 0
        self.medicine = 0
        self.connected = False
        self._terminal_reason = "not_started"

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def reset_run(self) -> Mapping[str, Any]:
        self.current_step = 0
        self.colonists = 3
        self.food = 16
        self.medicine = 5
        self._terminal_reason = "in_progress"
        return self.get_observation()

    def get_observation(self) -> Mapping[str, Any]:
        return {
            "step": self.current_step,
            "colonists": self.colonists,
            "food": self.food,
            "food_reserve": self.food,
            "medicine": self.medicine,
        }

    def apply_action(self, action: Mapping[str, Any]) -> EnvStepResult:
        self.current_step += 1
        action_type = str(action.get("type", "wait"))
        reward = 0.0

        # baseline upkeep
        self.food -= 1

        if action_type in {"gather_food", "forage"}:
            self.food += 3
            reward += 1.0
        elif action_type in {"use_medicine", "tend"} and self.medicine > 0:
            self.medicine -= 1
            reward += 0.4
        elif action_type in {"recruit"} and self.current_step in {3, 6} and self.food >= 10:
            self.colonists += 1
            self.food -= 2
            reward += 0.8
        else:
            reward += 0.1

        if self.current_step == 4:
            self.colonists += 1

        if self.food <= 0:
            self._terminal_reason = "food_depleted"
        elif self.colonists <= 0:
            self._terminal_reason = "colony_lost"
        elif self.current_step >= self.max_steps:
            self._terminal_reason = "max_steps_reached"
        else:
            self._terminal_reason = "in_progress"

        observation = self.get_observation()
        info = {
            "backend": self.backend_name,
            "terminal_reason": self._terminal_reason,
            "action_type": action_type,
        }
        return EnvStepResult(observation=observation, reward=reward, done=self.is_terminal(), info=info)

    def reset(self) -> Mapping[str, Any]:
        return self.reset_run()

    def step(self, action: Mapping[str, Any]) -> EnvStepResult:
        step_result = self.apply_action(action)
        return step_result

    def is_terminal(self) -> bool:
        return self._terminal_reason != "in_progress"

    def get_terminal_reason(self) -> str:
        return self._terminal_reason

    def close(self) -> None:
        self.disconnect()
