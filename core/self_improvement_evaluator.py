"""Evaluator MVP pour comparer une modification avant/apres."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkResult:
    quality_score: float
    latency_ms: float
    tests_passed: int
    tests_total: int


@dataclass(frozen=True)
class EvaluationResult:
    accepted: bool
    reason: str
    delta_quality: float
    delta_latency_ms: float


class SelfImprovementEvaluator:
    """Politique simple d'acceptation d'une auto-modification."""

    def evaluate(self, before: BenchmarkResult, after: BenchmarkResult) -> EvaluationResult:
        if after.tests_total <= 0:
            return EvaluationResult(
                accepted=False,
                reason="no tests executed",
                delta_quality=after.quality_score - before.quality_score,
                delta_latency_ms=after.latency_ms - before.latency_ms,
            )

        if after.tests_passed < after.tests_total:
            return EvaluationResult(
                accepted=False,
                reason="test regression detected",
                delta_quality=after.quality_score - before.quality_score,
                delta_latency_ms=after.latency_ms - before.latency_ms,
            )

        delta_quality = after.quality_score - before.quality_score
        delta_latency = after.latency_ms - before.latency_ms

        accepted = delta_quality >= 0 and delta_latency <= 50.0
        reason = "accepted" if accepted else "quality/latency tradeoff not acceptable"

        return EvaluationResult(
            accepted=accepted,
            reason=reason,
            delta_quality=delta_quality,
            delta_latency_ms=delta_latency,
        )
