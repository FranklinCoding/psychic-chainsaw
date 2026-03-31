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

    def connect(self) -> None:
        """Open any backend connections needed before a run."""

    def disconnect(self) -> None:
        """Close any backend connections after a run."""

    def reset_run(self) -> Mapping[str, Any]:
        """Reset environment state for a new run."""

    def get_observation(self) -> Mapping[str, Any]:
        """Return latest observation snapshot."""

    def apply_action(self, action: Mapping[str, Any]) -> EnvStepResult:
        """Apply an action during a run."""

    def is_terminal(self) -> bool:
        """Whether the current run reached terminal state."""

    def get_terminal_reason(self) -> str:
        """Machine-readable terminal reason for the current run."""


class TrainerPolicy(Protocol):
    """Policy interface to keep trainer independent from backend implementation."""

    def select_action(self, observation: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return action for current observation."""
