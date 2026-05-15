"""
Testes para o circuit breaker da Anthropic API — S4-04 (SDD §9.4.2).

Cobre:
  - Transições de estado: CLOSED → OPEN → HALF_OPEN → CLOSED
  - Retry com tenacity (backoff exponencial em erros transitórios)
  - Rejeição imediata quando circuito está OPEN
  - Integração com _synthesize() e SpecialistAgent.analyze()
"""

import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic

from app.agents.anthropic_circuit_breaker import (
    AnthropicCircuitOpenError,
    CircuitBreaker,
    CircuitState,
    call_anthropic_with_retry,
    get_circuit_state,
    reset_circuit_for_testing,
)
from app.models.report import Severity

# Apenas testes async são marcados individualmente (pytestmark global causaria
# warnings em testes síncronos da máquina de estados)


# ── Fixture: garante circuito CLOSED entre testes ─────────────────────────────

@pytest.fixture(autouse=True)
def reset_cb():
    reset_circuit_for_testing()
    yield
    reset_circuit_for_testing()


# ── CircuitBreaker: máquina de estados ────────────────────────────────────────

def test_initial_state_is_closed():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    assert cb.state == CircuitState.closed
    assert not cb.is_open


def test_single_failure_does_not_open_circuit():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    cb.record_failure()
    assert cb.state == CircuitState.closed


def test_circuit_opens_after_threshold_failures():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    for _ in range(3):
        cb.record_failure()
    assert cb.state == CircuitState.open
    assert cb.is_open


def test_circuit_does_not_open_below_threshold():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    for _ in range(2):
        cb.record_failure()
    assert cb.state == CircuitState.closed


def test_success_resets_failure_count():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
    cb.record_failure()
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    # Após reset pelo sucesso, 1 falha não abre o circuito
    assert cb.state == CircuitState.closed


def test_circuit_transitions_to_half_open_after_timeout():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.open
    time.sleep(0.15)
    assert cb.state == CircuitState.half_open


def test_success_in_half_open_closes_circuit():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.05)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.1)
    assert cb.state == CircuitState.half_open
    cb.record_success()
    assert cb.state == CircuitState.closed


def test_failure_in_half_open_reopens_circuit():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.05)
    cb.record_failure()
    cb.record_failure()
    time.sleep(0.1)
    cb.state  # transição para half_open
    cb.record_failure()
    assert cb.state == CircuitState.open


def test_reset_returns_to_closed():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.is_open
    cb.reset()
    assert cb.state == CircuitState.closed
    assert not cb.is_open


# ── call_anthropic_with_retry: chamadas com sucesso ───────────────────────────

@pytest.mark.asyncio
async def test_successful_call_returns_result():
    mock_fn = AsyncMock(return_value="result-ok")
    result = await call_anthropic_with_retry(mock_fn, "arg1", key="val")
    assert result == "result-ok"
    mock_fn.assert_awaited_once_with("arg1", key="val")


@pytest.mark.asyncio
async def test_successful_call_closes_circuit():
    mock_fn = AsyncMock(return_value="ok")
    await call_anthropic_with_retry(mock_fn)
    assert get_circuit_state() == CircuitState.closed


# ── call_anthropic_with_retry: retry em erros transitórios ───────────────────

@pytest.mark.asyncio
async def test_retries_on_connection_error_then_succeeds():
    mock_fn = AsyncMock(
        side_effect=[anthropic.APIConnectionError(request=MagicMock()), "success"]
    )
    with patch("app.agents.anthropic_circuit_breaker.settings") as s:
        s.cb_max_retries = 3
        s.cb_failure_threshold = 3
        s.cb_recovery_timeout_s = 60.0
        result = await call_anthropic_with_retry(mock_fn)
    assert result == "success"
    assert mock_fn.await_count == 2


@pytest.mark.asyncio
async def test_retries_on_rate_limit_then_succeeds():
    mock_fn = AsyncMock(
        side_effect=[
            anthropic.RateLimitError(message="rate limit", response=MagicMock(), body={}),
            "ok",
        ]
    )
    with patch("app.agents.anthropic_circuit_breaker.settings") as s:
        s.cb_max_retries = 3
        s.cb_failure_threshold = 3
        s.cb_recovery_timeout_s = 60.0
        result = await call_anthropic_with_retry(mock_fn)
    assert result == "ok"


@pytest.mark.asyncio
async def test_exhausted_retries_records_failure_and_raises():
    mock_fn = AsyncMock(
        side_effect=anthropic.APIConnectionError(request=MagicMock())
    )
    with patch("app.agents.anthropic_circuit_breaker.settings") as s:
        s.cb_max_retries = 2
        s.cb_failure_threshold = 3
        s.cb_recovery_timeout_s = 60.0
        with pytest.raises(anthropic.APIConnectionError):
            await call_anthropic_with_retry(mock_fn)

    # Após 1 falha (threshold=3), circuito ainda fechado mas contagem incrementou
    assert get_circuit_state() == CircuitState.closed


@pytest.mark.asyncio
async def test_three_exhausted_retries_opens_circuit():
    mock_fn = AsyncMock(
        side_effect=anthropic.APIConnectionError(request=MagicMock())
    )
    with patch("app.agents.anthropic_circuit_breaker.settings") as s:
        s.cb_max_retries = 1
        s.cb_failure_threshold = 3
        s.cb_recovery_timeout_s = 60.0
        for _ in range(3):
            with pytest.raises(anthropic.APIConnectionError):
                await call_anthropic_with_retry(mock_fn)

    assert get_circuit_state() == CircuitState.open


# ── call_anthropic_with_retry: circuito aberto ───────────────────────────────

@pytest.mark.asyncio
async def test_open_circuit_raises_immediately_without_calling_fn():
    mock_fn = AsyncMock(return_value="should-not-be-called")

    # Abrir o circuito manualmente
    from app.agents.anthropic_circuit_breaker import _get_cb
    cb = _get_cb()
    cb._state = CircuitState.open
    cb._opened_at = time.monotonic()

    with pytest.raises(AnthropicCircuitOpenError):
        await call_anthropic_with_retry(mock_fn)

    mock_fn.assert_not_awaited()


# ── Integração: _synthesize com circuito aberto ───────────────────────────────

@pytest.mark.asyncio
async def test_synthesize_returns_fallback_when_circuit_open():
    from app.agents.orchestrator import _synthesize
    from app.models.report import SpecialistFinding, Severity

    findings = [
        SpecialistFinding(specialist="Latency", severity=Severity.critical,
                          summary="P99 high", details="2300ms"),
        SpecialistFinding(specialist="Errors", severity=Severity.ok,
                          summary="OK", details="<1%"),
    ]

    # Abrir o circuito
    from app.agents.anthropic_circuit_breaker import _get_cb
    _get_cb()._state = CircuitState.open
    _get_cb()._opened_at = time.monotonic()

    report = await _synthesize(findings, [])

    assert report.overall_severity == Severity.critical
    assert "Circuit Open" in report.title
    assert report.similar_incidents == []


# ── Integração: SpecialistAgent com circuito aberto ───────────────────────────

@pytest.mark.asyncio
async def test_specialist_returns_warning_finding_when_circuit_open():
    from app.agents.specialists.latency import LatencyAgent
    from app.agents.anthropic_circuit_breaker import _get_cb

    _get_cb()._state = CircuitState.open
    _get_cb()._opened_at = time.monotonic()

    agent = LatencyAgent()
    finding = await agent.analyze()

    assert finding.specialist == "Latency"
    assert finding.severity == Severity.warning
    assert "circuit open" in finding.summary.lower()


# ── get_circuit_state ─────────────────────────────────────────────────────────

def test_get_circuit_state_returns_closed_initially():
    assert get_circuit_state() == CircuitState.closed
