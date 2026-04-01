import os

import pytest

from trainer.config import TrainerConfig, load_config


def test_load_default_config() -> None:
    config = load_config()

    assert isinstance(config, TrainerConfig)
    assert config.bridge_backend == "mock"
    assert config.backends.rimapi.base_url.startswith("http")
    assert config.backends.rimbridge.base_url.startswith("http")


def test_load_mock_profile_merges_with_default() -> None:
    config = load_config(profile="mock")

    assert config.bridge_backend == "mock"
    assert config.policy.max_colonists == 4
    assert config.training.checkpoint_frequency == 10


def test_load_rimapi_profile_merges_with_default() -> None:
    config = load_config(profile="rimapi")

    assert config.bridge_backend == "rimapi"
    assert config.training.training_mode is False
    assert config.training.evaluation_mode is True
    assert config.policy.max_colonists == 8
    assert config.backends.rimapi.base_url.startswith("http")


def test_load_rimbridge_profile_merges_with_default() -> None:
    config = load_config(profile="rimbridge")

    assert config.bridge_backend == "rimbridge"
    assert config.training.checkpoint_frequency == 5
    assert config.policy.max_colonists == 10
    assert config.training.max_run_duration_minutes == 60


def test_load_config_works_outside_repo_cwd(tmp_path) -> None:
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        config = load_config(profile="mock")
    finally:
        os.chdir(original_cwd)

    assert config.bridge_backend == "mock"


def test_load_config_unknown_profile_raises_clear_error() -> None:
    with pytest.raises(FileNotFoundError, match="Config profile not found"):
        load_config(profile="does-not-exist")
