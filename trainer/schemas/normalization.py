from __future__ import annotations

from typing import Any, Mapping

from trainer.schemas.action import SHARED_ACTION_ADAPTER, SharedAction
from trainer.schemas.observation import (
    FailureRiskIndicators,
    ProgressIndicators,
    ResearchStatus,
    SharedObservation,
)


def _filter_fields(model_type: type, payload: Mapping[str, Any]) -> dict[str, Any]:
    allowed = set(model_type.model_fields.keys())
    return {key: value for key, value in payload.items() if key in allowed}


def normalize_observation(payload: Mapping[str, Any] | SharedObservation) -> SharedObservation:
    """Normalize backend payloads into the shared observation schema."""

    if isinstance(payload, SharedObservation):
        return payload

    mapped = dict(payload)
    aliases = {
        "step": "step_count",
        "colonists": "colonist_count",
        "food_reserve": "food_reserves",
        "run_time": "run_time_seconds",
        "research": "research_status",
    }
    for source_key, target_key in aliases.items():
        if source_key in mapped and target_key not in mapped:
            mapped[target_key] = mapped.pop(source_key)
        else:
            mapped.pop(source_key, None)

    defaults: dict[str, Any] = {
        "colonist_count": 0,
        "food_reserves": 0.0,
        "medicine_reserves": 0.0,
        "colony_wealth": 0.0,
    }
    for key, value in defaults.items():
        mapped.setdefault(key, value)

    # Keep schema strict while preserving adapter compatibility by dropping unknown keys.
    mapped = _filter_fields(SharedObservation, mapped)

    if isinstance(mapped.get("research_status"), Mapping):
        mapped["research_status"] = _filter_fields(ResearchStatus, mapped["research_status"])
    if isinstance(mapped.get("progress_indicators"), Mapping):
        mapped["progress_indicators"] = _filter_fields(
            ProgressIndicators, mapped["progress_indicators"]
        )
    if isinstance(mapped.get("failure_risk_indicators"), Mapping):
        mapped["failure_risk_indicators"] = _filter_fields(
            FailureRiskIndicators, mapped["failure_risk_indicators"]
        )

    return SharedObservation.model_validate(mapped)


def normalize_action(payload: Mapping[str, Any] | SharedAction) -> SharedAction:
    """Coerce dict payloads (or already-typed actions) into shared action schema."""

    if isinstance(payload, Mapping):
        return SHARED_ACTION_ADAPTER.validate_python(dict(payload))
    return payload


def encode_action(action: Mapping[str, Any] | SharedAction) -> dict[str, Any]:
    """Convert a shared action into a plain payload for future backend adapters."""

    normalized = normalize_action(action)
    return normalized.model_dump(mode="python")
