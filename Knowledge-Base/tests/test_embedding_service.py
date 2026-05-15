"""Testes para embedding_service com SentenceTransformer mockado via sys.modules."""

from tests.conftest import FAKE_VECTOR


def test_encode_returns_list():
    from app.services.embedding_service import encode
    result = encode("Redis memory saturation detected.")
    assert isinstance(result, list)


def test_encode_returns_384_dimensions():
    from app.services.embedding_service import encode
    result = encode("any text")
    assert len(result) == 384


def test_encode_returns_fake_vector():
    from app.services.embedding_service import encode
    result = encode("any text")
    assert result == FAKE_VECTOR


def test_load_model_cached(monkeypatch):
    """_load_model deve ser chamado apenas uma vez por causa do lru_cache."""
    from app.services import embedding_service
    call_count = 0
    original = embedding_service._load_model.__wrapped__

    def counting_load():
        nonlocal call_count
        call_count += 1
        return original()

    monkeypatch.setattr(embedding_service, "_load_model", embedding_service._load_model)
    embedding_service.encode("first call")
    embedding_service.encode("second call")
    # O modelo só é carregado uma vez — verificamos via cache_info
    info = embedding_service._load_model.cache_info()
    assert info.misses <= 1
