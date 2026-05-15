import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


async def search_kb(query: str, limit: int = 3) -> list[dict]:
    """
    Busca incidentes similares na Knowledge Base.
    Retorna [] em qualquer erro — degradação graciosa (SDD §2.5 / CUJ-03).
    """
    try:
        headers: dict[str, str] = {}
        if settings.kb_api_key:
            headers["X-API-Key"] = settings.kb_api_key
        try:
            from opentelemetry.propagate import inject
            inject(headers)
        except Exception:
            pass

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.kb_api_url}/kb/search",
                json={"query": query, "limit": limit},
                headers=headers,
            )
            response.raise_for_status()
            return response.json().get("results", [])

    except Exception as exc:
        logger.warning("KB search failed — degrading gracefully: %s", exc)
        return []
