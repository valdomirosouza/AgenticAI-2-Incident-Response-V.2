"""
Testes dos helpers síncronos e invariantes de negócio.
Esses helpers concentram a lógica que os handlers async delegam,
tornando a cobertura independente da limitação do coverage.py com Python 3.11.
"""

import pytest
import fakeredis.aioredis
from datetime import datetime, timezone

from app.routers.metrics import (
    build_overview,
    build_response_times,
    build_rps,
    percentile_rank,
)
from app.ingestion import ingest_log, get_redis
from app.models import HaproxyLog

pytestmark = pytest.mark.asyncio

SAMPLE = HaproxyLog(
    frontend="http-in",
    backend="web-backend",
    status_code=200,
    time_response=42.5,
    bytes_read=1024,
    request_method="GET",
    request_path="/health",
)


# ─── build_overview ───────────────────────────────────────────────────────────

def test_build_overview_zero():
    result = build_overview(0, 0, 0)
    assert result.requests_total == 0
    assert result.error_rate_4xx_pct == 0.0
    assert result.error_rate_5xx_pct == 0.0


def test_build_overview_5xx_rate():
    result = build_overview(total=100, errors_4xx=0, errors_5xx=5)
    assert result.error_rate_5xx_pct == 5.0
    assert result.error_rate_4xx_pct == 0.0


def test_build_overview_4xx_rate():
    result = build_overview(total=20, errors_4xx=2, errors_5xx=0)
    assert result.error_rate_4xx_pct == 10.0


def test_build_overview_mixed_errors():
    result = build_overview(total=100, errors_4xx=10, errors_5xx=5)
    assert result.error_rate_4xx_pct == 10.0
    assert result.error_rate_5xx_pct == 5.0


def test_build_overview_all_fields_present():
    result = build_overview(50, 3, 2)
    assert hasattr(result, "requests_total")
    assert hasattr(result, "errors_4xx")
    assert hasattr(result, "errors_5xx")
    assert hasattr(result, "error_rate_4xx_pct")
    assert hasattr(result, "error_rate_5xx_pct")


# ─── percentile_rank ──────────────────────────────────────────────────────────

def test_percentile_rank_p50():
    assert percentile_rank(100, 50) == 49


def test_percentile_rank_p95():
    assert percentile_rank(100, 95) == 94


def test_percentile_rank_p99():
    assert percentile_rank(100, 99) == 98


def test_percentile_rank_floor_at_zero():
    assert percentile_rank(1, 50) == 0


def test_percentile_rank_small_sample():
    assert percentile_rank(5, 50) >= 0


# ─── build_response_times ─────────────────────────────────────────────────────

def test_build_response_times_with_data():
    scores = (
        [("member1", 50.0)],
        [("member1", 95.0)],
        [("member1", 99.0)],
    )
    result = build_response_times(10, scores)
    assert result.p50_ms == 50.0
    assert result.p95_ms == 95.0
    assert result.p99_ms == 99.0
    assert result.sample_count == 10


def test_build_response_times_empty_scores():
    result = build_response_times(1, ([], [], []))
    assert result.p50_ms == 0.0
    assert result.p95_ms == 0.0
    assert result.p99_ms == 0.0


def test_build_response_times_monotonic():
    scores = (
        [("m", 10.0)],
        [("m", 50.0)],
        [("m", 90.0)],
    )
    result = build_response_times(100, scores)
    assert result.p50_ms <= result.p95_ms <= result.p99_ms


# ─── build_rps ────────────────────────────────────────────────────────────────

def test_build_rps_empty_buckets():
    now = datetime.now(timezone.utc)
    result = build_rps({}, now)
    assert result.current_rps == 0.0
    assert result.buckets == {}


def test_build_rps_current_minute_in_bucket():
    now = datetime.now(timezone.utc)
    minute = now.strftime("%Y-%m-%dT%H:%M")
    result = build_rps({minute: 60}, now)
    assert result.current_rps == 1.0  # 60 req / 60s = 1 RPS
    assert result.buckets[minute] == 60


def test_build_rps_only_past_minute():
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    past = (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M")
    result = build_rps({past: 120}, now)
    assert result.current_rps == 0.0  # Não é o minuto atual


# ─── get_redis retornando normalmente ────────────────────────────────────────

async def test_get_redis_returns_client_when_set():
    """Cobre o branch `return _REDIS_CLIENT` em get_redis (linha 32)."""
    from app import ingestion
    from unittest.mock import AsyncMock

    mock_client = AsyncMock()
    ingestion._REDIS_CLIENT = mock_client
    result = await ingestion.get_redis()
    assert result is mock_client
    ingestion._REDIS_CLIENT = None  # Limpar estado global


# ─── ingest_log — linhas 79-82 (Prometheus + debug log) ─────────────────────

async def test_ingest_log_prometheus_counter_incremented():
    """Cobre linhas 79-82: Prometheus labels e logger.debug em ingest_log."""
    from app import metrics_registry
    from unittest.mock import patch, MagicMock

    r = fakeredis.aioredis.FakeRedis(decode_responses=True)

    inc_called_with = []
    original = metrics_registry.HAPROXY_LOGS_INGESTED.labels

    def capture_labels(**kwargs):
        inc_called_with.append(kwargs)
        counter = MagicMock()
        counter.inc = MagicMock()
        return counter

    with patch.object(metrics_registry.HAPROXY_LOGS_INGESTED, "labels", side_effect=capture_labels):
        await ingest_log(SAMPLE, r)

    assert len(inc_called_with) == 1
    assert inc_called_with[0]["backend"] == "web-backend"
    assert inc_called_with[0]["status_class"] == "2xx"

    await r.aclose()


async def test_ingest_log_debug_log_emitted():
    """Logger.debug deve ser chamado com campos corretos após ingestão."""
    import logging
    from unittest.mock import patch, MagicMock

    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    log_calls = []

    original_debug = logging.Logger.debug

    def capture_debug(self, msg, *args, **kwargs):
        if "Log ingested" in msg:
            log_calls.append(kwargs.get("extra", {}))
        return original_debug(self, msg, *args, **kwargs)

    with patch.object(logging.Logger, "debug", capture_debug):
        await ingest_log(SAMPLE, r)

    assert any(c.get("backend") == "web-backend" for c in log_calls)
    await r.aclose()
