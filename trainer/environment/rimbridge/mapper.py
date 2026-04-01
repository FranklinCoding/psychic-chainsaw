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

_RESOURCE_KEYWORDS = ("food", "meal", "medicine", "nutrition", "resource")
_WORK_PRIORITY_KEYWORDS = ("workpriority", "work_priority", "work-priority")
_RESEARCH_KEYWORDS = ("research", "tech")
_ALERT_LABEL_KEYWORDS = {
    "starvation": ("food", "starvation", "hungry", "malnutrition"),
    "medical": ("injury", "wound", "bleed", "medical", "sick", "disease", "downed"),
    "mood": ("mood", "break", "berserk", "tantrum", "sad", "recreation"),
    "threat": ("raid", "threat", "enemy", "hostile", "danger", "fire", "manhunter"),
}


def _clamp_ratio(value: float) -> float:
    return max(0.0, min(1.0, value))


def _to_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _to_sequence(value: Any) -> list[Any]:
    return list(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)) else []


def _contains_keyword(values: Sequence[str], keywords: Sequence[str]) -> bool:
    haystack = " ".join(values).lower()
    return any(keyword in haystack for keyword in keywords)


def _extract_tool_names(
    *,
    session_info: Mapping[str, Any] | None,
    tool_descriptors: Sequence[Mapping[str, Any]],
    capability_descriptors: Sequence[Mapping[str, Any]],
) -> set[str]:
    names: set[str] = set()
    session_capabilities = _to_mapping(_to_mapping(session_info).get("capabilities"))
    for method_name in _to_sequence(session_capabilities.get("methods")):
        if isinstance(method_name, str):
            names.add(method_name)

    for descriptor in list(tool_descriptors) + list(capability_descriptors):
        entry = _to_mapping(descriptor)
        for key in ("name", "id", "capabilityId", "alias"):
            value = entry.get(key)
            if isinstance(value, str):
                names.add(value)
        aliases = _to_sequence(entry.get("aliases"))
        for alias in aliases:
            if isinstance(alias, str):
                names.add(alias)
    return names


def parse_rimbridge_capabilities(
    *,
    session_info: Mapping[str, Any] | None,
    tool_descriptors: Sequence[Mapping[str, Any]],
    capability_descriptors: Sequence[Mapping[str, Any]],
) -> BridgeCapabilities:
    tool_names = _extract_tool_names(
        session_info=session_info,
        tool_descriptors=tool_descriptors,
        capability_descriptors=capability_descriptors,
    )

    readable_names = sorted(tool_names)
    return BridgeCapabilities(
        can_set_speed=("rimworld/set_time_speed" in tool_names or "rimworld/pause_game" in tool_names),
        can_restart_run=(
            "rimworld/go_to_main_menu" in tool_names
            and any(name in tool_names for name in ("rimworld/start_debug_game", "rimworld/load_game", "rimworld/load_game_ready"))
        ),
        can_start_new_game=("rimworld/start_debug_game" in tool_names),
        can_read_colonists=("rimworld/list_colonists" in tool_names),
        can_read_resources=_contains_keyword(readable_names, _RESOURCE_KEYWORDS),
        can_set_work_priorities=_contains_keyword(readable_names, _WORK_PRIORITY_KEYWORDS),
        can_choose_research=_contains_keyword(readable_names, _RESEARCH_KEYWORDS)
        and any(name in tool_names for name in ("rimworld/open_main_tab", "rimworld/click_ui_target")),
        can_control_alert_posture=("rimworld/activate_alert" in tool_names and "rimworld/list_alerts" in tool_names),
        metadata={
            "backend_family": "gabp",
            "tool_count": len(tool_names),
            "tool_names": readable_names,
        },
    )


def _game_speed_from_payload(bridge_status: Mapping[str, Any], game_info: Mapping[str, Any]) -> GameSpeed:
    for source in (game_info, bridge_status):
        raw_speed = source.get("timeSpeed") or source.get("speed") or source.get("gameSpeed")
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
    if bool(game_info.get("isPaused") or bridge_status.get("isPaused")):
        return GameSpeed.paused
    return GameSpeed.normal


def _alerts_to_risk(alerts: Sequence[Mapping[str, Any]], key: str) -> float:
    labels = []
    for alert in alerts:
        entry = _to_mapping(alert)
        label = entry.get("label") or entry.get("title") or entry.get("summary") or entry.get("text")
        if isinstance(label, str):
            labels.append(label.lower())
    if not labels:
        return 0.0
    matches = sum(1 for label in labels if any(keyword in label for keyword in _ALERT_LABEL_KEYWORDS[key]))
    return _clamp_ratio(matches / max(len(labels), 1))


def _count_flagged_colonists(colonists: Sequence[Mapping[str, Any]], keywords: Sequence[str]) -> int:
    count = 0
    for entry in colonists:
        data = _to_mapping(entry)
        normalized = " ".join(str(value).lower() for value in data.values())
        if any(keyword in normalized for keyword in keywords):
            count += 1
    return count


def map_rimbridge_observation(
    *,
    bridge_status: Mapping[str, Any],
    game_info: Mapping[str, Any],
    colonists: Sequence[Mapping[str, Any]],
    alerts: Sequence[Mapping[str, Any]],
    messages: Sequence[Mapping[str, Any]],
    capabilities: BridgeCapabilities,
    capability_descriptors: Sequence[Mapping[str, Any]],
) -> Observation:
    colonist_entries = [_to_mapping(entry) for entry in colonists]
    colonist_count = int(game_info.get("colonistCount") or game_info.get("colonist_count") or len(colonist_entries))
    downed = _count_flagged_colonists(colonist_entries, ("downed", "incapacitated"))
    injured = _count_flagged_colonists(colonist_entries, ("injured", "wounded", "bleeding", "pain"))
    mental_break = _count_flagged_colonists(colonist_entries, ("break", "berserk", "tantrum", "sad"))
    healthy = max(colonist_count - injured - downed, 0)

    colony_wealth = float(
        game_info.get("colonyWealth")
        or game_info.get("wealth")
        or bridge_status.get("colonyWealth")
        or bridge_status.get("wealth")
        or 0.0
    )
    game_tick = int(
        game_info.get("gameTick")
        or game_info.get("tick")
        or bridge_status.get("gameTick")
        or bridge_status.get("tick")
        or 0
    )

    mood_risk = _clamp_ratio(max(_alerts_to_risk(alerts, "mood"), mental_break / max(colonist_count, 1)))
    health_risk = _clamp_ratio(max(_alerts_to_risk(alerts, "medical"), downed / max(colonist_count, 1)))
    starvation_risk = _alerts_to_risk(alerts, "starvation")
    threat_level = _clamp_ratio(max(_alerts_to_risk(alerts, "threat"), _alerts_to_risk(messages, "threat")))
    injury_burden = _clamp_ratio((injured + downed) / max(colonist_count, 1))

    food_value = (
        game_info.get("food")
        or game_info.get("foodTotal")
        or bridge_status.get("food")
        or bridge_status.get("foodTotal")
        or 0
    )
    medicine_value = (
        game_info.get("medicine")
        or game_info.get("medicineTotal")
        or bridge_status.get("medicine")
        or bridge_status.get("medicineTotal")
        or 0
    )
    food = int(food_value or 0)
    medicine = int(medicine_value or 0)

    research_payload = _to_mapping(game_info.get("research") or bridge_status.get("research"))
    research_state = ResearchState(
        current_project=str(research_payload.get("currentProject") or research_payload.get("project") or "")
        or None,
        progress=_clamp_ratio(float(research_payload.get("progress") or 0.0)),
        completed=bool(research_payload.get("completed") or float(research_payload.get("progress") or 0.0) >= 1.0),
    )

    colony_development = _clamp_ratio(
        min(colony_wealth / 25000.0, 1.0) * 0.6 + min(colonist_count / 8.0, 1.0) * 0.4
    )

    unavailable_fields: list[str] = []
    if not capabilities.can_read_resources:
        unavailable_fields.extend(["food", "medicine"])
    if not capabilities.can_choose_research:
        unavailable_fields.append("research_actions")

    return Observation(
        colonist_count=colonist_count,
        colonist_status_summary=ColonistStatusSummary(
            healthy=healthy,
            injured=injured,
            downed=downed,
            mental_break_risk=mental_break,
        ),
        food=food,
        medicine=medicine,
        colony_wealth=colony_wealth,
        mood_risk=mood_risk,
        health_risk=health_risk,
        injury_burden=injury_burden,
        threat_level=threat_level,
        research_state=research_state,
        step_count=game_tick,
        run_time_seconds=max(0, int(game_tick / 60)),
        game_speed=_game_speed_from_payload(bridge_status, game_info),
        progress=ProgressIndicators(
            run_completion=0.0,
            colony_development=colony_development,
            research_completion=research_state.progress,
        ),
        failure_risk=FailureRiskIndicators(
            starvation=starvation_risk,
            medical=health_risk,
            mood_break=mood_risk,
            restart=max(starvation_risk, health_risk, mood_risk, threat_level),
        ),
        metadata={
            "backend": "rimbridge",
            "raw_bridge_status": dict(bridge_status),
            "raw_game_info": dict(game_info),
            "raw_capabilities": [dict(item) for item in capability_descriptors],
            "raw_alerts": [dict(item) for item in alerts],
            "capabilities": capabilities.model_dump(mode="python"),
            "unavailable_fields": unavailable_fields,
            "partial_observation": bool(unavailable_fields),
        },
    )
