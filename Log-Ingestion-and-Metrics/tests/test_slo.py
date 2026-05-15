"""
Testes unitários para o módulo SLO — S4-01 (SDD §3.2.1).

Cobre:
  - compute_availability_slo: budget ok, at risk, breaching
  - compute_latency_slo: p95 e p99, estados saudáveis, at risk, breaching
  - build_slo_report: integração, overall_health = pior estado
  - SloDefinition.error_budget_pct: cálculo do budget total
"""

import pytest

from app.models import MetricsOverview, ResponseTimesData, SloHealth
from app.slo import (
    SLOS,
    SloDefinition,
    build_slo_report,
    compute_availability_slo,
    compute_latency_slo,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _overview(total: int = 1000, errors_5xx: int = 0, errors_4xx: int = 0) -> MetricsOverview:
    return MetricsOverview(
        requests_total=total,
        errors_4xx=errors_4xx,
        errors_5xx=errors_5xx,
        error_rate_4xx_pct=round(errors_4xx / total * 100, 2) if total else 0.0,
        error_rate_5xx_pct=round(errors_5xx / total * 100, 2) if total else 0.0,
    )


def _rt(p50: float = 100.0, p95: float = 200.0, p99: float = 400.0, count: int = 100) -> ResponseTimesData:
    return ResponseTimesData(p50_ms=p50, p95_ms=p95, p99_ms=p99, sample_count=count)


# ── SloDefinition ─────────────────────────────────────────────────────────────

def test_slo_definition_error_budget_availability():
    slo = SLOS["availability"]
    assert slo.error_budget_pct == 0.5  # 100 - 99.5

def test_slo_definition_error_budget_latency_p95():
    slo = SLOS["latency_p95"]
    assert slo.error_budget_pct == 1.0  # 100 - 99.0

def test_slo_definition_error_budget_latency_p99():
    slo = SLOS["latency_p99"]
    assert slo.error_budget_pct == 0.1  # 100 - 99.9


# ── compute_availability_slo ──────────────────────────────────────────────────

def test_availability_healthy_no_errors():
    ov = _overview(total=1000, errors_5xx=0)
    status = compute_availability_slo(ov)
    assert status.compliant is True
    assert status.health == SloHealth.healthy
    assert status.current_value == 0.0
    assert status.budget_remaining_pct == 0.5
    assert status.budget_burned_pct == 0.0


def test_availability_healthy_low_errors():
    # 1 erro em 1000 = 0.1% → dentro do budget (0.5%)
    ov = _overview(total=1000, errors_5xx=1)
    status = compute_availability_slo(ov)
    assert status.compliant is True
    assert status.health == SloHealth.healthy
    assert status.current_value == 0.1
    assert status.budget_burned_pct == pytest.approx(20.0, abs=1.0)


def test_availability_at_risk():
    # 3 erros em 1000 = 0.3% → 60% do budget consumido → at_risk
    ov = _overview(total=1000, errors_5xx=3)
    status = compute_availability_slo(ov)
    assert status.compliant is True
    assert status.health == SloHealth.at_risk
    assert status.budget_burned_pct == pytest.approx(60.0, abs=1.0)


def test_availability_breaching():
    # 6 erros em 1000 = 0.6% → acima do threshold (0.5%)
    ov = _overview(total=1000, errors_5xx=6)
    status = compute_availability_slo(ov)
    assert status.compliant is False
    assert status.health == SloHealth.breaching
    assert status.current_value == 0.6
    assert status.budget_burned_pct == 100.0


def test_availability_zero_requests():
    ov = _overview(total=0, errors_5xx=0)
    status = compute_availability_slo(ov)
    assert status.compliant is True
    assert status.current_value == 0.0
    assert status.health == SloHealth.healthy


def test_availability_fields_match_slo_definition():
    ov = _overview()
    status = compute_availability_slo(ov)
    slo = SLOS["availability"]
    assert status.slo_id == slo.slo_id
    assert status.target_pct == slo.target_pct
    assert status.threshold == slo.threshold
    assert status.unit == slo.unit
    assert status.error_budget_pct == slo.error_budget_pct


# ── compute_latency_slo (P95) ─────────────────────────────────────────────────

def test_latency_p95_healthy():
    rt = _rt(p95=200.0)
    status = compute_latency_slo(rt, "latency_p95")
    assert status.compliant is True
    assert status.health == SloHealth.healthy
    assert status.current_value == 200.0
    # burned = 200/500 * 100 = 40% → healthy (≤ 50%)
    assert status.budget_burned_pct == pytest.approx(40.0, abs=0.5)


def test_latency_p95_at_risk():
    # burned = 350/500 * 100 = 70% → at_risk (> 50%)
    rt = _rt(p95=350.0)
    status = compute_latency_slo(rt, "latency_p95")
    assert status.compliant is True
    assert status.health == SloHealth.at_risk
    assert status.budget_burned_pct == pytest.approx(70.0, abs=0.5)


def test_latency_p95_breaching():
    rt = _rt(p95=600.0)
    status = compute_latency_slo(rt, "latency_p95")
    assert status.compliant is False
    assert status.health == SloHealth.breaching
    assert status.budget_burned_pct == 100.0


def test_latency_p95_exactly_at_threshold():
    rt = _rt(p95=500.0)
    status = compute_latency_slo(rt, "latency_p95")
    assert status.compliant is True
    assert status.budget_burned_pct == 100.0
    # Threshold exato → compliant, mas budget_burned=100 → at_risk
    assert status.health == SloHealth.at_risk


def test_latency_p95_zero_ms():
    rt = _rt(p95=0.0)
    status = compute_latency_slo(rt, "latency_p95")
    assert status.compliant is True
    assert status.budget_burned_pct == 0.0
    assert status.health == SloHealth.healthy


# ── compute_latency_slo (P99) ─────────────────────────────────────────────────

def test_latency_p99_healthy():
    rt = _rt(p99=400.0)
    status = compute_latency_slo(rt, "latency_p99")
    assert status.compliant is True
    assert status.health == SloHealth.healthy
    # burned = 400/1000 * 100 = 40%
    assert status.budget_burned_pct == pytest.approx(40.0, abs=0.5)


def test_latency_p99_breaching():
    rt = _rt(p99=1200.0)
    status = compute_latency_slo(rt, "latency_p99")
    assert status.compliant is False
    assert status.health == SloHealth.breaching


def test_latency_p99_slo_id():
    rt = _rt()
    status = compute_latency_slo(rt, "latency_p99")
    assert status.slo_id == "latency_p99"
    assert status.unit == "ms"
    assert status.threshold == 1000.0


# ── build_slo_report ──────────────────────────────────────────────────────────

def test_build_slo_report_all_healthy():
    ov = _overview(total=1000, errors_5xx=0)
    rt = _rt(p95=100.0, p99=200.0)
    report = build_slo_report(ov, rt)

    assert report.overall_health == SloHealth.healthy
    assert len(report.slos) == 3
    slo_ids = {s.slo_id for s in report.slos}
    assert slo_ids == {"availability", "latency_p95", "latency_p99"}
    assert report.requests_total == 1000
    assert report.sample_count == 100
    assert report.window == "session"


def test_build_slo_report_overall_is_worst():
    # availability ok, p95 at_risk, p99 healthy → overall = at_risk
    ov = _overview(total=1000, errors_5xx=0)
    rt = _rt(p95=350.0, p99=200.0)
    report = build_slo_report(ov, rt)
    assert report.overall_health == SloHealth.at_risk


def test_build_slo_report_one_breaching():
    # P95 breaching → overall = breaching (pior estado)
    ov = _overview(total=1000, errors_5xx=0)
    rt = _rt(p95=600.0, p99=200.0)
    report = build_slo_report(ov, rt)
    assert report.overall_health == SloHealth.breaching


def test_build_slo_report_availability_breaching():
    ov = _overview(total=1000, errors_5xx=6)
    rt = _rt(p95=100.0, p99=200.0)
    report = build_slo_report(ov, rt)
    assert report.overall_health == SloHealth.breaching


def test_build_slo_report_has_timestamp():
    ov = _overview()
    rt = _rt()
    report = build_slo_report(ov, rt)
    assert report.timestamp is not None
