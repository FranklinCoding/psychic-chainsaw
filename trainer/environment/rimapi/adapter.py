from __future__ import annotations

from trainer.config import RimAPIBackendConfig
from trainer.environment.base_env import BaseEnvironmentAdapter
from trainer.environment.rimapi.client import RimAPIClient
from trainer.environment.rimapi.mapper import map_rimapi_observation, parse_rimapi_capabilities
from trainer.interfaces import EnvStepResult
from trainer.schemas import (
    BridgeCapabilities,
    EnvironmentAction,
    GameSpeed,
    Observation,
    PauseAction,
    ResumeAction,
    SetSpeedAction,
    WaitAction,
    validate_action,
)

_RIMAPI_SPEEDS: dict[GameSpeed, int] = {
    GameSpeed.paused: 0,
    GameSpeed.normal: 1,
    GameSpeed.fast: 2,
    GameSpeed.superfast: 3,
}


class RimAPIAdapter(BaseEnvironmentAdapter):
    """Capability-aware adapter for the RIMAPI REST bridge."""

    backend_name = "rimapi"

    def __init__(self, settings: RimAPIBackendConfig, client: RimAPIClient | None = None) -> None:
        self.settings = settings
        self.client = client or RimAPIClient(settings)
        self.connected = False
        self._version_info: dict[str, object] = {}
        self._capabilities = parse_rimapi_capabilities()
        self._last_observation: Observation | None = None

    def reset(self) -> Observation:
        if self.settings.start_new_game_on_reset and self.get_capabilities().can_start_new_game:
            self.client.start_new_game_devquick()
        observation = self.get_observation()
        self._last_observation = observation
        return observation

    def step(self, action: EnvironmentAction) -> EnvStepResult:
        return self.apply_action(action)

    def connect(self) -> None:
        self._version_info = self.client.connect()
        self.connected = True

    def disconnect(self) -> None:
        self.client.close()
        self.connected = False

    def get_capabilities(self) -> BridgeCapabilities:
        return self._capabilities

    def get_observation(self) -> Observation:
        if not self.connected:
            self.connect()

        game_state = self.client.get_game_state()
        colonists = self.client.get_colonists_detailed()
        resources_summary = self.client.get_resources_summary()
        research_state = self.client.get_research_state()

        observation = map_rimapi_observation(
            game_state=game_state,
            colonists=colonists,
            resources_summary=resources_summary,
            research_state_payload=research_state,
            capabilities=self.get_capabilities(),
            backend_metadata={"version_info": dict(self._version_info)},
        )
        self._last_observation = observation
        return observation

    def apply_action(self, action: EnvironmentAction) -> EnvStepResult:
        validated_action = validate_action(action)

        if isinstance(validated_action, WaitAction):
            observation = self.get_observation()
            return EnvStepResult(
                observation=observation,
                reward=0.0,
                done=False,
                info={"backend": self.backend_name, "action_type": validated_action.type, "status": "polled"},
            )

        if not self.supports_action(validated_action):
            return self.unsupported_action_result(validated_action)

        if isinstance(validated_action, SetSpeedAction):
            self.client.set_game_speed(_RIMAPI_SPEEDS[validated_action.payload.speed])
        elif isinstance(validated_action, PauseAction):
            self.client.set_game_speed(_RIMAPI_SPEEDS[GameSpeed.paused])
        elif isinstance(validated_action, ResumeAction):
            self.client.set_game_speed(_RIMAPI_SPEEDS[GameSpeed.normal])
        else:
            return self.unsupported_action_result(
                validated_action,
                reason=(
                    f"RIMAPI integration currently supports observation polling and speed control only; "
                    f"'{validated_action.type}' is intentionally degraded."
                ),
            )

        observation = self.get_observation()
        return EnvStepResult(
            observation=observation,
            reward=0.0,
            done=False,
            info={"backend": self.backend_name, "action_type": validated_action.type, "status": "applied"},
        )
