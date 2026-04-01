from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from typing import Any

from trainer.config import TrainerConfig, load_config
from trainer.environment.bridge_factory import create_environment
from trainer.failure_detection import FailureAssessment, FailureDetector
from trainer.interfaces import TrainerPolicy
from trainer.schemas import (
    ChooseResearchAction,
    EnvironmentAction,
    GameSpeed,
    Observation,
    PriorityLevel,
    SetFoodPriorityAction,
    SetMedicalPriorityAction,
    SetSpeedAction,
    SpeedPayload,
    WaitAction,
    ResearchChoicePayload,
    ResourcePriorityPayload,
)


@dataclass(slots=True)
class LoopStats:
    backend: str = "unknown"
    steps: int = 0
    total_reward: float = 0.0
    completed: bool = False
    terminal_reason: str = "not_started"
    terminal_details: dict[str, Any] = field(default_factory=dict)
    final_colonists: int = 0
    final_food: int = 0
    final_medicine: int = 0


class SimplePolicy(TrainerPolicy):
    """Minimal policy that adjusts shared priorities based on typed observations."""

    def select_action(self, observation: Observation) -> EnvironmentAction:
        if observation.step_count == 0:
            return SetSpeedAction(payload=SpeedPayload(speed=GameSpeed.fast))
        if observation.food < 12:
            return SetFoodPriorityAction(payload=ResourcePriorityPayload(priority=PriorityLevel.high))
        if observation.health_risk >= 0.3 and observation.medicine > 0:
            return SetMedicalPriorityAction(payload=ResourcePriorityPayload(priority=PriorityLevel.high))
        if observation.step_count == 2 and observation.research_state.current_project != "microelectronics":
            return ChooseResearchAction(payload=ResearchChoicePayload(project="microelectronics"))
        return WaitAction()


def _record_final_observation(stats: LoopStats, observation: Observation) -> None:
    stats.final_colonists = observation.colonist_count
    stats.final_food = observation.food
    stats.final_medicine = observation.medicine


def _finalize_failure_terminal(
    stats: LoopStats,
    assessment: FailureAssessment,
) -> None:
    stats.completed = True
    stats.terminal_reason = assessment.terminal_reason.code
    stats.terminal_details = assessment.terminal_reason.as_dict()


def run_training_loop(config: TrainerConfig, max_steps: int = 10) -> LoopStats:
    env = create_environment(config)
    policy = SimplePolicy()
    detector = FailureDetector(config)

    stats = LoopStats(backend=env.backend_name, terminal_reason="in_progress", terminal_details={})

    env.connect()
    observation = env.reset_run()
    _record_final_observation(stats, observation)
    initial_assessment = detector.assess(observation)

    try:
        if initial_assessment.should_terminate:
            _finalize_failure_terminal(stats, initial_assessment)
            return stats

        while stats.steps < max_steps:
            action = policy.select_action(observation)
            step_result = env.apply_action(action)

            stats.steps += 1
            stats.total_reward += step_result.reward
            observation = step_result.observation
            _record_final_observation(stats, observation)

            failure_assessment = detector.assess(observation)
            step_result.info["failure_assessment"] = failure_assessment.as_dict()
            if failure_assessment.should_terminate and failure_assessment.terminal_reason is not None:
                step_result.info["terminal_reason"] = failure_assessment.terminal_reason.code
                step_result.info["terminal_details"] = failure_assessment.terminal_reason.as_dict()

            done = bool(env.is_terminal() or step_result.done or failure_assessment.should_terminate)
            if failure_assessment.should_terminate and failure_assessment.terminal_reason is not None:
                _finalize_failure_terminal(stats, failure_assessment)
            elif done and env.get_terminal_reason() not in {"unknown", "in_progress"}:
                stats.completed = True
                stats.terminal_reason = str(env.get_terminal_reason())
                stats.terminal_details = {
                    "category": "environment",
                    "code": str(env.get_terminal_reason()),
                    "summary": str(step_result.info.get("terminal_reason", env.get_terminal_reason())),
                }
            elif done:
                stats.completed = True
                stats.terminal_reason = str(step_result.info.get("terminal_reason", "completed"))
                stats.terminal_details = step_result.info.get("terminal_details", {})
            else:
                stats.terminal_reason = "in_progress"

            if done:
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
        f"backend={stats.backend} steps={stats.steps} total_reward={stats.total_reward:.2f} "
        f"completed={stats.completed} terminal_reason={stats.terminal_reason} "
        f"final_colonists={stats.final_colonists} final_food={stats.final_food} "
        f"final_medicine={stats.final_medicine}"
    )


if __name__ == "__main__":
    main()
