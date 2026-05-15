from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _get_api_key_or_ip(request: Request) -> str:
    """Rate limit granular por API Key ou fallback para IP (SDD §7.3.5)."""
    return request.headers.get("X-API-Key") or get_remote_address(request)


limiter = Limiter(key_func=_get_api_key_or_ip)
