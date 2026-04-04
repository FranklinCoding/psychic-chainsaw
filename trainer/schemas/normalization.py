from __future__ import annotations

from typing import Any, Mapping

from trainer.schemas.action import SHARED_ACTION_ADAPTER, SharedAction
from trainer.schemas.observation import SharedObservation


def normalize_observation(payload: Mapping[str, Any] | SharedObservation) -> SharedObservation:
    """Normalize backend payloads into the shared observation schema."""

    if isinstance(payload, SharedObservation):
        return payload

    mapped = dict(payload)
    if "step" in mapped and "step_count" not in mapped:
        mapped["step_count"] = mapped.pop("step")
    else:
        mapped.pop("step", None)

    if "colonists" in mapped and "colonist_count" not in mapped:
        mapped["colonist_count"] = mapped.pop("colonists")
    else:
        mapped.pop("colonists", None)

    if "food_reserve" in mapped and "food_reserves" not in mapped:
        mapped["food_reserves"] = mapped.pop("food_reserve")
    else:
        mapped.pop("food_reserve", None)

    defaults: dict[str, Any] = {
        "colonist_count": 0,
        "food_reserves": 0.0,
        "medicine_reserves": 0.0,
        "colony_wealth": 0.0,
    }
    for key, value in defaults.items():
        mapped.setdefault(key, value)

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
