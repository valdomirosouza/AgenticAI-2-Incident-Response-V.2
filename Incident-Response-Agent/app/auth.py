import hmac as _hmac
import logging
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from app.config import settings
from app.key_manager import has_any_keys, is_valid

logger = logging.getLogger(__name__)

_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_prometheus_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(key: str | None = Security(_header)) -> None:
    # Lê settings.api_key em cada chamada para suportar patches em testes
    if not has_any_keys(settings.api_key):
        return  # auth desabilitada (API_KEY não configurada)
    if not key or not is_valid(key, settings.api_key):
        logger.warning("Auth failure", extra={"reason": "invalid_or_missing_api_key"})
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def require_prometheus_key(key: str | None = Security(_prometheus_header)) -> None:
    """Protege GET /prometheus/metrics (A05 — bypass em development)."""
    if not settings.prometheus_api_key:
        return  # development: sem autenticação
    if not key or not _hmac.compare_digest(key.encode(), settings.prometheus_api_key.encode()):
        logger.warning("Prometheus auth failure", extra={"reason": "invalid_or_missing_key"})
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


async def require_admin_key(key: str | None = Security(_header)) -> None:
    """Proteção para /admin/* — requer ADMIN_KEY separada da API_KEY."""
    if not settings.admin_key:
        raise HTTPException(status_code=503, detail="Admin operations not configured")
    if not key or not _hmac.compare_digest(key.encode(), settings.admin_key.encode()):
        logger.warning("Admin auth failure", extra={"reason": "invalid_admin_key"})
        raise HTTPException(status_code=401, detail="Invalid admin key")
