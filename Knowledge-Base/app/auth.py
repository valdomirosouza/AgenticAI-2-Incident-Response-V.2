import hmac
import logging
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.config import settings

logger = logging.getLogger(__name__)

_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(key: str | None = Security(_header)) -> None:
    if not settings.api_key:
        return
    if not key or not hmac.compare_digest(key.encode(), settings.api_key.encode()):
        logger.warning("Auth failure on KB endpoint")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
