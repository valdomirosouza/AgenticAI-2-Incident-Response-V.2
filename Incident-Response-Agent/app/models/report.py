from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    ok = "ok"
    warning = "warning"
    critical = "critical"


_SEVERITY_RANK: dict[Severity, int] = {
    Severity.ok: 0,
    Severity.warning: 1,
    Severity.critical: 2,
}


def max_severity(severities: list[Severity]) -> Severity:
    if not severities:
        return Severity.ok
    return max(severities, key=lambda s: _SEVERITY_RANK[s])


class SpecialistFinding(BaseModel):
    specialist: str
    severity: Severity
    summary: str
    details: str


class IncidentReport(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    overall_severity: Severity
    title: str
    diagnosis: str
    recommendations: list[str] = Field(default_factory=list)
    findings: list[SpecialistFinding] = Field(default_factory=list)
    similar_incidents: list[str] = Field(default_factory=list)

    # Campos de análise causal (SDD §9.13.4)
    root_causes: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)

    # Suporte ao IMAG / Incident Commander (SDD §9.13.7)
    incident_commander_brief: str = ""
    incident_phase: str = "response"
    escalation_recommended: bool = False

    # Métricas para avaliação científica da dissertação (SDD §10.4)
    analysis_duration_seconds: float = 0.0
    llm_calls_count: int = 0
    kb_chunks_retrieved: int = 0
    kb_score_max: Optional[float] = None
    specialist_model_version: str = ""

    # Preenchidos pelo engenheiro pós-resolução
    human_severity_validation: Optional[str] = None
    human_ttd_minutes: Optional[float] = None
    human_ttr_minutes: Optional[float] = None
