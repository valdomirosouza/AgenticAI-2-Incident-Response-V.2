"""
Circuit breaker para chamadas à Anthropic API — S4-04 (SDD §9.4.2).

Padrão de resiliência: falhas transitórias disparam retry com backoff exponencial
(tenacity); falhas consecutivas abrem o circuito, que se recupera automaticamente
após `cb_recovery_timeout_s` segundos.

Estados:
  CLOSED    — operação normal; falhas são contadas
  OPEN      — circuito aberto; chamadas rejeitadas imediatamente
  HALF_OPEN — sondagem de recuperação; se bem-sucedida, fecha o circuito

Integração com orquestrador:
  - SpecialistAgent.analyze() → call_anthropic_with_retry()
  - orchestrator._synthesize() → call_anthropic_with_retry()
  - Quando circuito aberto → AnthropicCircuitOpenError → fallback rule-based
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

import anthropic
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger(__name__)

# Exceções que justificam retry + penalidade no circuito (transitórias)
_RETRYABLE_EXCEPTIONS = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.InternalServerError,
    anthropic.RateLimitError,
)


class AnthropicCircuitOpenError(RuntimeError):
    """Raised when the circuit breaker is OPEN and the call is rejected."""


class CircuitState(str, Enum):
    closed = "closed"
    open = "open"
    half_open = "half_open"


@dataclass
class CircuitBreaker:
    """
    Circuit breaker com estado compartilhado entre todos os agentes (singleton).

    failure_threshold  — falhas consecutivas para abrir o circuito
    recovery_timeout   — segundos até tentar a recuperação (half-open)
    """

    failure_threshold: int = 3
    recovery_timeout: float = 60.0

    _state: CircuitState = field(default=CircuitState.closed, init=False, repr=False)
    _consecutive_failures: int = field(default=0, init=False, repr=False)
    _opened_at: float = field(default=0.0, init=False, repr=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.open:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.half_open
                logger.info(
                    "Circuit breaker → HALF_OPEN after %.0fs (recovery probe allowed)",
                    elapsed,
                )
        return self._state

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.open

    def record_success(self) -> None:
        if self._state != CircuitState.closed:
            logger.info(
                "Circuit breaker → CLOSED (Anthropic API recovered after %d consecutive failures)",
                self._consecutive_failures,
            )
        self._state = CircuitState.closed
        self._consecutive_failures = 0

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            if self._state != CircuitState.open:
                logger.error(
                    "Circuit breaker → OPEN after %d consecutive failures — Anthropic API degraded",
                    self._consecutive_failures,
                )
                self._opened_at = time.monotonic()
            self._state = CircuitState.open

    def reset(self) -> None:
        """Resets to CLOSED state. Used in tests only."""
        self._state = CircuitState.closed
        self._consecutive_failures = 0
        self._opened_at = 0.0


# ── Singleton — estado compartilhado entre todos os agentes ──────────────────
_cb: CircuitBreaker | None = None


def _get_cb() -> CircuitBreaker:
    global _cb
    if _cb is None:
        _cb = CircuitBreaker(
            failure_threshold=settings.cb_failure_threshold,
            recovery_timeout=settings.cb_recovery_timeout_s,
        )
    return _cb


def get_circuit_state() -> CircuitState:
    """Retorna o estado atual do circuito. Útil para health checks e observabilidade."""
    return _get_cb().state


def reset_circuit_for_testing() -> None:
    """Reseta o circuito para CLOSED. Apenas para testes."""
    _get_cb().reset()


# ── Wrapper principal ─────────────────────────────────────────────────────────

async def call_anthropic_with_retry(
    coro_fn: Callable[..., Coroutine[Any, Any, Any]],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Executa uma chamada à Anthropic API com:
      1. Verificação do circuit breaker (rejeição imediata se OPEN)
      2. Retry com backoff exponencial via tenacity (até cb_max_retries tentativas)
      3. Atualização do estado do circuito após sucesso ou falha

    Args:
        coro_fn: função async da SDK Anthropic (e.g. client.messages.create)
        *args / **kwargs: argumentos passados diretamente ao coro_fn

    Raises:
        AnthropicCircuitOpenError: se o circuito estiver OPEN
        anthropic.*Error: re-raised após esgotar as tentativas de retry
    """
    cb = _get_cb()

    if cb.is_open:
        logger.warning(
            "Circuit breaker OPEN — rejecting Anthropic API call immediately "
            "(%.0fs since opened)",
            time.monotonic() - cb._opened_at,
        )
        raise AnthropicCircuitOpenError(
            "Anthropic API circuit breaker is OPEN — falling back to rule-based analysis"
        )

    @retry(
        retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
        stop=stop_after_attempt(settings.cb_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _attempt() -> Any:
        return await coro_fn(*args, **kwargs)

    try:
        result = await _attempt()
        cb.record_success()
        return result
    except _RETRYABLE_EXCEPTIONS as exc:
        logger.error(
            "Anthropic API call failed after %d retries: %s — recording circuit failure",
            settings.cb_max_retries,
            exc,
        )
        cb.record_failure()
        raise
