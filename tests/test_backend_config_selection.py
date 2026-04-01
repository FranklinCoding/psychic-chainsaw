from __future__ import annotations

import pytest

from trainer.config import load_config
from trainer.environment.errors import BackendConnectionError
from trainer.environment.bridge_factory import create_environment
from trainer.environment.rimapi.adapter import RimAPIAdapter
from trainer.environment.rimbridge.client import RimBridgeClient
from trainer.environment.rimbridge.adapter import RimBridgeServerAdapter


def test_bridge_factory_uses_rimapi_settings_from_selected_profile() -> None:
    config = load_config(profile="rimapi")

    env = create_environment(config)

    assert isinstance(env, RimAPIAdapter)
    assert env.settings.base_url == "http://127.0.0.1:8765"
    assert env.settings.timeout_seconds == 10
    assert env.settings.map_id == 0


def test_bridge_factory_uses_rimbridge_settings_from_selected_profile() -> None:
    config = load_config(profile="rimbridge")

    env = create_environment(config)

    assert isinstance(env, RimBridgeServerAdapter)
    assert env.settings.host == "127.0.0.1"
    assert env.settings.config_path == "%APPDATA%\\gabp\\bridge.json"
    assert env.settings.transport == "auto"


def test_rimbridge_client_reports_missing_config_path_clearly(tmp_path) -> None:
    config = load_config(profile="rimbridge")
    config.backends.rimbridge.config_path = str(tmp_path / "missing-bridge.json")

    client = RimBridgeClient(config.backends.rimbridge)

    with pytest.raises(BackendConnectionError, match="config file not found"):
        client.connect()
