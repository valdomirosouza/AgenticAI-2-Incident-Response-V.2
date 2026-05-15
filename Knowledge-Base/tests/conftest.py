"""
Fixtures globais para o Knowledge-Base.
sentence_transformers é stubbed em sys.modules antes de qualquer import da app
para evitar dependência do modelo de 100 MB nos testes.
"""

import sys
from unittest.mock import MagicMock

# ── Stub sentence_transformers antes de qualquer import da app ────────────────
_st_stub = MagicMock()
_FAKE_VECTOR = [float(i % 10) / 10 for i in range(384)]
_st_stub.SentenceTransformer.return_value.encode.return_value.tolist.return_value = _FAKE_VECTOR
sys.modules.setdefault("sentence_transformers", _st_stub)

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app

FAKE_VECTOR = _FAKE_VECTOR
SAMPLE_CHUNK = {
    "content": "Redis OOM caused by unbounded key growth without TTL policy.",
    "incident_id": "INC-001",
    "metadata": {"source": "post-mortem"},
}


@pytest.fixture(autouse=True)
def reset_qdrant_client():
    """Zera o singleton do cliente Qdrant entre testes."""
    from app.services import qdrant_service
    qdrant_service._client = None
    yield
    qdrant_service._client = None


@pytest.fixture(autouse=True)
def clear_model_cache():
    """Limpa o lru_cache do modelo de embedding entre testes."""
    from app.services import embedding_service
    embedding_service._load_model.cache_clear()
    yield


@pytest.fixture
async def client():
    with patch("app.services.qdrant_service.ensure_collection", new=AsyncMock()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


@pytest.fixture
async def client_with_auth():
    with (
        patch("app.config.settings.api_key", "test-secret"),
        patch("app.services.qdrant_service.ensure_collection", new=AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
