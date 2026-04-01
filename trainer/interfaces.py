from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from trainer.schemas import EnvironmentAction, Observation

@dataclass(slots=True)
class EnvStepResult:
    """Represents one environment transition."""

    observation: Observation
    reward: float
    done: bool
    info: dict[str, Any] = field(default_factory=dict)


class EnvironmentAdapter(Protocol):
    """Shared interface each backend adapter must implement."""

    backend_name: str

    def reset(self) -> Observation:
        """Start or restart an episode and return initial observation."""

    def step(self, action: EnvironmentAction) -> EnvStepResult:
        """Apply action and return transition data."""

    def close(self) -> None:
        """Clean up backend resources."""

    def connect(self) -> None:
        """Open any backend connections needed before a run."""

    def disconnect(self) -> None:
        """Close any backend connections after a run."""

    def reset_run(self) -> Observation:
        """Reset environment state for a new run."""

    def get_observation(self) -> Observation:
        """Return latest observation snapshot."""

    def apply_action(self, action: EnvironmentAction) -> EnvStepResult:
        """Apply an action during a run."""

    def is_terminal(self) -> bool:
        """Whether the current run reached terminal state."""

    def get_terminal_reason(self) -> str:
        """Machine-readable terminal reason for the current run."""


class TrainerPolicy(Protocol):
    """Policy interface to keep trainer independent from backend implementation."""

    def select_action(self, observation: Observation) -> EnvironmentAction:
        """Return action for current observation."""
