"""Testes para fallback_analyzer — análise determinística sem LLM."""

import pytest
from unittest.mock import patch
from app.agents.fallback_analyzer import analyze_by_rules
from app.models.report import Severity

METRICS_CLEAN = {
    "response_times": {"p99_ms": 100},
    "overview": {"error_rate_5xx_pct": 0.5},
}
METRICS_HIGH_LATENCY = {
    "response_times": {"p99_ms": 2000},
    "overview": {"error_rate_5xx_pct": 0.0},
}
METRICS_HIGH_ERRORS = {
    "response_times": {"p99_ms": 100},
    "overview": {"error_rate_5xx_pct": 10.0},
}
METRICS_BOTH_CRITICAL = {
    "response_times": {"p99_ms": 2000},
    "overview": {"error_rate_5xx_pct": 10.0},
}


def test_all_within_thresholds_returns_ok():
    report = analyze_by_rules(METRICS_CLEAN)
    assert report.overall_severity == Severity.ok
    assert len(report.findings) == 0


def test_high_latency_adds_latency_finding():
    report = analyze_by_rules(METRICS_HIGH_LATENCY)
    assert any(f.specialist == "Latency" for f in report.findings)


def test_high_latency_is_critical():
    report = analyze_by_rules(METRICS_HIGH_LATENCY)
    assert report.overall_severity == Severity.critical


def test_high_error_rate_adds_errors_finding():
    report = analyze_by_rules(METRICS_HIGH_ERRORS)
    assert any(f.specialist == "Errors" for f in report.findings)


def test_high_error_rate_is_critical():
    report = analyze_by_rules(METRICS_HIGH_ERRORS)
    assert report.overall_severity == Severity.critical


def test_both_high_returns_two_findings():
    report = analyze_by_rules(METRICS_BOTH_CRITICAL)
    assert len(report.findings) == 2
    assert report.overall_severity == Severity.critical


def test_missing_keys_dont_crash():
    report = analyze_by_rules({})
    assert report.overall_severity == Severity.ok


def test_none_values_dont_crash():
    report = analyze_by_rules({"response_times": {"p99_ms": None}, "overview": {"error_rate_5xx_pct": None}})
    assert report.overall_severity == Severity.ok


def test_latency_finding_summary_includes_threshold():
    with patch("app.agents.fallback_analyzer.settings") as s:
        s.latency_p99_threshold_ms = 500.0
        s.error_rate_5xx_threshold_pct = 99.0
        report = analyze_by_rules({"response_times": {"p99_ms": 900}, "overview": {"error_rate_5xx_pct": 0}})
    assert "500" in report.findings[0].summary


def test_error_finding_summary_includes_threshold():
    with patch("app.agents.fallback_analyzer.settings") as s:
        s.latency_p99_threshold_ms = 99999.0
        s.error_rate_5xx_threshold_pct = 1.0
        report = analyze_by_rules({"response_times": {"p99_ms": 0}, "overview": {"error_rate_5xx_pct": 10}})
    assert "1.0" in report.findings[0].summary


def test_fallback_report_has_recommendations():
    report = analyze_by_rules(METRICS_CLEAN)
    assert len(report.recommendations) > 0


def test_fallback_report_title_indicates_degraded():
    report = analyze_by_rules(METRICS_CLEAN)
    assert "Rule-Based" in report.title or "Degraded" in report.title


def test_fallback_report_similar_incidents_empty():
    report = analyze_by_rules(METRICS_CLEAN)
    assert report.similar_incidents == []
