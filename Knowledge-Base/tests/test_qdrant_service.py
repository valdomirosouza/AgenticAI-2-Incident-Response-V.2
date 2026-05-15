"""Testes para qdrant_service com AsyncQdrantClient mockado."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tests.conftest import FAKE_VECTOR

pytestmark = pytest.mark.asyncio


# ─── get_client ───────────────────────────────────────────────────────────────

async def test_get_client_creates_on_first_call():
    from app.services import qdrant_service

    mock_client = AsyncMock()
    with patch("app.services.qdrant_service.AsyncQdrantClient", return_value=mock_client) as mock_cls:
        client = await qdrant_service.get_client()
        assert client is mock_client
        mock_cls.assert_called_once()


async def test_get_client_returns_cached_on_second_call():
    from app.services import qdrant_service

    mock_client = AsyncMock()
    with patch("app.services.qdrant_service.AsyncQdrantClient", return_value=mock_client):
        first = await qdrant_service.get_client()
        second = await qdrant_service.get_client()
        assert first is second


# ─── ensure_collection ────────────────────────────────────────────────────────

async def test_ensure_collection_skips_when_exists():
    from app.services import qdrant_service

    mock_client = AsyncMock()
    mock_client.collection_exists.return_value = True
    with patch("app.services.qdrant_service.AsyncQdrantClient", return_value=mock_client):
        await qdrant_service.ensure_collection()
        mock_client.create_collection.assert_not_called()


async def test_ensure_collection_creates_when_missing():
    from app.services import qdrant_service

    mock_client = AsyncMock()
    mock_client.collection_exists.return_value = False
    with patch("app.services.qdrant_service.AsyncQdrantClient", return_value=mock_client):
        await qdrant_service.ensure_collection()
        mock_client.create_collection.assert_called_once()


# ─── upsert ───────────────────────────────────────────────────────────────────

async def test_upsert_calls_client_upsert():
    from app.services import qdrant_service

    mock_client = AsyncMock()
    with patch("app.services.qdrant_service.AsyncQdrantClient", return_value=mock_client):
        await qdrant_service.upsert(
            chunk_id="abc-123",
            vector=FAKE_VECTOR,
            payload={"content": "test", "incident_id": "INC-001"},
        )
        mock_client.upsert.assert_called_once()


async def test_upsert_passes_correct_collection():
    from app.services import qdrant_service
    from app.config import settings

    mock_client = AsyncMock()
    with patch("app.services.qdrant_service.AsyncQdrantClient", return_value=mock_client):
        await qdrant_service.upsert("id", FAKE_VECTOR, {})
        call_kwargs = mock_client.upsert.call_args.kwargs
        assert call_kwargs["collection_name"] == settings.qdrant_collection


# ─── search ───────────────────────────────────────────────────────────────────

async def test_search_returns_mapped_results():
    from app.services import qdrant_service

    mock_hit = MagicMock()
    mock_hit.id = "abc-123"
    mock_hit.score = 0.92
    mock_hit.payload = {"content": "Redis OOM", "incident_id": "INC-001"}

    mock_client = AsyncMock()
    mock_client.search.return_value = [mock_hit]
    with patch("app.services.qdrant_service.AsyncQdrantClient", return_value=mock_client):
        results = await qdrant_service.search(FAKE_VECTOR, limit=3)

    assert len(results) == 1
    assert results[0]["id"] == "abc-123"
    assert results[0]["score"] == 0.92
    assert results[0]["content"] == "Redis OOM"
    assert results[0]["incident_id"] == "INC-001"


async def test_search_returns_empty_list_when_no_results():
    from app.services import qdrant_service

    mock_client = AsyncMock()
    mock_client.search.return_value = []
    with patch("app.services.qdrant_service.AsyncQdrantClient", return_value=mock_client):
        results = await qdrant_service.search(FAKE_VECTOR)

    assert results == []


async def test_search_handles_none_payload():
    from app.services import qdrant_service

    mock_hit = MagicMock()
    mock_hit.id = "xyz"
    mock_hit.score = 0.75
    mock_hit.payload = None

    mock_client = AsyncMock()
    mock_client.search.return_value = [mock_hit]
    with patch("app.services.qdrant_service.AsyncQdrantClient", return_value=mock_client):
        results = await qdrant_service.search(FAKE_VECTOR)

    assert results[0]["content"] == ""
    assert results[0]["incident_id"] == ""


async def test_search_applies_score_threshold():
    from app.services import qdrant_service
    from app.config import settings

    mock_client = AsyncMock()
    mock_client.search.return_value = []
    with patch("app.services.qdrant_service.AsyncQdrantClient", return_value=mock_client):
        await qdrant_service.search(FAKE_VECTOR, limit=5)
        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["score_threshold"] == settings.min_similarity_score
