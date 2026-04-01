import pytest
from pydantic import ValidationError

from trainer.environment.mock_env import MockEnvironmentAdapter
from trainer.schemas import (
    FailureRiskIndicators,
    GameSpeed,
    Observation,
    PauseAction,
    PriorityLevel,
    ProgressIndicators,
    RequestRestartAction,
    ResearchState,
    ResourcePriorityPayload,
    SetFoodPriorityAction,
    SetSpeedAction,
    validate_action,
)


def test_observation_model_creation_and_validation() -> None:
    observation = Observation(
        colonist_count=3,
        colonist_status_summary={"healthy": 2, "injured": 1, "downed": 0, "mental_break_risk": 0},
        food=18,
        medicine=4,
        colony_wealth=1400.0,
        mood_risk=0.2,
        health_risk=0.15,
        injury_burden=0.1,
        threat_level=0.3,
        research_state=ResearchState(current_project="battery", progress=0.4, completed=False),
        step_count=5,
        game_speed=GameSpeed.fast,
        progress=ProgressIndicators(run_completion=0.5, colony_development=0.6, research_completion=0.4),
        failure_risk=FailureRiskIndicators(starvation=0.1, medical=0.15, mood_break=0.2, restart=0.2),
    )

    assert observation.colonist_count == 3
    assert observation.game_speed is GameSpeed.fast
    assert observation.research_state.current_project == "battery"

    with pytest.raises(ValidationError):
        Observation(
            colonist_count=-1,
            colonist_status_summary={"healthy": 0, "injured": 0, "downed": 0, "mental_break_risk": 0},
            food=0,
            medicine=0,
            colony_wealth=0.0,
            mood_risk=0.0,
            health_risk=0.0,
            injury_burden=0.0,
            threat_level=0.0,
            research_state=ResearchState(current_project=None, progress=0.0, completed=False),
            step_count=0,
            progress=ProgressIndicators(run_completion=0.0, colony_development=0.0, research_completion=0.0),
            failure_risk=FailureRiskIndicators(starvation=0.0, medical=0.0, mood_break=0.0, restart=0.0),
        )


def test_action_model_creation_and_validation() -> None:
    action = validate_action({"type": "set_speed", "payload": {"speed": "fast"}})

    assert isinstance(action, SetSpeedAction)
    assert action.payload.speed is GameSpeed.fast

    research_action = validate_action({"type": "choose_research", "payload": {"project": "microelectronics"}})
    assert research_action.type == "choose_research"

    with pytest.raises(ValidationError):
        validate_action({"type": "unsupported_action", "payload": {}})


def test_mock_environment_produces_valid_observations() -> None:
    env = MockEnvironmentAdapter()

    observation = env.reset_run()

    assert isinstance(observation, Observation)
    assert observation.colonist_count == 3
    assert observation.progress.run_completion == 0.0
    assert observation.metadata["backend"] == "mock"


def test_mock_environment_handles_actions_correctly() -> None:
    env = MockEnvironmentAdapter()
    env.reset_run()

    food_before = env.get_observation().food
    food_step = env.apply_action(SetFoodPriorityAction(payload=ResourcePriorityPayload(priority=PriorityLevel.high)))

    assert food_step.observation.food > food_before
    assert food_step.info["action_type"] == "set_food_priority"

    paused_step = env.apply_action(PauseAction())
    assert paused_step.observation.game_speed is GameSpeed.paused
    assert paused_step.observation.metadata["paused"] is True

    restart_step = env.apply_action(RequestRestartAction())
    assert restart_step.done is True
    assert env.get_terminal_reason() == "restart_requested"
