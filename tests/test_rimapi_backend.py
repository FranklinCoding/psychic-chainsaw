from __future__ import annotations

import json
from pathlib import Path

from trainer.environment.rimapi.mapper import map_rimapi_observation, parse_rimapi_capabilities

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_rimapi_maps_sample_payloads_into_shared_observation() -> None:
    sample = _load_fixture("rimapi_sample.json")
    capabilities = parse_rimapi_capabilities()

    observation = map_rimapi_observation(
        game_state=sample["game_state"],
        colonists=sample["colonists"],
        resources_summary=sample["resources_summary"],
        research_state_payload=sample["research_state"],
        capabilities=capabilities,
        backend_metadata={"version_info": {"api_version": "v1"}},
    )

    assert observation.colonist_count == 3
    assert observation.colonist_status_summary.healthy == 1
    assert observation.colonist_status_summary.injured == 1
    assert observation.colonist_status_summary.downed == 1
    assert observation.food == 48
    assert observation.medicine == 9
    assert observation.research_state.current_project == "microelectronics"
    assert observation.progress.research_completion == 0.46
    assert observation.game_speed.value == "normal"
    assert observation.metadata["backend"] == "rimapi"
    assert observation.metadata["capabilities"]["can_read_resources"] is True


def test_rimapi_capabilities_are_reported_cleanly() -> None:
    capabilities = parse_rimapi_capabilities()

    assert capabilities.can_set_speed is True
    assert capabilities.can_restart_run is True
    assert capabilities.can_start_new_game is True
    assert capabilities.can_read_colonists is True
    assert capabilities.can_read_resources is True
    assert capabilities.can_set_work_priorities is False
    assert capabilities.can_choose_research is False
    assert capabilities.can_control_alert_posture is False
