from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, TypeAlias

from trainer.schemas.action import SharedAction
from trainer.schemas.observation import SharedObservation

SharedObservationInput: TypeAlias = SharedObservation | Mapping[str, Any]
SharedActionInput: TypeAlias = SharedAction | Mapping[str, Any]


@dataclass(slots=True)
class EnvStepResult:
    """Represents one environment transition."""

    observation: SharedObservation
    reward: float
    done: bool
    info: Mapping[str, Any] = field(default_factory=dict)


class EnvironmentAdapter(Protocol):
    """Shared interface each backend adapter must implement."""

    backend_name: str

    def reset(self) -> SharedObservation:
        """Start or restart an episode and return initial observation."""

    def step(self, action: SharedActionInput) -> EnvStepResult:
        """Apply action and return transition data."""

    def close(self) -> None:
        """Clean up backend resources."""


class TrainerPolicy(Protocol):
    """Policy interface to keep trainer independent from backend implementation."""

    def select_action(self, observation: SharedObservationInput) -> SharedActionInput:
        """Return action for current observation."""
