import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.auth import require_api_key
from app.services import embedding_service, qdrant_service
from app.services.chunk_validator import validate_chunk_size, detect_blameful_language

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/kb")


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=3, ge=1, le=10)


class ChunkIngest(BaseModel):
    content: str = Field(min_length=1)
    incident_id: str = Field(min_length=1, max_length=50)
    metadata: dict = Field(default_factory=dict)


@router.post("/search")
async def search(body: SearchRequest):
    vector = embedding_service.encode(body.query)
    results = await qdrant_service.search(vector, limit=body.limit)
    return {"results": results, "count": len(results)}


@router.post("/ingest", dependencies=[Depends(require_api_key)], status_code=201)
async def ingest(body: ChunkIngest):
    try:
        validate_chunk_size(body.content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    warnings = detect_blameful_language(body.content)
    if warnings:
        logger.warning("Blameful language detected in chunk: %s", warnings)

    vector = embedding_service.encode(body.content)
    chunk_id = str(uuid.uuid4())
    await qdrant_service.upsert(
        chunk_id=chunk_id,
        vector=vector,
        payload={"content": body.content, "incident_id": body.incident_id, **body.metadata},
    )
    logger.info("Chunk ingested", extra={"chunk_id": chunk_id, "incident_id": body.incident_id})
    return {"chunk_id": chunk_id, "blameful_warnings": warnings}
