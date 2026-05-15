"""
Análise determinística sem LLM — ativada quando Anthropic API está indisponível.
Garante operação degradada com diagnóstico baseado em regras (SDD §9.4.3).
"""

import logging
from datetime import datetime, timezone

from app.config import settings
from app.models.report import IncidentReport, Severity, SpecialistFinding

logger = logging.getLogger(__name__)


def analyze_by_rules(metrics: dict) -> IncidentReport:
    findings: list[SpecialistFinding] = []

    # Regra de latência
    p99 = metrics.get("response_times", {}).get("p99_ms", 0) or 0
    if p99 > settings.latency_p99_threshold_ms:
        findings.append(
            SpecialistFinding(
                specialist="Latency",
                severity=Severity.critical,
                summary=f"P99 latency {p99}ms exceeds {settings.latency_p99_threshold_ms}ms threshold",
                details="Rule-based analysis (LLM unavailable)",
            )
        )

    # Regra de erros
    error_rate = metrics.get("overview", {}).get("error_rate_5xx_pct", 0) or 0
    if error_rate > settings.error_rate_5xx_threshold_pct:
        findings.append(
            SpecialistFinding(
                specialist="Errors",
                severity=Severity.critical,
                summary=f"5xx error rate {error_rate}% exceeds {settings.error_rate_5xx_threshold_pct}%",
                details="Rule-based analysis (LLM unavailable)",
            )
        )

    overall = (
        max(findings, key=lambda f: {"ok": 0, "warning": 1, "critical": 2}[f.severity.value]).severity
        if findings
        else Severity.ok
    )

    logger.warning("Fallback rule-based analysis activated — LLM unavailable")

    return IncidentReport(
        timestamp=datetime.now(timezone.utc),
        overall_severity=overall,
        title="Rule-Based Analysis (LLM Degraded)",
        diagnosis="LLM unavailable. Analysis performed by deterministic threshold rules.",
        recommendations=["Check Anthropic API availability", "Review metrics manually in Grafana"],
        findings=findings,
        similar_incidents=[],
    )
