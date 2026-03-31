from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from trainer.config import TrainerConfig, load_config
from trainer.environment.bridge_factory import create_environment
from trainer.interfaces import TrainerPolicy


@dataclass(slots=True)
class LoopStats:
    steps: int = 0
    total_reward: float = 0.0
    completed: bool = False


class SimplePolicy(TrainerPolicy):
    """Minimal policy that prefers gathering food when reserves are low."""

    def select_action(self, observation: Mapping[str, Any]) -> Mapping[str, Any]:
        if int(observation.get("food_reserve", 0)) < 20:
            return {"type": "gather_food"}
        return {"type": "wait"}


def run_training_loop(config: TrainerConfig, max_steps: int = 10) -> LoopStats:
    env = create_environment(config)
    policy = SimplePolicy()

    stats = LoopStats()
    observation = env.reset()

    try:
        while stats.steps < max_steps:
            action = policy.select_action(observation)
            step_result = env.step(action)

            stats.steps += 1
            stats.total_reward += step_result.reward
            observation = step_result.observation

            if step_result.done:
                stats.completed = True
                break
    finally:
        env.close()

    return stats


def main() -> None:
    config = load_config()
    stats = run_training_loop(config)
    print(
        f"backend={config.bridge_backend} steps={stats.steps} "
        f"total_reward={stats.total_reward:.2f} completed={stats.completed}"
    )


if __name__ == "__main__":
    main()
