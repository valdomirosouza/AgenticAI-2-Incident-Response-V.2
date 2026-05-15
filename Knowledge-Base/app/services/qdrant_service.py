import logging
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter
from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncQdrantClient | None = None
VECTOR_SIZE = 384  # all-MiniLM-L6-v2


async def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
    return _client


async def ensure_collection() -> None:
    client = await get_client()
    exists = await client.collection_exists(settings.qdrant_collection)
    if not exists:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("Collection '%s' created", settings.qdrant_collection)


async def upsert(chunk_id: str, vector: list[float], payload: dict) -> None:
    client = await get_client()
    await client.upsert(
        collection_name=settings.qdrant_collection,
        points=[PointStruct(id=chunk_id, vector=vector, payload=payload)],
    )


async def search(vector: list[float], limit: int = 3) -> list[dict]:
    """Aplica score_threshold para rejeitar chunks irrelevantes (SDD §7.3.4)."""
    client = await get_client()
    results = await client.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector,
        limit=limit,
        score_threshold=settings.min_similarity_score,
        with_payload=True,
    )
    return [
        {
            "id": str(r.id),
            "score": r.score,
            "content": r.payload.get("content", "") if r.payload else "",
            "incident_id": r.payload.get("incident_id", "") if r.payload else "",
        }
        for r in results
    ]
