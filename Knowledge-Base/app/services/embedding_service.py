import logging
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    logger.info("Loading embedding model: %s", settings.embedding_model)
    return SentenceTransformer(settings.embedding_model)


def encode(text: str) -> list[float]:
    model = _load_model()
    return model.encode(text, normalize_embeddings=True).tolist()
