"""
E2E tests — CUJ-E2E-01: Log-Ingestion pipeline com Redis real.

Spin up um container Redis via testcontainers, injeta logs via POST /logs/ingest,
e verifica que os contadores aparecem em GET /metrics/overview e /metrics/response-times.

Requer Docker rodando localmente. Pulados automaticamente se Docker não estiver disponível.
"""

import subprocess
import pytest
from testcontainers.redis import RedisContainer
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.ingestion import get_redis, init_redis, close_redis


def _docker_available() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=5).returncode == 0
    except Exception:
        return False


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not _docker_available(), reason="Docker not available"),
]

SAMPLE_LOG = {
    "frontend": "http-in",
    "backend": "web-backend",
    "status_code": 200,
    "time_response": 42.5,
    "bytes_read": 1024,
    "request_method": "GET",
    "request_path": "/api/v1/health",
}

ERROR_LOG = {
    "frontend": "http-in",
    "backend": "web-backend",
    "status_code": 500,
    "time_response": 850.0,
    "bytes_read": 256,
    "request_method": "POST",
    "request_path": "/api/v1/data",
}


@pytest.fixture(scope="module")
def redis_container():
    with RedisContainer() as r:
        yield r


@pytest.fixture
async def real_redis(redis_container):
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    url = f"redis://{host}:{port}"
    await init_redis(url)
    r = await get_redis()
    await r.flushall()
    yield r
    await close_redis()


@pytest.fixture
async def client(real_redis):
    app.dependency_overrides[get_redis] = lambda: real_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _ingest(client: AsyncClient, log: dict) -> None:
    resp = await client.post("/logs", json=log)
    assert resp.status_code == 202


# ── CUJ-E2E-01a: ingestão incrementa contador requests_total ─────────────────

async def test_ingest_increments_total(client):
    await _ingest(client, SAMPLE_LOG)
    await _ingest(client, SAMPLE_LOG)

    resp = await client.get("/metrics/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["requests_total"] == 2
    assert data["errors_5xx"] == 0
    assert data["error_rate_5xx_pct"] == 0.0


# ── CUJ-E2E-01b: log 5xx é contado como erro ─────────────────────────────────

async def test_error_log_counted(client):
    await _ingest(client, SAMPLE_LOG)
    await _ingest(client, ERROR_LOG)

    resp = await client.get("/metrics/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["requests_total"] == 2
    assert data["errors_5xx"] == 1
    assert data["error_rate_5xx_pct"] == 50.0


# ── CUJ-E2E-01c: response-times refletem o tempo do log ingerido ─────────────

async def test_response_times_reflect_ingested_log(client):
    await _ingest(client, SAMPLE_LOG)  # time_response=42.5 ms

    resp = await client.get("/metrics/response-times")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sample_count"] == 1
    # Com 1 sample, p50/p95/p99 apontam para o único elemento
    assert data["p50_ms"] == pytest.approx(42.5, abs=0.1)


# ── CUJ-E2E-01d: health endpoint retorna 200 ─────────────────────────────────

async def test_health_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
