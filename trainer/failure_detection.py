from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from trainer.config import TrainerConfig
from trainer.schemas import Observation


def _clamp_ratio(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(slots=True)
class FailureSignal:
    code: str
    label: str
    score: float
    weight: float
    active: bool
    detail: str

    @property
    def contribution(self) -> float:
        return self.score * self.weight

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "label": self.label,
            "score": round(self.score, 4),
            "weight": round(self.weight, 4),
            "contribution": round(self.contribution, 4),
            "active": self.active,
            "detail": self.detail,
        }


@dataclass(slots=True)
class TerminalReason:
    category: str
    code: str
    summary: str
    score: float
    threshold: float
    primary_signal: str
    contributors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "category": self.category,
            "code": self.code,
            "summary": self.summary,
            "score": round(self.score, 4),
            "threshold": round(self.threshold, 4),
            "primary_signal": self.primary_signal,
            "contributors": list(self.contributors),
        }


@dataclass(slots=True)
class FailureAssessment:
    total_score: float
    threshold: float
    should_terminate: bool
    signals: list[FailureSignal]
    terminal_reason: TerminalReason | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "total_score": round(self.total_score, 4),
            "threshold": round(self.threshold, 4),
            "should_terminate": self.should_terminate,
            "signals": [signal.as_dict() for signal in self.signals],
            "terminal_reason": self.terminal_reason.as_dict() if self.terminal_reason else None,
        }


class FailureDetector:
    """Bridge-agnostic failure scoring based only on shared observations."""

    _PROGRESS_SIGNAL = "stalled_progress"

    def __init__(self, config: TrainerConfig) -> None:
        self.config = config
        self._progress_samples: deque[tuple[int, float]] = deque()

    def reset(self) -> None:
        self._progress_samples.clear()

    def _capability_enabled(self, observation: Observation, capability_name: str, default: bool = True) -> bool:
        capabilities = observation.metadata.get("capabilities")
        if not isinstance(capabilities, dict):
            return default

        value = capabilities.get(capability_name)
        return value if isinstance(value, bool) else default

    def assess(self, observation: Observation) -> FailureAssessment:
        progress_value = self._progress_value(observation)
        self._progress_samples.append((observation.step_count, progress_value))

        max_samples = self.config.failure.progress_window_steps
        while len(self._progress_samples) > max_samples:
            self._progress_samples.popleft()

        signals = [
            self._all_colonists_incapacitated_signal(observation),
            self._starvation_signal(observation),
            self._medical_collapse_signal(observation),
            self._mood_collapse_signal(observation),
            self._injury_burden_signal(observation),
            self._stalled_progress_signal(observation),
            self._resource_depletion_signal(observation),
            self._high_failure_risk_signal(observation),
        ]

        total_weight = sum(signal.weight for signal in signals if signal.weight > 0.0 and signal.score > 0.0) or 1.0
        total_score = sum(signal.contribution for signal in signals) / total_weight
        threshold = self.config.policy.failure_threshold

        terminal_reason = self._build_terminal_reason(
            observation=observation,
            total_score=total_score,
            threshold=threshold,
            signals=signals,
        )
        return FailureAssessment(
            total_score=total_score,
            threshold=threshold,
            should_terminate=terminal_reason is not None,
            signals=signals,
            terminal_reason=terminal_reason,
        )

    def _reserve_scarcity(self, amount: int, reserve: int) -> float:
        if reserve <= 0:
            return 0.0
        return _clamp_ratio(1.0 - (amount / reserve))

    def _progress_value(self, observation: Observation) -> float:
        return _clamp_ratio(
            (observation.progress.colony_development * 0.65) + (observation.progress.research_completion * 0.35)
        )

    def _all_colonists_incapacitated_signal(self, observation: Observation) -> FailureSignal:
        if not self._capability_enabled(observation, "can_read_colonists"):
            return FailureSignal(
                code="all_colonists_incapacitated",
                label="All colonists dead or downed",
                score=0.0,
                weight=self.config.failure.weights.all_colonists_incapacitated,
                active=False,
                detail="colonist state unavailable for this backend",
            )

        no_colonists_left = observation.colonist_count == 0
        all_downed = observation.colonist_count > 0 and (
            observation.colonist_status_summary.downed >= observation.colonist_count
        )
        score = 1.0 if no_colonists_left or all_downed else 0.0
        detail = (
            f"colonists={observation.colonist_count}, downed={observation.colonist_status_summary.downed}"
        )
        return FailureSignal(
            code="all_colonists_incapacitated",
            label="All colonists dead or downed",
            score=score,
            weight=self.config.failure.weights.all_colonists_incapacitated,
            active=score >= 1.0,
            detail=detail,
        )

    def _starvation_signal(self, observation: Observation) -> FailureSignal:
        can_read_resources = self._capability_enabled(observation, "can_read_resources")
        food_scarcity = self._reserve_scarcity(observation.food, self.config.policy.min_food_reserve) if can_read_resources else 0.0
        score = max(observation.failure_risk.starvation, food_scarcity)
        detail = (
            f"food={observation.food}, starvation_risk={observation.failure_risk.starvation:.2f}"
            if can_read_resources
            else f"food=unavailable, starvation_risk={observation.failure_risk.starvation:.2f}"
        )
        return FailureSignal(
            code="starvation_collapse",
            label="Starvation or food collapse",
            score=score,
            weight=self.config.failure.weights.starvation,
            active=score >= self.config.failure.starvation_signal_threshold,
            detail=detail,
        )

    def _medical_collapse_signal(self, observation: Observation) -> FailureSignal:
        can_read_resources = self._capability_enabled(observation, "can_read_resources")
        medicine_scarcity = (
            self._reserve_scarcity(observation.medicine, self.config.policy.min_medicine_reserve)
            if can_read_resources
            else 0.0
        )
        downed_ratio = (
            observation.colonist_status_summary.downed / observation.colonist_count
            if observation.colonist_count > 0
            else 0.0
        )
        score = max(observation.health_risk, medicine_scarcity, downed_ratio)
        detail = (
            f"health_risk={observation.health_risk:.2f}, "
            f"medicine={observation.medicine if can_read_resources else 'unavailable'}, "
            f"downed_ratio={downed_ratio:.2f}"
        )
        return FailureSignal(
            code="medical_collapse",
            label="Medical collapse",
            score=score,
            weight=self.config.failure.weights.medical_collapse,
            active=score >= self.config.failure.medical_signal_threshold,
            detail=detail,
        )

    def _mood_collapse_signal(self, observation: Observation) -> FailureSignal:
        mental_break_ratio = (
            observation.colonist_status_summary.mental_break_risk / observation.colonist_count
            if observation.colonist_count > 0
            else 0.0
        )
        score = max(observation.mood_risk, mental_break_ratio)
        detail = (
            f"mood_risk={observation.mood_risk:.2f}, "
            f"mental_break_ratio={mental_break_ratio:.2f}"
        )
        return FailureSignal(
            code="mood_collapse",
            label="Mood collapse",
            score=score,
            weight=self.config.failure.weights.mood_collapse,
            active=score >= self.config.failure.mood_signal_threshold,
            detail=detail,
        )

    def _injury_burden_signal(self, observation: Observation) -> FailureSignal:
        acceptable = self.config.policy.acceptable_injury_threshold
        if acceptable >= 1.0:
            score = 0.0
        else:
            score = _clamp_ratio((observation.injury_burden - acceptable) / (1.0 - acceptable))
        detail = f"injury_burden={observation.injury_burden:.2f}, acceptable={acceptable:.2f}"
        return FailureSignal(
            code="severe_injury_burden",
            label="Severe injury burden",
            score=score,
            weight=self.config.failure.weights.severe_injury_burden,
            active=score >= self.config.failure.injury_signal_threshold,
            detail=detail,
        )

    def _stalled_progress_signal(self, observation: Observation) -> FailureSignal:
        samples = list(self._progress_samples)
        score = 0.0
        progress_delta = 0.0

        if len(samples) >= self.config.failure.progress_window_steps:
            oldest_step, oldest_value = samples[0]
            latest_step, latest_value = samples[-1]
            if latest_step > oldest_step:
                progress_delta = latest_value - oldest_value
                min_delta = self.config.failure.min_progress_delta
                if min_delta > 0.0:
                    score = _clamp_ratio(1.0 - (progress_delta / min_delta))

        detail = (
            f"progress_delta={progress_delta:.3f}, window={len(samples)}, "
            f"current_progress={self._progress_value(observation):.3f}"
        )
        return FailureSignal(
            code=self._PROGRESS_SIGNAL,
            label="No meaningful progress over time",
            score=score,
            weight=self.config.failure.weights.stalled_progress,
            active=score >= 1.0,
            detail=detail,
        )

    def _resource_depletion_signal(self, observation: Observation) -> FailureSignal:
        if not self._capability_enabled(observation, "can_read_resources"):
            return FailureSignal(
                code="severe_resource_depletion",
                label="Severe resource depletion",
                score=0.0,
                weight=self.config.failure.weights.severe_resource_depletion,
                active=False,
                detail="resource totals unavailable for this backend",
            )

        food_scarcity = self._reserve_scarcity(observation.food, self.config.policy.min_food_reserve)
        medicine_scarcity = self._reserve_scarcity(observation.medicine, self.config.policy.min_medicine_reserve)
        score = min(food_scarcity, medicine_scarcity)
        detail = f"food_scarcity={food_scarcity:.2f}, medicine_scarcity={medicine_scarcity:.2f}"
        return FailureSignal(
            code="severe_resource_depletion",
            label="Severe resource depletion",
            score=score,
            weight=self.config.failure.weights.severe_resource_depletion,
            active=score >= self.config.failure.resource_signal_threshold,
            detail=detail,
        )

    def _high_failure_risk_signal(self, observation: Observation) -> FailureSignal:
        score = observation.failure_risk.restart
        detail = f"restart_risk={observation.failure_risk.restart:.2f}"
        return FailureSignal(
            code="high_failure_risk",
            label="High overall failure risk",
            score=score,
            weight=self.config.failure.weights.high_failure_risk,
            active=score >= self.config.failure.high_risk_signal_threshold,
            detail=detail,
        )

    def _build_terminal_reason(
        self,
        observation: Observation,
        total_score: float,
        threshold: float,
        signals: list[FailureSignal],
    ) -> TerminalReason | None:
        immediate_signal = next(
            (signal for signal in signals if signal.code == "all_colonists_incapacitated" and signal.active),
            None,
        )
        if immediate_signal is not None:
            return TerminalReason(
                category="failure",
                code=immediate_signal.code,
                summary="All colonists are dead or downed, so the run is considered lost.",
                score=total_score,
                threshold=threshold,
                primary_signal=immediate_signal.label,
                contributors=self._contributors(signals),
            )

        starvation_signal = next((signal for signal in signals if signal.code == "starvation_collapse"), None)
        if starvation_signal is not None and self._severe_starvation_collapse(observation, starvation_signal):
            return TerminalReason(
                category="failure",
                code=starvation_signal.code,
                summary="Food reserves are exhausted and starvation risk is severe, so the run is considered lost.",
                score=total_score,
                threshold=threshold,
                primary_signal=starvation_signal.label,
                contributors=self._contributors(signals),
            )

        if total_score < threshold:
            return None

        primary_signal = max(signals, key=lambda signal: (signal.contribution, signal.score))
        contributor_labels = self._contributors(signals)
        summary = (
            f"Failure score {total_score:.2f} crossed threshold {threshold:.2f}; "
            f"primary driver: {primary_signal.label.lower()}."
        )
        return TerminalReason(
            category="failure",
            code=primary_signal.code,
            summary=summary,
            score=total_score,
            threshold=threshold,
            primary_signal=primary_signal.label,
            contributors=contributor_labels,
        )

    def _contributors(self, signals: list[FailureSignal]) -> list[str]:
        contributors = [signal.label for signal in signals if signal.active]
        if contributors:
            return contributors

        ranked = sorted(signals, key=lambda signal: (signal.contribution, signal.score), reverse=True)
        return [signal.label for signal in ranked[:3] if signal.score > 0.0]

    def _severe_starvation_collapse(self, observation: Observation, signal: FailureSignal) -> bool:
        return (
            observation.food <= 0
            and observation.failure_risk.starvation >= 0.9
            and signal.active
        )
