import pytest
from pydantic import ValidationError

from trainer.environment.mock_env import MockEnvironmentAdapter
from trainer.schemas.action import SHARED_ACTION_ADAPTER
from trainer.schemas.observation import SharedObservation


def test_observation_model_creation_and_validation() -> None:
    observation = SharedObservation(
        colonist_count=4,
        colonist_status_summary="healthy",
        food_reserves=25,
        medicine_reserves=10,
        colony_wealth=3200,
    )

    assert observation.colonist_count == 4
    assert observation.food_reserves == 25

    with pytest.raises(ValidationError):
        SharedObservation(
            colonist_count=-1,
            colonist_status_summary="bad",
            food_reserves=1,
            medicine_reserves=1,
            colony_wealth=1,
        )


def test_action_model_creation_and_validation() -> None:
    action = SHARED_ACTION_ADAPTER.validate_python(
        {"action_type": "set_speed", "speed": "fast"}
    )
    assert action.action_type == "set_speed"

    with pytest.raises(ValidationError):
        SHARED_ACTION_ADAPTER.validate_python(
            {"action_type": "set_food_priority", "level": 9}
        )


def test_mock_environment_produces_valid_shared_observations() -> None:
    env = MockEnvironmentAdapter(max_steps=3)
    observation = env.reset()
    assert isinstance(observation, SharedObservation)

    result = env.step(SHARED_ACTION_ADAPTER.validate_python({"action_type": "pause"}))
    assert isinstance(result.observation, SharedObservation)
    assert result.observation.step_count == 1


def test_mock_environment_executes_shared_actions() -> None:
    env = MockEnvironmentAdapter(max_steps=3)
    env.reset()

    action = SHARED_ACTION_ADAPTER.validate_python(
        {"action_type": "set_food_priority", "level": 5}
    )
    result = env.step(action)

    assert result.info["action_type"] == "set_food_priority"
    assert result.reward > 0
    assert result.observation.food_reserves > 20
