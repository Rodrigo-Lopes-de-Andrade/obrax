"""Observabilidade dos agentes (B10.8).

Métricas alvo do SPRINTS: `agent_response_duration_seconds` (P95 < 5s) e
`agent_interpretation_correct_ratio` (≥ 90%). Sem dependência `prometheus_client`
no MVP — registrador in-process com o mesmo contrato (observe/snapshot),
trocável por gauges/histograms Prometheus em staging/prod (mesma filosofia das
outras integrações). Sentry-on-error é feito pelo handler global existente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class AgentMetrics:
    _durations: list[float] = field(default_factory=list)
    _interpretations: list[bool] = field(default_factory=list)

    def observe_duration(self, seconds: float) -> None:
        self._durations.append(seconds)

    def observe_interpretation(self, *, correct: bool) -> None:
        self._interpretations.append(correct)

    def p95_duration(self) -> float:
        if not self._durations:
            return 0.0
        ordered = sorted(self._durations)
        idx = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
        return ordered[idx]

    def interpretation_ratio(self) -> float:
        if not self._interpretations:
            return 1.0
        return sum(self._interpretations) / len(self._interpretations)

    def snapshot(self) -> dict[str, float]:
        return {
            "agent_response_duration_seconds_p95": self.p95_duration(),
            "agent_interpretation_correct_ratio": self.interpretation_ratio(),
            "agent_interactions_total": float(len(self._durations)),
        }


@lru_cache
def get_agent_metrics() -> AgentMetrics:
    return AgentMetrics()
