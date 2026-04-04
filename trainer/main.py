from __future__ import annotations

from dataclasses import dataclass

from trainer.config import TrainerConfig, load_config
from trainer.environment.bridge_factory import create_environment
from trainer.interfaces import TrainerPolicy
from trainer.schemas.action import SetFoodPriorityAction, SetSpeedAction, SharedAction
from trainer.schemas.observation import SharedObservation


@dataclass(slots=True)
class LoopStats:
    steps: int = 0
    total_reward: float = 0.0
    completed: bool = False


class SimplePolicy(TrainerPolicy):
    """Minimal policy that prioritizes food stability in mock mode."""

    def select_action(self, observation: SharedObservation) -> SharedAction:
        if observation.food_reserves < 20:
            return SetFoodPriorityAction(action_type="set_food_priority", level=4)
        return SetSpeedAction(action_type="set_speed", speed="normal")


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
