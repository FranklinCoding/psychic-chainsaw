from __future__ import annotations

from trainer.config import RimBridgeBackendConfig
from trainer.environment.base_env import BaseEnvironmentAdapter
from trainer.environment.rimbridge.client import RimBridgeClient
from trainer.environment.rimbridge.mapper import map_rimbridge_observation, parse_rimbridge_capabilities
from trainer.interfaces import EnvStepResult
from trainer.schemas import (
    BridgeCapabilities,
    EnvironmentAction,
    GameSpeed,
    Observation,
    PauseAction,
    RequestRestartAction,
    ResumeAction,
    SetSpeedAction,
    WaitAction,
    validate_action,
)

_RIMBRIDGE_SPEEDS: dict[GameSpeed, str] = {
    GameSpeed.paused: "Paused",
    GameSpeed.normal: "Normal",
    GameSpeed.fast: "Fast",
    GameSpeed.superfast: "Superfast",
}


class RimBridgeServerAdapter(BaseEnvironmentAdapter):
    """Direct-capable adapter for RimBridgeServer's GABP surface."""

    backend_name = "rimbridge"

    def __init__(self, settings: RimBridgeBackendConfig, client: RimBridgeClient | None = None) -> None:
        self.settings = settings
        self.client = client or RimBridgeClient(settings)
        self.connected = False
        self._session_info: dict[str, object] = {}
        self._tool_descriptors: list[dict[str, object]] = []
        self._capability_descriptors: list[dict[str, object]] = []
        self._capabilities = BridgeCapabilities(metadata={"backend_family": "gabp"})
        self._last_observation: Observation | None = None

    def reset(self) -> Observation:
        observation = self.get_observation()
        self._last_observation = observation
        return observation

    def step(self, action: EnvironmentAction) -> EnvStepResult:
        return self.apply_action(action)

    def connect(self) -> None:
        self._session_info = self.client.connect()
        self._tool_descriptors = self.client.list_tools()
        self._capability_descriptors = self.client.list_capabilities()
        self._capabilities = parse_rimbridge_capabilities(
            session_info=self._session_info,
            tool_descriptors=self._tool_descriptors,
            capability_descriptors=self._capability_descriptors,
        )
        self.connected = True

    def disconnect(self) -> None:
        self.client.close()
        self.connected = False

    def get_capabilities(self) -> BridgeCapabilities:
        return self._capabilities

    def get_observation(self) -> Observation:
        if not self.connected:
            self.connect()

        bridge_status = self.client.get_bridge_status()
        game_info = self.client.get_game_info()
        colonists = self.client.list_colonists() if self.get_capabilities().can_read_colonists else []
        alerts = self.client.list_alerts()
        messages = self.client.list_messages()

        observation = map_rimbridge_observation(
            bridge_status=bridge_status,
            game_info=game_info,
            colonists=colonists,
            alerts=alerts,
            messages=messages,
            capabilities=self.get_capabilities(),
            capability_descriptors=self._capability_descriptors,
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
            self.client.set_time_speed(_RIMBRIDGE_SPEEDS[validated_action.payload.speed])
        elif isinstance(validated_action, PauseAction):
            self.client.pause_game(True)
        elif isinstance(validated_action, ResumeAction):
            self.client.pause_game(False)
        elif isinstance(validated_action, RequestRestartAction):
            if self.get_capabilities().can_restart_run:
                self.client.go_to_main_menu()
                self.client.start_debug_game()
            else:
                return self.unsupported_action_result(validated_action)
        else:
            return self.unsupported_action_result(
                validated_action,
                reason=(
                    "RimBridgeServer integration currently supports observation polling plus pause/speed/reset controls only; "
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
