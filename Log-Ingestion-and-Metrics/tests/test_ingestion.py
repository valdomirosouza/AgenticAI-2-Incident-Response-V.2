"""
Testes TDD — CUJ-01: Ingestão de Logs HAProxy.
Ciclo RED → GREEN → REFACTOR (SDD §4.3).
"""

import pytest
from datetime import datetime, timezone
from tests.conftest import SAMPLE_LOG


pytestmark = pytest.mark.asyncio


async def test_health_returns_200(client):
    """[CUJ-08] GET /health deve retornar 200 com status healthy."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


async def test_ingest_returns_202(client):
    """[CUJ-01] POST /logs deve retornar 202 Accepted."""
    response = await client.post("/logs", json=SAMPLE_LOG)
    assert response.status_code == 202


async def test_ingest_increments_total_counter(client, fake_redis):
    """[CUJ-01] metrics:requests:total deve ser incrementado."""
    await client.post("/logs", json=SAMPLE_LOG)
    total = await fake_redis.get("metrics:requests:total")
    assert int(total) == 1


async def test_ingest_increments_status_counter(client, fake_redis):
    """[CUJ-01] Contador por status HTTP deve ser incrementado."""
    await client.post("/logs", json=SAMPLE_LOG)
    count = await fake_redis.get("metrics:status:200")
    assert int(count) == 1


async def test_ingest_increments_backend_counter(client, fake_redis):
    """[CUJ-01] Contador por backend deve ser incrementado."""
    await client.post("/logs", json=SAMPLE_LOG)
    count = await fake_redis.get("metrics:backend:web-backend")
    assert int(count) == 1


async def test_ingest_stores_response_time_in_sorted_set(client, fake_redis):
    """[CUJ-01] Tempo de resposta deve ser armazenado no sorted set."""
    await client.post("/logs", json=SAMPLE_LOG)
    count = await fake_redis.zcard("metrics:response_times")
    assert count == 1


async def test_ingest_increments_4xx_error_counter(client, fake_redis):
    """[CUJ-01] Logs 4xx devem incrementar o contador de erros 4xx."""
    log_4xx = {**SAMPLE_LOG, "status_code": 404}
    await client.post("/logs", json=log_4xx)
    errors = await fake_redis.get("metrics:errors:4xx")
    assert int(errors) == 1


async def test_ingest_increments_5xx_error_counter(client, fake_redis):
    """[CUJ-01] Logs 5xx devem incrementar o contador de erros 5xx."""
    log_5xx = {**SAMPLE_LOG, "status_code": 503}
    await client.post("/logs", json=log_5xx)
    errors = await fake_redis.get("metrics:errors:5xx")
    assert int(errors) == 1


async def test_ingest_2xx_does_not_increment_error_counters(client, fake_redis):
    """[CUJ-01] Logs 2xx não devem incrementar contadores de erro."""
    await client.post("/logs", json=SAMPLE_LOG)
    errors_4xx = await fake_redis.get("metrics:errors:4xx")
    errors_5xx = await fake_redis.get("metrics:errors:5xx")
    assert errors_4xx is None
    assert errors_5xx is None


async def test_ingest_rps_bucket_incremented(client, fake_redis):
    """[CUJ-01] Bucket de RPS do minuto atual deve ser incrementado."""
    minute_key = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    await client.post("/logs", json=SAMPLE_LOG)
    rps = await fake_redis.get(f"metrics:rps:{minute_key}")
    assert int(rps) == 1


async def test_ingest_rejects_negative_response_time(client):
    """[CUJ-01] Tempo de resposta negativo deve ser rejeitado com 422."""
    log = {**SAMPLE_LOG, "time_response": -10}
    response = await client.post("/logs", json=log)
    assert response.status_code == 422


async def test_ingest_rejects_invalid_status_code(client):
    """[CUJ-01] Status code fora de 100-599 deve retornar 422."""
    log = {**SAMPLE_LOG, "status_code": 999}
    response = await client.post("/logs", json=log)
    assert response.status_code == 422


async def test_ingest_rejects_empty_backend(client):
    """[CUJ-01] Backend vazio deve retornar 422."""
    log = {**SAMPLE_LOG, "backend": ""}
    response = await client.post("/logs", json=log)
    assert response.status_code == 422


async def test_ingest_multiple_logs_accumulate_counters(client, fake_redis):
    """[CUJ-01] Múltiplos logs devem acumular contadores corretamente."""
    for _ in range(5):
        await client.post("/logs", json=SAMPLE_LOG)
    total = await fake_redis.get("metrics:requests:total")
    assert int(total) == 5
