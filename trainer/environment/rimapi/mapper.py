from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from trainer.schemas import (
    BridgeCapabilities,
    ColonistStatusSummary,
    FailureRiskIndicators,
    GameSpeed,
    Observation,
    ProgressIndicators,
    ResearchState,
)


def _clamp_ratio(value: float) -> float:
    return max(0.0, min(1.0, value))


def _to_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_sequence(value: Any) -> list[Any]:
    return list(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else []


def _game_speed_from_payload(game_state: Mapping[str, Any]) -> GameSpeed:
    raw_speed = game_state.get("speed") or game_state.get("game_speed")
    if isinstance(raw_speed, str):
        normalized = raw_speed.strip().lower()
        mapping = {
            "paused": GameSpeed.paused,
            "normal": GameSpeed.normal,
            "fast": GameSpeed.fast,
            "superfast": GameSpeed.superfast,
            "super_fast": GameSpeed.superfast,
            "super fast": GameSpeed.superfast,
        }
        if normalized in mapping:
            return mapping[normalized]
    if isinstance(raw_speed, int):
        return {
            0: GameSpeed.paused,
            1: GameSpeed.normal,
            2: GameSpeed.fast,
            3: GameSpeed.superfast,
            4: GameSpeed.superfast,
        }.get(raw_speed, GameSpeed.normal)
    if bool(game_state.get("is_paused")):
        return GameSpeed.paused
    return GameSpeed.normal


def _extract_research_state(payload: Mapping[str, Any] | None) -> ResearchState:
    data = _to_mapping(payload)
    current_project = data.get("current_project") or data.get("project") or data.get("project_name")
    progress = data.get("progress") or data.get("research_progress") or 0.0
    completed = data.get("completed")
    if completed is None:
        completed = bool(progress) and float(progress) >= 1.0
    return ResearchState(
        current_project=str(current_project) if current_project else None,
        progress=_clamp_ratio(float(progress or 0.0)),
        completed=bool(completed),
    )


def parse_rimapi_capabilities() -> BridgeCapabilities:
    return BridgeCapabilities(
        can_set_speed=True,
        can_restart_run=True,
        can_start_new_game=True,
        can_read_colonists=True,
        can_read_resources=True,
        can_set_work_priorities=False,
        can_choose_research=False,
        can_control_alert_posture=False,
        metadata={
            "backend_family": "rest",
            "observation_sources": [
                "/api/v1/game/state",
                "/api/v1|v2/colonists/detailed",
                "/api/v1/resources/summary",
            ],
        },
    )


def map_rimapi_observation(
    *,
    game_state: Mapping[str, Any],
    colonists: Sequence[Mapping[str, Any]],
    resources_summary: Mapping[str, Any],
    research_state_payload: Mapping[str, Any] | None,
    capabilities: BridgeCapabilities,
    backend_metadata: Mapping[str, Any] | None = None,
) -> Observation:
    colonist_entries = [_to_mapping(entry) for entry in colonists]
    resources = _to_mapping(resources_summary)
    critical_resources = _to_mapping(resources.get("critical_resources"))
    food_summary = _to_mapping(critical_resources.get("food_summary"))

    colonist_count = int(game_state.get("colonist_count") or len(colonist_entries))
    health_values: list[float] = []
    mood_values: list[float] = []
    bleeding_values: list[float] = []
    injured = 0
    downed = 0
    mental_break_risk = 0

    for entry in colonist_entries:
        colonist = _to_mapping(entry.get("colonist") or entry.get("pawn") or entry)
        detail = _to_mapping(entry.get("detailes") or entry.get("details") or entry)
        medical = _to_mapping(detail.get("colonist_medical_info") or detail.get("medical_info"))

        health = float(colonist.get("health") or 0.0)
        mood = float(colonist.get("mood") or 0.0)
        bleeding = float(medical.get("bleeding_rate") or 0.0)
        in_pain = bool(medical.get("in_pain"))
        is_downed = bool(
            colonist.get("is_downed")
            or colonist.get("downed")
            or detail.get("is_downed")
            or detail.get("downed")
            or health <= 0.2
        )

        health_values.append(_clamp_ratio(health))
        mood_values.append(_clamp_ratio(mood))
        bleeding_values.append(max(0.0, bleeding))

        if mood < 0.35:
            mental_break_risk += 1
        if is_downed:
            downed += 1
        elif health < 0.9 or in_pain or bleeding > 0:
            injured += 1

    healthy = max(colonist_count - injured - downed, 0)
    average_health = sum(health_values) / len(health_values) if health_values else 1.0
    average_mood = sum(mood_values) / len(mood_values) if mood_values else 1.0
    average_bleeding = sum(bleeding_values) / len(bleeding_values) if bleeding_values else 0.0
    injury_burden = _clamp_ratio(((1.0 - average_health) * 0.8) + min(average_bleeding, 1.0) * 0.2)

    food = int(food_summary.get("food_total") or 0)
    total_nutrition = float(food_summary.get("total_nutrition") or 0.0)
    medicine = int(critical_resources.get("medicine_total") or 0)
    colony_wealth = float(game_state.get("colony_wealth") or resources.get("total_market_value") or 0.0)
    game_tick = int(game_state.get("game_tick") or 0)
    research_state = _extract_research_state(research_state_payload)

    nutrition_days = total_nutrition / max(float(colonist_count) * 1.6, 1.0)
    starvation_risk = _clamp_ratio((2.0 - nutrition_days) / 2.0)
    mood_risk = _clamp_ratio(max(1.0 - average_mood, mental_break_risk / max(colonist_count, 1)))
    health_risk = _clamp_ratio(max(1.0 - average_health, average_bleeding, downed / max(colonist_count, 1)))

    colony_development = _clamp_ratio(
        min(colony_wealth / 25000.0, 1.0) * 0.5
        + min(colonist_count / 8.0, 1.0) * 0.3
        + min(total_nutrition / 1200.0, 1.0) * 0.2
    )

    metadata = {
        "backend": "rimapi",
        "raw_game_state": dict(game_state),
        "raw_resources_summary": dict(resources_summary),
        "capabilities": capabilities.model_dump(mode="python"),
    }
    if backend_metadata:
        metadata.update(dict(backend_metadata))
    if research_state_payload is not None:
        metadata["raw_research_state"] = dict(research_state_payload)

    return Observation(
        colonist_count=colonist_count,
        colonist_status_summary=ColonistStatusSummary(
            healthy=healthy,
            injured=injured,
            downed=downed,
            mental_break_risk=mental_break_risk,
        ),
        food=food,
        medicine=medicine,
        colony_wealth=colony_wealth,
        mood_risk=mood_risk,
        health_risk=health_risk,
        injury_burden=injury_burden,
        threat_level=0.0,
        research_state=research_state,
        step_count=game_tick,
        run_time_seconds=max(0, int(game_tick / 60)),
        game_speed=_game_speed_from_payload(game_state),
        progress=ProgressIndicators(
            run_completion=0.0,
            colony_development=colony_development,
            research_completion=research_state.progress,
        ),
        failure_risk=FailureRiskIndicators(
            starvation=starvation_risk,
            medical=health_risk,
            mood_break=mood_risk,
            restart=max(starvation_risk, health_risk, mood_risk),
        ),
        metadata=metadata,
    )
