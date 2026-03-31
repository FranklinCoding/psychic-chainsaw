import subprocess
import sys

from trainer.config import load_config
from trainer.main import run_training_loop


def test_mock_training_loop_runs_to_completion() -> None:
    config = load_config(profile="mock")

    stats = run_training_loop(config=config, max_steps=10)

    assert stats.completed is True
    assert stats.steps > 0
    assert stats.steps <= 10
    assert stats.terminal_reason == "max_steps_reached"
    assert stats.final_colonists >= 4
    assert stats.final_food > 0


def test_mock_main_smoke_profile_run() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "trainer.main", "--profile", "mock"],
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    assert "backend=mock" in output
    assert "terminal_reason=max_steps_reached" in output
    assert "final_colonists=" in output
