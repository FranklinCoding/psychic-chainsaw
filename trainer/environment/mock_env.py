from __future__ import annotations

from typing import Any, Mapping

from trainer.environment.base_env import BaseEnvironmentAdapter
from trainer.interfaces import EnvStepResult


class MockEnvironmentAdapter(BaseEnvironmentAdapter):
    """Simple deterministic backend for local development and CI."""

    backend_name = "mock"

    def __init__(self, max_steps: int = 5) -> None:
        self.max_steps = max_steps
        self.current_step = 0
        self.food_reserve = 20

    def reset(self) -> Mapping[str, Any]:
        self.current_step = 0
        self.food_reserve = 20
        return {
            "step": self.current_step,
            "food_reserve": self.food_reserve,
            "colonists": 3,
            "threat_level": 0.0,
        }

    def step(self, action: Mapping[str, Any]) -> EnvStepResult:
        self.current_step += 1
        action_type = str(action.get("type", "wait"))

        if action_type == "gather_food":
            self.food_reserve += 2
            reward = 1.0
        elif action_type == "consume_food":
            self.food_reserve -= 3
            reward = -0.5
        else:
            self.food_reserve -= 1
            reward = 0.1

        done = self.current_step >= self.max_steps or self.food_reserve <= 0
        observation = {
            "step": self.current_step,
            "food_reserve": self.food_reserve,
            "colonists": 3,
            "threat_level": 0.1 if self.current_step % 2 == 0 else 0.0,
        }
        info = {"action_type": action_type, "backend": self.backend_name}
        return EnvStepResult(observation=observation, reward=reward, done=done, info=info)
