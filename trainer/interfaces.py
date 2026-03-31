from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


@dataclass(slots=True)
class EnvStepResult:
    """Represents one environment transition."""

    observation: Mapping[str, Any]
    reward: float
    done: bool
    info: Mapping[str, Any] = field(default_factory=dict)


class EnvironmentAdapter(Protocol):
    """Shared interface each backend adapter must implement."""

    backend_name: str

    def reset(self) -> Mapping[str, Any]:
        """Start or restart an episode and return initial observation."""

    def step(self, action: Mapping[str, Any]) -> EnvStepResult:
        """Apply action and return transition data."""

    def close(self) -> None:
        """Clean up backend resources."""


class TrainerPolicy(Protocol):
    """Policy interface to keep trainer independent from backend implementation."""

    def select_action(self, observation: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return action for current observation."""
