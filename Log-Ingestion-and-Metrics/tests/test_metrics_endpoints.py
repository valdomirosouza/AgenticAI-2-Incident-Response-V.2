"""
Testes TDD — CUJ-05: Consulta de métricas (response times, overview, RPS, saturação).
"""

import pytest
from tests.conftest import SAMPLE_LOG

pytestmark = pytest.mark.asyncio


async def test_overview_returns_all_fields(client):
    """[CUJ-05] GET /metrics/overview deve retornar todos os campos obrigatórios."""
    response = await client.get("/metrics/overview")
    assert response.status_code == 200
    data = response.json()
    assert all(k in data for k in ["requests_total", "errors_4xx", "errors_5xx", "error_rate_4xx_pct", "error_rate_5xx_pct"])


async def test_overview_starts_at_zero(client):
    """[CUJ-05] Sem logs ingeridos, todos os contadores devem ser zero."""
    response = await client.get("/metrics/overview")
    data = response.json()
    assert data["requests_total"] == 0
    assert data["errors_4xx"] == 0
    assert data["errors_5xx"] == 0


async def test_overview_reflects_ingested_logs(client):
    """[CUJ-05] Overview deve refletir os logs ingeridos."""
    await client.post("/logs", json={**SAMPLE_LOG, "status_code": 200})
    await client.post("/logs", json={**SAMPLE_LOG, "status_code": 500})
    data = (await client.get("/metrics/overview")).json()
    assert data["requests_total"] == 2
    assert data["errors_5xx"] == 1


async def test_overview_calculates_error_rate_pct(client):
    """[CUJ-05] Taxa de erro deve ser calculada em percentual."""
    for _ in range(9):
        await client.post("/logs", json={**SAMPLE_LOG, "status_code": 200})
    await client.post("/logs", json={**SAMPLE_LOG, "status_code": 500})
    data = (await client.get("/metrics/overview")).json()
    assert data["error_rate_5xx_pct"] == 10.0


async def test_response_times_empty_when_no_data(client):
    """[CUJ-05] GET /metrics/response-times sem dados deve retornar zeros."""
    response = await client.get("/metrics/response-times")
    assert response.status_code == 200
    data = response.json()
    assert data["sample_count"] == 0
    assert data["p50_ms"] == 0.0


async def test_response_times_calculates_percentiles(client):
    """[CUJ-05] Percentis devem ser calculados corretamente com múltiplos logs."""
    latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    for ms in latencies:
        await client.post("/logs", json={**SAMPLE_LOG, "time_response": float(ms)})

    data = (await client.get("/metrics/response-times")).json()
    assert data["sample_count"] == 10
    assert data["p50_ms"] > 0
    assert data["p95_ms"] >= data["p50_ms"]
    assert data["p99_ms"] >= data["p95_ms"]


async def test_saturation_returns_redis_info(client):
    """[CUJ-05] GET /metrics/saturation deve retornar informações do Redis."""
    response = await client.get("/metrics/saturation")
    assert response.status_code == 200
    data = response.json()
    assert "response_time_samples" in data
    assert "redis" in data


async def test_rps_returns_buckets(client):
    """[CUJ-05] GET /metrics/rps deve retornar buckets por minuto."""
    await client.post("/logs", json=SAMPLE_LOG)
    response = await client.get("/metrics/rps")
    assert response.status_code == 200
    data = response.json()
    assert "buckets" in data
    assert "current_rps" in data
    assert len(data["buckets"]) >= 1


async def test_security_headers_present_on_health(client):
    """[DAST] GET /health deve retornar headers de segurança obrigatórios."""
    response = await client.get("/health")
    assert "x-content-type-options" in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "x-frame-options" in response.headers
    assert "referrer-policy" in response.headers
