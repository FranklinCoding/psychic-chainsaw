from __future__ import annotations

import json
from pathlib import Path

from trainer.environment.rimbridge.mapper import map_rimbridge_observation, parse_rimbridge_capabilities

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_rimbridge_maps_sample_payloads_into_shared_observation() -> None:
    sample = _load_fixture("rimbridge_sample.json")
    capabilities = parse_rimbridge_capabilities(
        session_info=sample["session_info"],
        tool_descriptors=sample["tool_descriptors"],
        capability_descriptors=sample["capability_descriptors"],
    )

    observation = map_rimbridge_observation(
        bridge_status=sample["bridge_status"],
        game_info=sample["game_info"],
        colonists=sample["colonists"],
        alerts=sample["alerts"],
        messages=sample["messages"],
        capabilities=capabilities,
        capability_descriptors=sample["capability_descriptors"],
    )

    assert observation.colonist_count == 2
    assert observation.colonist_status_summary.healthy == 1
    assert observation.colonist_status_summary.downed == 1
    assert observation.colony_wealth == 9800.0
    assert observation.game_speed.value == "paused"
    assert observation.threat_level > 0.0
    assert observation.metadata["backend"] == "rimbridge"
    assert observation.metadata["partial_observation"] is True
    assert "food" in observation.metadata["unavailable_fields"]


def test_rimbridge_capabilities_are_parsed_from_tool_surface() -> None:
    sample = _load_fixture("rimbridge_sample.json")
    capabilities = parse_rimbridge_capabilities(
        session_info=sample["session_info"],
        tool_descriptors=sample["tool_descriptors"],
        capability_descriptors=sample["capability_descriptors"],
    )

    assert capabilities.can_set_speed is True
    assert capabilities.can_restart_run is True
    assert capabilities.can_start_new_game is True
    assert capabilities.can_read_colonists is True
    assert capabilities.can_read_resources is False
    assert capabilities.can_set_work_priorities is False
    assert capabilities.can_choose_research is False
    assert capabilities.can_control_alert_posture is False
