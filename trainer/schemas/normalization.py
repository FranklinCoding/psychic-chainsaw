from __future__ import annotations

from typing import Any, Mapping

from trainer.schemas.action import SHARED_ACTION_ADAPTER, SharedAction
from trainer.schemas.observation import SharedObservation


def normalize_observation(payload: Mapping[str, Any]) -> SharedObservation:
    """Normalize backend payloads into the shared observation schema."""

    mapped = dict(payload)
    if "step" in mapped and "step_count" not in mapped:
        mapped["step_count"] = mapped["step"]
    if "colonists" in mapped and "colonist_count" not in mapped:
        mapped["colonist_count"] = mapped["colonists"]
    if "food_reserve" in mapped and "food_reserves" not in mapped:
        mapped["food_reserves"] = mapped["food_reserve"]

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

    if isinstance(payload, dict):
        return SHARED_ACTION_ADAPTER.validate_python(payload)
    return payload
