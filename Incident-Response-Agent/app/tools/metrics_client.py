import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class MetricsClient:
    def __init__(self) -> None:
        self._base = settings.metrics_api_url

    async def _get(self, path: str) -> dict:
        headers: dict[str, str] = {}
        try:
            from opentelemetry.propagate import inject
            inject(headers)
        except Exception:
            pass

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self._base}{path}", headers=headers)
            response.raise_for_status()
            return response.json()

    async def get_overview(self) -> dict:
        return await self._get("/metrics/overview")

    async def get_response_times(self) -> dict:
        return await self._get("/metrics/response-times")

    async def get_saturation(self) -> dict:
        return await self._get("/metrics/saturation")

    async def get_rps(self) -> dict:
        return await self._get("/metrics/rps")

    async def get_backends(self) -> dict:
        return await self._get("/metrics/backends")
