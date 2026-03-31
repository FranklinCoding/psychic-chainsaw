from __future__ import annotations

import argparse
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
    terminal_reason: str = "not_started"
    final_colonists: int = 0
    final_food: int = 0
    final_medicine: int = 0


class SimplePolicy(TrainerPolicy):
    """Minimal policy that prefers gathering food when reserves are low."""

    def select_action(self, observation: Mapping[str, Any]) -> Mapping[str, Any]:
        food = int(observation.get("food", observation.get("food_reserve", 0)))
        medicine = int(observation.get("medicine", 0))
        step = int(observation.get("step", 0))
        if food < 10:
            return {"type": "gather_food"}
        if medicine > 0 and step % 5 == 0:
            return {"type": "use_medicine"}
        return {"type": "wait"}


def run_training_loop(config: TrainerConfig, max_steps: int = 10) -> LoopStats:
    env = create_environment(config)
    policy = SimplePolicy()

    stats = LoopStats(terminal_reason="in_progress")

    env.connect()
    observation = env.reset_run()

    try:
        while stats.steps < max_steps:
            action = policy.select_action(observation)
            step_result = env.apply_action(action)

            stats.steps += 1
            stats.total_reward += step_result.reward
            observation = step_result.observation
            stats.final_colonists = int(observation.get("colonists", 0))
            stats.final_food = int(observation.get("food", observation.get("food_reserve", 0)))
            stats.final_medicine = int(observation.get("medicine", 0))

            done = bool(env.is_terminal() or step_result.done)
            if env.get_terminal_reason() != "unknown":
                stats.terminal_reason = str(env.get_terminal_reason())
            else:
                stats.terminal_reason = str(step_result.info.get("terminal_reason", "completed"))

            if done:
                stats.completed = True
                break
    finally:
        env.close()

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run trainer with a selected configuration profile")
    parser.add_argument(
        "--profile",
        help="Profile name from config/profiles (e.g., mock, rimapi, rimbridge)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(profile=args.profile)
    stats = run_training_loop(config)
    print(
        f"backend={config.bridge_backend} steps={stats.steps} total_reward={stats.total_reward:.2f} "
        f"completed={stats.completed} terminal_reason={stats.terminal_reason} "
        f"final_colonists={stats.final_colonists} final_food={stats.final_food} "
        f"final_medicine={stats.final_medicine}"
    )


if __name__ == "__main__":
    main()
