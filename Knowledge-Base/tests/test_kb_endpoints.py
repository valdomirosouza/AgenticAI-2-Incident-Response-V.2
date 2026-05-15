"""
Testes dos endpoints /kb/search e /kb/ingest, incluindo autenticação.
Qdrant é mockado em cada teste para evitar dependência de serviço externo.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.conftest import SAMPLE_CHUNK, FAKE_VECTOR

pytestmark = pytest.mark.asyncio

SEARCH_RESULT = {
    "id": "abc-123",
    "score": 0.91,
    "content": "Redis OOM caused by missing TTL policy.",
    "incident_id": "INC-001",
}


# ─── /kb/search ──────────────────────────────────────────────────────────────

async def test_search_returns_results(client):
    with patch("app.services.qdrant_service.search", new=AsyncMock(return_value=[SEARCH_RESULT])):
        response = await client.post("/kb/search", json={"query": "Redis memory"})

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["results"][0]["score"] == 0.91


async def test_search_empty_results(client):
    with patch("app.services.qdrant_service.search", new=AsyncMock(return_value=[])):
        response = await client.post("/kb/search", json={"query": "unknown topic"})

    assert response.status_code == 200
    assert response.json()["count"] == 0


async def test_search_respects_limit(client):
    with patch("app.services.qdrant_service.search", new=AsyncMock(return_value=[])) as mock_search:
        await client.post("/kb/search", json={"query": "latency spike", "limit": 5})
        mock_search.assert_called_once_with(FAKE_VECTOR, limit=5)


async def test_search_default_limit_is_3(client):
    with patch("app.services.qdrant_service.search", new=AsyncMock(return_value=[])) as mock_search:
        await client.post("/kb/search", json={"query": "latency"})
        mock_search.assert_called_once_with(FAKE_VECTOR, limit=3)


async def test_search_empty_query_returns_422(client):
    response = await client.post("/kb/search", json={"query": ""})
    assert response.status_code == 422


async def test_search_query_too_long_returns_422(client):
    response = await client.post("/kb/search", json={"query": "x" * 1001})
    assert response.status_code == 422


async def test_search_limit_too_high_returns_422(client):
    response = await client.post("/kb/search", json={"query": "redis", "limit": 11})
    assert response.status_code == 422


async def test_search_limit_zero_returns_422(client):
    response = await client.post("/kb/search", json={"query": "redis", "limit": 0})
    assert response.status_code == 422


# ─── /kb/ingest — sem autenticação configurada ────────────────────────────────

async def test_ingest_without_auth_config_succeeds(client):
    """Quando api_key não está configurado, ingest passa sem header."""
    with patch("app.services.qdrant_service.upsert", new=AsyncMock()):
        response = await client.post("/kb/ingest", json=SAMPLE_CHUNK)

    assert response.status_code == 201
    data = response.json()
    assert "chunk_id" in data
    assert isinstance(data["blameful_warnings"], list)


async def test_ingest_returns_chunk_id(client):
    with patch("app.services.qdrant_service.upsert", new=AsyncMock()):
        response = await client.post("/kb/ingest", json=SAMPLE_CHUNK)

    chunk_id = response.json()["chunk_id"]
    assert len(chunk_id) == 36  # UUID4 com hifens


async def test_ingest_calls_upsert_with_correct_payload(client):
    with patch("app.services.qdrant_service.upsert", new=AsyncMock()) as mock_upsert:
        await client.post("/kb/ingest", json=SAMPLE_CHUNK)

    call_kwargs = mock_upsert.call_args.kwargs
    assert call_kwargs["payload"]["content"] == SAMPLE_CHUNK["content"]
    assert call_kwargs["payload"]["incident_id"] == SAMPLE_CHUNK["incident_id"]
    assert call_kwargs["payload"]["source"] == "post-mortem"


async def test_ingest_chunk_too_large_returns_422(client):
    oversized = {**SAMPLE_CHUNK, "content": "x" * 5001}
    response = await client.post("/kb/ingest", json=oversized)
    assert response.status_code == 422
    assert "Content too large" in response.json()["detail"]


async def test_ingest_detects_blameful_language(client):
    blameful = {**SAMPLE_CHUNK, "content": "This incident was caused by human error and negligence."}
    with patch("app.services.qdrant_service.upsert", new=AsyncMock()):
        response = await client.post("/kb/ingest", json=blameful)

    assert response.status_code == 201
    warnings = response.json()["blameful_warnings"]
    assert len(warnings) >= 1


async def test_ingest_clean_content_has_no_warnings(client):
    with patch("app.services.qdrant_service.upsert", new=AsyncMock()):
        response = await client.post("/kb/ingest", json=SAMPLE_CHUNK)

    assert response.json()["blameful_warnings"] == []


# ─── /kb/ingest — com autenticação configurada ────────────────────────────────

async def test_ingest_valid_api_key_succeeds(client_with_auth):
    with patch("app.services.qdrant_service.upsert", new=AsyncMock()):
        response = await client_with_auth.post(
            "/kb/ingest",
            json=SAMPLE_CHUNK,
            headers={"X-API-Key": "test-secret"},
        )
    assert response.status_code == 201


async def test_ingest_missing_api_key_returns_401(client_with_auth):
    response = await client_with_auth.post("/kb/ingest", json=SAMPLE_CHUNK)
    assert response.status_code == 401


async def test_ingest_wrong_api_key_returns_401(client_with_auth):
    response = await client_with_auth.post(
        "/kb/ingest",
        json=SAMPLE_CHUNK,
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


# ─── /health ─────────────────────────────────────────────────────────────────

async def test_health_returns_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
