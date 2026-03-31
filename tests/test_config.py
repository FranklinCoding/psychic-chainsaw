from trainer.config import TrainerConfig, load_config


def test_load_default_config() -> None:
    config = load_config()

    assert isinstance(config, TrainerConfig)
    assert config.bridge_backend == "mock"
    assert config.backends.rimapi.base_url.startswith("http")
    assert config.backends.rimbridge.base_url.startswith("http")


def test_load_mock_profile() -> None:
    config = load_config(profile="mock")
    assert config.bridge_backend == "mock"
