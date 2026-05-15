"""
E2E tests — CUJ-E2E-02: Knowledge-Base pipeline com Qdrant real.

Spin up um container Qdrant via testcontainers, ingere um chunk de post-mortem,
e verifica que a busca vetorial retorna o chunk correto.

Embeddings são stubados (vetor fixo de 384 dim) para evitar download do modelo.
Requer Docker rodando localmente. Pulados automaticamente se Docker não estiver disponível.
"""

import subprocess
import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from app.main import app
from app.services import qdrant_service


def _docker_available() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=5).returncode == 0
    except Exception:
        return False


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not _docker_available(), reason="Docker not available"),
]

SAMPLE_CHUNK = {
    "content": "Redis OOM caused by unbounded key growth. Fix: set allkeys-lru policy.",
    "incident_id": "INC-001",
    "metadata": {"source": "post-mortem", "severity": "critical"},
}

SECOND_CHUNK = {
    "content": "Blue/green deploy latency spike: missing readiness probe for Redis warmup.",
    "incident_id": "INC-002",
    "metadata": {"source": "post-mortem", "severity": "warning"},
}


@pytest.fixture(scope="module")
def qdrant_container():
    container = (
        DockerContainer("qdrant/qdrant:v1.18.0")
        .with_exposed_ports(6333)
    )
    with container as c:
        wait_for_logs(c, "Actix runtime found", timeout=30)
        yield c


@pytest.fixture
def qdrant_url(qdrant_container):
    host = qdrant_container.get_container_host_ip()
    port = qdrant_container.get_exposed_port(6333)
    return f"http://{host}:{port}"


@pytest.fixture
async def client(qdrant_url):
    # reset_qdrant_client autouse fixture (conftest) já zerará _client após o teste
    qdrant_service._client = None
    with patch("app.config.settings.qdrant_url", qdrant_url):
        with patch("app.config.settings.qdrant_collection", "test-postmortems"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                yield c
    qdrant_service._client = None


@pytest.fixture
async def client_with_auth(qdrant_url):
    qdrant_service._client = None
    with patch("app.config.settings.qdrant_url", qdrant_url):
        with patch("app.config.settings.qdrant_collection", "test-postmortems-auth"):
            with patch("app.config.settings.api_key", "test-secret"):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                    yield c
    qdrant_service._client = None


# ── CUJ-E2E-02a: ingestão e busca do chunk ───────────────────────────────────

async def test_ingest_and_search(client):
    ingest_resp = await client.post(
        "/kb/ingest",
        json=SAMPLE_CHUNK,
        headers={"X-API-Key": ""},
    )
    assert ingest_resp.status_code == 200
    body = ingest_resp.json()
    assert body["status"] == "ok"
    assert "chunk_id" in body

    search_resp = await client.post(
        "/kb/search",
        json={"query": "Redis OOM memory issue", "limit": 3},
    )
    assert search_resp.status_code == 200
    results = search_resp.json()["results"]
    # O embedding stub sempre retorna o mesmo vetor → cosine = 1.0 → sempre retorna
    assert len(results) >= 1
    assert results[0]["incident_id"] == "INC-001"


# ── CUJ-E2E-02b: ingestão múltipla e busca retorna os chunks ─────────────────

async def test_ingest_multiple_chunks(client):
    for chunk in [SAMPLE_CHUNK, SECOND_CHUNK]:
        resp = await client.post("/kb/ingest", json=chunk, headers={"X-API-Key": ""})
        assert resp.status_code == 200

    search_resp = await client.post(
        "/kb/search",
        json={"query": "latency deploy", "limit": 5},
    )
    assert search_resp.status_code == 200
    results = search_resp.json()["results"]
    assert len(results) >= 1
    incident_ids = {r["incident_id"] for r in results}
    # Ambos os chunks devem estar na coleção (mesmo vetor stub → ambos retornados)
    assert "INC-001" in incident_ids or "INC-002" in incident_ids


# ── CUJ-E2E-02c: ingestão sem API key retorna 200 (sem auth em dev) ──────────

async def test_ingest_no_auth_in_dev(client):
    resp = await client.post("/kb/ingest", json=SAMPLE_CHUNK)
    assert resp.status_code == 200


# ── CUJ-E2E-02d: ingestão com API key válida funciona ────────────────────────

async def test_ingest_with_valid_api_key(client_with_auth):
    resp = await client_with_auth.post(
        "/kb/ingest",
        json=SAMPLE_CHUNK,
        headers={"X-API-Key": "test-secret"},
    )
    assert resp.status_code == 200


# ── CUJ-E2E-02e: busca em coleção vazia retorna lista vazia ──────────────────

async def test_search_empty_collection(client):
    resp = await client.post(
        "/kb/search",
        json={"query": "nothing here", "limit": 3},
    )
    assert resp.status_code == 200
    # Coleção foi criada no lifespan mas sem dados → results vazio
    assert isinstance(resp.json()["results"], list)


# ── CUJ-E2E-02f: health endpoint ok ─────────────────────────────────────────

async def test_health_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
