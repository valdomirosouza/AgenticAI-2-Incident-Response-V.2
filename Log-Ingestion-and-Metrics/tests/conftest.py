import pytest
import fakeredis.aioredis
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

from app.main import app
from app.ingestion import get_redis

SAMPLE_LOG = {
    "frontend": "http-in",
    "backend": "web-backend",
    "status_code": 200,
    "time_response": 42.5,
    "bytes_read": 1024,
    "request_method": "GET",
    "request_path": "/api/v1/health",
}


@pytest.fixture
async def fake_redis():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.flushall()
    await r.aclose()


@pytest.fixture
async def client(fake_redis):
    app.dependency_overrides[get_redis] = lambda: fake_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
