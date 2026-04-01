from __future__ import annotations

from trainer.interfaces import EnvStepResult
from trainer.schemas import BridgeCapabilities, EnvironmentAction, Observation, validate_action

_ACTION_CAPABILITY_FLAGS: dict[str, str] = {
    "set_speed": "can_set_speed",
    "pause": "can_set_speed",
    "resume": "can_set_speed",
    "request_restart": "can_restart_run",
    "set_work_priorities": "can_set_work_priorities",
    "choose_research": "can_choose_research",
    "set_combat_posture": "can_control_alert_posture",
}


class BaseEnvironmentAdapter:
    """Optional convenience base class for adapter implementations."""

    backend_name = "base"

    def reset(self) -> Observation:
        raise NotImplementedError

    def step(self, action: EnvironmentAction) -> EnvStepResult:
        raise NotImplementedError

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def reset_run(self) -> Observation:
        return self.reset()

    def get_observation(self) -> Observation:
        raise NotImplementedError

    def get_capabilities(self) -> BridgeCapabilities:
        return BridgeCapabilities()

    def apply_action(self, action: EnvironmentAction) -> EnvStepResult:
        return self.step(action)

    def supports_action(self, action: EnvironmentAction) -> bool:
        validated_action = validate_action(action)
        capability_flag = _ACTION_CAPABILITY_FLAGS.get(validated_action.type)
        if capability_flag is None:
            return True
        return bool(getattr(self.get_capabilities(), capability_flag, False))

    def unsupported_action_result(self, action: EnvironmentAction, reason: str | None = None) -> EnvStepResult:
        validated_action = validate_action(action)
        message = reason or f"Action '{validated_action.type}' is not supported by backend '{self.backend_name}'."
        return EnvStepResult(
            observation=self.get_observation(),
            reward=0.0,
            done=self.is_terminal(),
            info={
                "backend": self.backend_name,
                "action_type": validated_action.type,
                "status": "unsupported",
                "reason": message,
                "capabilities": self.get_capabilities().model_dump(mode="python"),
            },
        )

    def is_terminal(self) -> bool:
        return False

    def get_terminal_reason(self) -> str:
        return "unknown"

    def close(self) -> None:
        self.disconnect()
