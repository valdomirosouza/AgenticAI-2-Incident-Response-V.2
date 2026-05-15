"""
SLO definitions and error budget calculator — S4-01 (SDD §3.2.1).

SLOs formais:
  availability  — ≥ 99.5% das requisições sem 5xx  (threshold: taxa 5xx ≤ 0.5%)
  latency_p95   — P95 ≤ 500ms                       (SLO target: 99.0%)
  latency_p99   — P99 ≤ 1000ms                      (SLO target: 99.9%)

Error budget:
  - Disponibilidade: budget = max_error_rate_pct; consumed = current_error_rate_pct
  - Latência: budget proporcional ao headroom até o threshold
    consumed = (current_ms / threshold) * budget_pct

Janela: sessão atual (desde o início do serviço — contadores Redis cumulativos).
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.models import MetricsOverview, ResponseTimesData, SloHealth, SloStatus, SloStatusReport

_HEALTH_RANK: dict[SloHealth, int] = {
    SloHealth.healthy: 0,
    SloHealth.at_risk: 1,
    SloHealth.breaching: 2,
}


@dataclass(frozen=True)
class SloDefinition:
    name: str
    slo_id: str
    target_pct: float   # ex: 99.5 → exige 99.5% de compliance
    threshold: float    # limite do indicador (ms ou taxa %)
    unit: str

    @property
    def error_budget_pct(self) -> float:
        """Budget total disponível = 100 - target_pct."""
        return round(100.0 - self.target_pct, 4)


# ── SLOs formais (SDD §3.2.1) ─────────────────────────────────────────────────

SLOS: dict[str, SloDefinition] = {
    "availability": SloDefinition(
        name="Availability",
        slo_id="availability",
        target_pct=99.5,
        threshold=0.5,   # 5xx error rate ≤ 0.5%
        unit="5xx_rate_pct",
    ),
    "latency_p95": SloDefinition(
        name="Latency P95",
        slo_id="latency_p95",
        target_pct=99.0,
        threshold=500.0,  # P95 ≤ 500ms
        unit="ms",
    ),
    "latency_p99": SloDefinition(
        name="Latency P99",
        slo_id="latency_p99",
        target_pct=99.9,
        threshold=1000.0,  # P99 ≤ 1000ms
        unit="ms",
    ),
}


# ── Cálculos puros (testáveis sem Redis) ──────────────────────────────────────

def _health(compliant: bool, budget_burned_pct: float) -> SloHealth:
    if not compliant:
        return SloHealth.breaching
    if budget_burned_pct > 50.0:
        return SloHealth.at_risk
    return SloHealth.healthy


def compute_availability_slo(overview: MetricsOverview) -> SloStatus:
    """
    SLO de disponibilidade: taxa de erros 5xx deve ser ≤ threshold.
    Budget consumido = current_error_rate / threshold.
    """
    slo = SLOS["availability"]
    current = overview.error_rate_5xx_pct
    budget_pct = slo.error_budget_pct   # 0.5%
    compliant = current <= slo.threshold

    consumed = min(current, budget_pct)
    remaining = max(0.0, budget_pct - current)
    burned = min(100.0, (current / budget_pct * 100)) if budget_pct > 0 else 0.0

    return SloStatus(
        name=slo.name,
        slo_id=slo.slo_id,
        target_pct=slo.target_pct,
        threshold=slo.threshold,
        unit=slo.unit,
        current_value=round(current, 4),
        compliant=compliant,
        error_budget_pct=round(budget_pct, 4),
        budget_consumed_pct=round(consumed, 4),
        budget_remaining_pct=round(remaining, 4),
        budget_burned_pct=round(burned, 1),
        health=_health(compliant, burned),
    )


def compute_latency_slo(rt: ResponseTimesData, slo_key: str) -> SloStatus:
    """
    SLO de latência: percentil deve estar abaixo do threshold.
    Budget consumido proporcional à proximidade do threshold.
    """
    slo = SLOS[slo_key]
    attr = "p95_ms" if slo_key == "latency_p95" else "p99_ms"
    current = getattr(rt, attr)

    budget_pct = slo.error_budget_pct
    compliant = current <= slo.threshold

    # Budget: quanto do threshold já consumimos
    burned = min(100.0, (current / slo.threshold * 100)) if slo.threshold > 0 else 0.0
    consumed = round(budget_pct * burned / 100, 4)
    remaining = round(max(0.0, budget_pct - consumed), 4)

    return SloStatus(
        name=slo.name,
        slo_id=slo.slo_id,
        target_pct=slo.target_pct,
        threshold=slo.threshold,
        unit=slo.unit,
        current_value=round(current, 2),
        compliant=compliant,
        error_budget_pct=round(budget_pct, 4),
        budget_consumed_pct=consumed,
        budget_remaining_pct=remaining,
        budget_burned_pct=round(burned, 1),
        health=_health(compliant, burned),
    )


def build_slo_report(overview: MetricsOverview, rt: ResponseTimesData) -> SloStatusReport:
    """Constrói o relatório completo de SLOs a partir das métricas atuais."""
    statuses = [
        compute_availability_slo(overview),
        compute_latency_slo(rt, "latency_p95"),
        compute_latency_slo(rt, "latency_p99"),
    ]

    overall = max(statuses, key=lambda s: _HEALTH_RANK[s.health]).health

    return SloStatusReport(
        timestamp=datetime.now(timezone.utc),
        window="session",
        requests_total=overview.requests_total,
        sample_count=rt.sample_count,
        slos=statuses,
        overall_health=overall,
    )
