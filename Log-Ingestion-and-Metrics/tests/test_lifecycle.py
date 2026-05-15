"""
Testes de cobertura para funções de ciclo de vida do Redis e branches descobertas.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.conftest import SAMPLE_LOG


pytestmark = pytest.mark.asyncio


# ─── init_redis / close_redis ────────────────────────────────────────────────

async def test_init_redis_calls_ping():
    """init_redis deve criar client e fazer ping."""
    from app import ingestion

    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)

    with patch("app.ingestion.aioredis.from_url", return_value=mock_client):
        await ingestion.init_redis("redis://localhost:6379", "")
        mock_client.ping.assert_called_once()

    # Limpa o estado global
    ingestion._REDIS_CLIENT = None


async def test_init_redis_with_password():
    """init_redis deve passar password ao from_url."""
    from app import ingestion

    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)

    with patch("app.ingestion.aioredis.from_url", return_value=mock_client) as mock_from_url:
        await ingestion.init_redis("redis://localhost:6379", "secret")
        call_kwargs = mock_from_url.call_args.kwargs
        assert call_kwargs["password"] == "secret"

    ingestion._REDIS_CLIENT = None


async def test_close_redis_calls_aclose():
    """close_redis deve fechar o client e zerar o estado global."""
    from app import ingestion

    mock_client = AsyncMock()
    ingestion._REDIS_CLIENT = mock_client

    await ingestion.close_redis()

    mock_client.aclose.assert_called_once()
    assert ingestion._REDIS_CLIENT is None


async def test_close_redis_noop_when_not_initialized():
    """close_redis não deve falhar se não houver client."""
    from app import ingestion

    ingestion._REDIS_CLIENT = None
    await ingestion.close_redis()  # Não deve levantar exceção


# ─── get_redis sem init ───────────────────────────────────────────────────────

async def test_get_redis_raises_when_not_initialized():
    """get_redis deve levantar RuntimeError se init_redis não foi chamado."""
    from app import ingestion

    ingestion._REDIS_CLIENT = None
    with pytest.raises(RuntimeError, match="Redis not initialized"):
        await ingestion.get_redis()


# ─── ingest_log — Prometheus counter e debug log ─────────────────────────────

async def test_ingest_log_calls_prometheus_counter(fake_redis):
    """ingest_log deve chamar o Prometheus counter após executar o pipeline."""
    from app.ingestion import ingest_log
    from app.models import HaproxyLog
    from app import metrics_registry

    log = HaproxyLog(**SAMPLE_LOG)

    original_inc = metrics_registry.HAPROXY_LOGS_INGESTED.labels

    calls = []

    def tracking_labels(**kwargs):
        calls.append(kwargs)
        return original_inc(**kwargs)

    with patch.object(metrics_registry.HAPROXY_LOGS_INGESTED, "labels", side_effect=tracking_labels):
        await ingest_log(log, fake_redis)

    assert len(calls) == 1
    assert calls[0]["backend"] == "web-backend"
    assert calls[0]["status_class"] == "2xx"


async def test_ingest_log_prometheus_counter_3xx(fake_redis):
    """ingest_log deve classificar status 3xx corretamente."""
    from app.ingestion import ingest_log
    from app.models import HaproxyLog

    log = HaproxyLog(**{**SAMPLE_LOG, "status_code": 301})
    await ingest_log(log, fake_redis)  # Não deve falhar


# ─── backends endpoint ────────────────────────────────────────────────────────

async def test_backends_returns_empty_when_no_data(client):
    """GET /metrics/backends sem logs ingeridos deve retornar dict vazio."""
    response = await client.get("/metrics/backends")
    assert response.status_code == 200
    data = response.json()
    assert "backends" in data
    assert isinstance(data["backends"], dict)


async def test_backends_returns_data_after_ingest(client):
    """GET /metrics/backends deve refletir os backends ingeridos."""
    await client.post("/logs", json=SAMPLE_LOG)
    await client.post("/logs", json={**SAMPLE_LOG, "backend": "api-backend"})

    response = await client.get("/metrics/backends")
    data = response.json()

    assert "web-backend" in data["backends"]
    assert "api-backend" in data["backends"]
    assert data["backends"]["web-backend"] == 1
    assert data["backends"]["api-backend"] == 1


# ─── overview branches ─────────────────────────────────────────────────────────

async def test_overview_error_rate_when_zero_total(client):
    """Sem requests, taxa de erro deve ser 0.0 (branch do `if total else 0.0`)."""
    response = await client.get("/metrics/overview")
    data = response.json()
    assert data["error_rate_4xx_pct"] == 0.0
    assert data["error_rate_5xx_pct"] == 0.0


async def test_overview_error_rates_when_total_nonzero(client):
    """Com requests, taxa de erro deve ser calculada (branch `total > 0`)."""
    for _ in range(5):
        await client.post("/logs", json={**SAMPLE_LOG, "status_code": 200})
    await client.post("/logs", json={**SAMPLE_LOG, "status_code": 500})

    data = (await client.get("/metrics/overview")).json()
    assert data["error_rate_5xx_pct"] > 0.0
    assert data["error_rate_4xx_pct"] == 0.0


# ─── response-times com dados (branches zrange) ──────────────────────────────

async def test_response_times_returns_nonzero_with_single_entry(client):
    """Com um único log, percentis devem ser iguais ao tempo ingerido."""
    await client.post("/logs", json={**SAMPLE_LOG, "time_response": 123.0})
    data = (await client.get("/metrics/response-times")).json()
    assert data["sample_count"] == 1
    assert data["p50_ms"] == 123.0


# ─── rps — loop body (bucket presente) ───────────────────────────────────────

async def test_rps_loop_fills_bucket_correctly(client):
    """GET /metrics/rps deve preencher bucket com valor correto."""
    for _ in range(3):
        await client.post("/logs", json=SAMPLE_LOG)

    data = (await client.get("/metrics/rps")).json()
    # O bucket do minuto atual deve ter 3 requests
    assert sum(data["buckets"].values()) == 3
