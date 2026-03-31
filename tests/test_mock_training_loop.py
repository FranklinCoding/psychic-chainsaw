from trainer.config import load_config
from trainer.main import run_training_loop


def test_mock_training_loop_runs_to_completion() -> None:
    config = load_config()
    config.bridge_backend = "mock"

    stats = run_training_loop(config=config, max_steps=10)

    assert stats.completed is True
    assert stats.steps > 0
    assert stats.steps <= 10
