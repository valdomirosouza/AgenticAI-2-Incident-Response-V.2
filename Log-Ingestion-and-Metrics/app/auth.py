import hmac
import logging
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from app.config import settings

logger = logging.getLogger(__name__)

_prometheus_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_prometheus_key(key: str | None = Security(_prometheus_header)) -> None:
    """Protege GET /prometheus/metrics — bypass se PROMETHEUS_API_KEY não configurado (A05)."""
    if not settings.prometheus_api_key:
        return  # development: sem autenticação
    if not key or not hmac.compare_digest(key.encode(), settings.prometheus_api_key.encode()):
        logger.warning("Prometheus auth failure", extra={"reason": "invalid_or_missing_key"})
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
