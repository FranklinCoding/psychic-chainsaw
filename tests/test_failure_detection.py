from trainer.config import load_config
from trainer.failure_detection import FailureDetector
from trainer.main import run_training_loop
from trainer.schemas import (
    ColonistStatusSummary,
    FailureRiskIndicators,
    GameSpeed,
    Observation,
    ProgressIndicators,
    ResearchState,
)


def build_observation(**overrides: object) -> Observation:
    defaults: dict[str, object] = {
        "colonist_count": 3,
        "colonist_status_summary": ColonistStatusSummary(healthy=2, injured=1, downed=0, mental_break_risk=0),
        "food": 18,
        "medicine": 5,
        "colony_wealth": 1500.0,
        "mood_risk": 0.15,
        "health_risk": 0.1,
        "injury_burden": 0.2,
        "threat_level": 0.2,
        "research_state": ResearchState(current_project="battery", progress=0.3, completed=False),
        "step_count": 5,
        "run_time_seconds": 75,
        "game_speed": GameSpeed.normal,
        "progress": ProgressIndicators(run_completion=0.4, colony_development=0.65, research_completion=0.3),
        "failure_risk": FailureRiskIndicators(starvation=0.1, medical=0.1, mood_break=0.1, restart=0.1),
        "metadata": {"backend": "test"},
    }
    defaults.update(overrides)
    return Observation(**defaults)


def test_failure_detector_identifies_starvation_collapse() -> None:
    config = load_config(profile="mock")
    detector = FailureDetector(config)

    observation = build_observation(
        food=0,
        mood_risk=0.15,
        failure_risk=FailureRiskIndicators(starvation=1.0, medical=0.2, mood_break=0.15, restart=0.55),
    )

    assessment = detector.assess(observation)

    assert assessment.should_terminate is True
    assert assessment.terminal_reason is not None
    assert assessment.terminal_reason.code == "starvation_collapse"
    assert assessment.total_score < assessment.threshold


def test_failure_detector_identifies_all_colonists_incapacitated() -> None:
    config = load_config(profile="mock")
    detector = FailureDetector(config)

    observation = build_observation(
        colonist_count=3,
        colonist_status_summary=ColonistStatusSummary(healthy=0, injured=0, downed=3, mental_break_risk=0),
        failure_risk=FailureRiskIndicators(starvation=0.3, medical=0.9, mood_break=0.3, restart=0.9),
    )

    assessment = detector.assess(observation)

    assert assessment.should_terminate is True
    assert assessment.terminal_reason is not None
    assert assessment.terminal_reason.code == "all_colonists_incapacitated"


def test_failure_detector_identifies_mood_and_health_collapse() -> None:
    config = load_config(profile="mock")
    detector = FailureDetector(config)

    observation = build_observation(
        food=20,
        medicine=0,
        mood_risk=0.95,
        health_risk=0.95,
        injury_burden=0.92,
        colonist_status_summary=ColonistStatusSummary(healthy=0, injured=1, downed=2, mental_break_risk=3),
        failure_risk=FailureRiskIndicators(starvation=0.0, medical=0.95, mood_break=0.95, restart=0.95),
    )

    assessment = detector.assess(observation)

    assert assessment.should_terminate is True
    assert assessment.terminal_reason is not None
    assert assessment.terminal_reason.code == "medical_collapse"
    assert "Mood collapse" in assessment.terminal_reason.contributors


def test_failure_detector_keeps_healthy_state_non_terminal() -> None:
    config = load_config(profile="mock")
    detector = FailureDetector(config)

    observation = build_observation(
        food=24,
        medicine=6,
        mood_risk=0.05,
        health_risk=0.04,
        injury_burden=0.1,
        progress=ProgressIndicators(run_completion=0.5, colony_development=0.8, research_completion=0.55),
        failure_risk=FailureRiskIndicators(starvation=0.0, medical=0.05, mood_break=0.05, restart=0.05),
    )

    assessment = detector.assess(observation)

    assert assessment.should_terminate is False
    assert assessment.terminal_reason is None


def test_mock_training_loop_can_terminate_from_failure_detector() -> None:
    config = load_config(profile="mock")
    config.policy.failure_threshold = 0.4
    config.failure.weights.all_colonists_incapacitated = 0.0
    config.failure.weights.starvation = 5.0
    config.failure.weights.medical_collapse = 0.0
    config.failure.weights.mood_collapse = 0.0
    config.failure.weights.severe_injury_burden = 0.0
    config.failure.weights.stalled_progress = 0.0
    config.failure.weights.severe_resource_depletion = 0.0
    config.failure.weights.high_failure_risk = 0.0

    stats = run_training_loop(config=config, max_steps=10)

    assert stats.completed is True
    assert stats.terminal_reason == "starvation_collapse"
    assert stats.terminal_details["category"] == "failure"
    assert stats.steps < 8
