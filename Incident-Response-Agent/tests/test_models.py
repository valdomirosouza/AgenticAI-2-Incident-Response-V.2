"""Testes para models/report.py e models/llm_response.py."""

import pytest
from datetime import timezone
from pydantic import ValidationError
from app.models.report import Severity, max_severity, IncidentReport, SpecialistFinding
from app.models.llm_response import OrchestratorResponse


# ─── Severity ─────────────────────────────────────────────────────────────────

def test_severity_values():
    assert Severity.ok.value == "ok"
    assert Severity.warning.value == "warning"
    assert Severity.critical.value == "critical"


# ─── max_severity ─────────────────────────────────────────────────────────────

def test_max_severity_empty_returns_ok():
    assert max_severity([]) == Severity.ok


def test_max_severity_single():
    assert max_severity([Severity.warning]) == Severity.warning


def test_max_severity_returns_highest():
    result = max_severity([Severity.ok, Severity.critical, Severity.warning])
    assert result == Severity.critical


def test_max_severity_all_ok():
    assert max_severity([Severity.ok, Severity.ok]) == Severity.ok


def test_max_severity_warning_beats_ok():
    assert max_severity([Severity.ok, Severity.warning]) == Severity.warning


# ─── SpecialistFinding ────────────────────────────────────────────────────────

def test_specialist_finding_stores_fields():
    f = SpecialistFinding(
        specialist="Latency",
        severity=Severity.warning,
        summary="P99 > 500ms",
        details="Measured 750ms at 14:00 UTC",
    )
    assert f.specialist == "Latency"
    assert f.severity == Severity.warning
    assert "750" in f.details


# ─── IncidentReport ───────────────────────────────────────────────────────────

def test_incident_report_defaults():
    report = IncidentReport(
        overall_severity=Severity.ok,
        title="System Healthy",
        diagnosis="All good.",
    )
    assert report.escalation_recommended is False
    assert report.llm_calls_count == 0
    assert report.kb_score_max is None
    assert report.incident_phase == "response"
    assert report.analysis_duration_seconds == 0.0
    assert report.specialist_model_version == ""


def test_incident_report_timestamp_is_tz_aware():
    report = IncidentReport(overall_severity=Severity.ok, title="T", diagnosis="D")
    assert report.timestamp.tzinfo is not None


def test_incident_report_human_fields_optional():
    report = IncidentReport(overall_severity=Severity.ok, title="T", diagnosis="D")
    assert report.human_severity_validation is None
    assert report.human_ttd_minutes is None
    assert report.human_ttr_minutes is None


def test_incident_report_accepts_all_fields():
    report = IncidentReport(
        overall_severity=Severity.critical,
        title="Redis OOM",
        diagnosis="Redis hit maxmemory limit.",
        recommendations=["Change eviction policy"],
        root_causes=["noeviction policy"],
        triggers=["Traffic spike"],
        incident_commander_brief="Redis OOM — apply allkeys-lru now.",
        escalation_recommended=True,
        llm_calls_count=5,
        kb_chunks_retrieved=3,
        kb_score_max=0.91,
        specialist_model_version="1.0.0",
    )
    assert report.escalation_recommended is True
    assert report.kb_score_max == 0.91


# ─── OrchestratorResponse ─────────────────────────────────────────────────────

def test_orchestrator_response_valid():
    data = {
        "overall_severity": "critical",
        "title": "High error rate",
        "diagnosis": "5xx rate at 15% across all backends.",
        "recommendations": ["Restart app pods", "Scale Redis"],
        "root_causes": ["Missing circuit breaker"],
        "triggers": ["Traffic spike 4x baseline"],
        "incident_commander_brief": "Critical: restart app pods immediately.",
    }
    resp = OrchestratorResponse(**data)
    assert resp.overall_severity == Severity.critical
    assert len(resp.recommendations) == 2
    assert resp.root_causes == ["Missing circuit breaker"]


def test_orchestrator_response_recommendations_not_list_raises():
    with pytest.raises(ValidationError, match="lista"):
        OrchestratorResponse(
            overall_severity="ok",
            title="T",
            diagnosis="D",
            recommendations="not a list",
        )


def test_orchestrator_response_truncates_long_recommendations():
    resp = OrchestratorResponse(
        overall_severity="ok",
        title="T",
        diagnosis="D",
        recommendations=["x" * 400],
    )
    assert len(resp.recommendations[0]) == 300


def test_orchestrator_response_limits_to_5_recommendations():
    resp = OrchestratorResponse(
        overall_severity="ok",
        title="T",
        diagnosis="D",
        recommendations=["a", "b", "c", "d", "e", "f", "g"],
    )
    assert len(resp.recommendations) == 5


def test_orchestrator_response_non_list_root_causes_becomes_empty():
    resp = OrchestratorResponse(
        overall_severity="ok",
        title="T",
        diagnosis="D",
        recommendations=["action"],
        root_causes="not a list",
    )
    assert resp.root_causes == []


def test_orchestrator_response_non_list_triggers_becomes_empty():
    resp = OrchestratorResponse(
        overall_severity="ok",
        title="T",
        diagnosis="D",
        recommendations=["action"],
        triggers=42,
    )
    assert resp.triggers == []


def test_orchestrator_response_truncates_root_causes():
    resp = OrchestratorResponse(
        overall_severity="ok",
        title="T",
        diagnosis="D",
        recommendations=["a"],
        root_causes=["x" * 400],
    )
    assert len(resp.root_causes[0]) == 300
