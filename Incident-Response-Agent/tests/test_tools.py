"""
Testes para tools/kb_client.py e tools/metrics_client.py.
httpx.AsyncClient é mockado em todos os testes — sem chamadas HTTP reais.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.tools.kb_client import search_kb
from app.tools.metrics_client import MetricsClient

pytestmark = pytest.mark.asyncio


# ─── helpers ──────────────────────────────────────────────────────────────────

def make_httpx_response(json_data: dict, status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=mock_resp)
        if status_code >= 400
        else None
    )
    return mock_resp


def mock_async_client(response: MagicMock):
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
    mock_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_ctx.post = AsyncMock(return_value=response)
    mock_ctx.get = AsyncMock(return_value=response)
    return mock_ctx


# ─── search_kb ────────────────────────────────────────────────────────────────

async def test_search_kb_returns_results():
    resp = make_httpx_response({"results": [{"id": "INC-001", "score": 0.92}]})
    with patch("app.tools.kb_client.httpx.AsyncClient", return_value=mock_async_client(resp)):
        results = await search_kb("Redis OOM")
    assert len(results) == 1
    assert results[0]["id"] == "INC-001"


async def test_search_kb_empty_results():
    resp = make_httpx_response({"results": []})
    with patch("app.tools.kb_client.httpx.AsyncClient", return_value=mock_async_client(resp)):
        results = await search_kb("unknown query")
    assert results == []


async def test_search_kb_degrades_gracefully_on_http_error():
    resp = make_httpx_response({}, status_code=500)
    with patch("app.tools.kb_client.httpx.AsyncClient", return_value=mock_async_client(resp)):
        results = await search_kb("anything")
    assert results == []


async def test_search_kb_degrades_gracefully_on_connection_error():
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(side_effect=httpx.ConnectError("refused"))
    with patch("app.tools.kb_client.httpx.AsyncClient", return_value=mock_ctx):
        results = await search_kb("anything")
    assert results == []


async def test_search_kb_adds_api_key_header_when_configured():
    resp = make_httpx_response({"results": []})
    mock_ctx = mock_async_client(resp)

    with (
        patch("app.tools.kb_client.httpx.AsyncClient", return_value=mock_ctx),
        patch("app.tools.kb_client.settings") as s,
    ):
        s.kb_api_url = "http://kb"
        s.kb_api_key = "my-secret"
        await search_kb("query")

    call_kwargs = mock_ctx.post.call_args.kwargs
    assert call_kwargs["headers"].get("X-API-Key") == "my-secret"


async def test_search_kb_no_api_key_header_when_not_configured():
    resp = make_httpx_response({"results": []})
    mock_ctx = mock_async_client(resp)

    with (
        patch("app.tools.kb_client.httpx.AsyncClient", return_value=mock_ctx),
        patch("app.tools.kb_client.settings") as s,
    ):
        s.kb_api_url = "http://kb"
        s.kb_api_key = ""
        await search_kb("query")

    call_kwargs = mock_ctx.post.call_args.kwargs
    assert "X-API-Key" not in call_kwargs.get("headers", {})


async def test_search_kb_respects_limit_param():
    resp = make_httpx_response({"results": []})
    mock_ctx = mock_async_client(resp)

    with (
        patch("app.tools.kb_client.httpx.AsyncClient", return_value=mock_ctx),
        patch("app.tools.kb_client.settings") as s,
    ):
        s.kb_api_url = "http://kb"
        s.kb_api_key = ""
        await search_kb("query", limit=5)

    call_kwargs = mock_ctx.post.call_args.kwargs
    assert call_kwargs["json"]["limit"] == 5


# ─── MetricsClient ────────────────────────────────────────────────────────────

async def test_metrics_client_get_overview():
    resp = make_httpx_response({"requests_total": 1000, "error_rate_5xx_pct": 0.5})
    mock_ctx = mock_async_client(resp)

    with patch("app.tools.metrics_client.httpx.AsyncClient", return_value=mock_ctx):
        client = MetricsClient()
        data = await client.get_overview()

    assert data["requests_total"] == 1000


async def test_metrics_client_get_response_times():
    resp = make_httpx_response({"p99_ms": 200.0, "p50_ms": 50.0})
    mock_ctx = mock_async_client(resp)

    with patch("app.tools.metrics_client.httpx.AsyncClient", return_value=mock_ctx):
        client = MetricsClient()
        data = await client.get_response_times()

    assert data["p99_ms"] == 200.0


async def test_metrics_client_get_saturation():
    resp = make_httpx_response({"redis": {"used_memory_bytes": 512_000}})
    mock_ctx = mock_async_client(resp)

    with patch("app.tools.metrics_client.httpx.AsyncClient", return_value=mock_ctx):
        client = MetricsClient()
        data = await client.get_saturation()

    assert "redis" in data


async def test_metrics_client_get_rps():
    resp = make_httpx_response({"current_rps": 1.5, "buckets": {}})
    mock_ctx = mock_async_client(resp)

    with patch("app.tools.metrics_client.httpx.AsyncClient", return_value=mock_ctx):
        client = MetricsClient()
        data = await client.get_rps()

    assert data["current_rps"] == 1.5


async def test_metrics_client_get_backends():
    resp = make_httpx_response({"backends": {"web": 500}})
    mock_ctx = mock_async_client(resp)

    with patch("app.tools.metrics_client.httpx.AsyncClient", return_value=mock_ctx):
        client = MetricsClient()
        data = await client.get_backends()

    assert data["backends"]["web"] == 500


async def test_metrics_client_raises_on_http_error():
    resp = make_httpx_response({}, status_code=503)
    mock_ctx = mock_async_client(resp)

    with patch("app.tools.metrics_client.httpx.AsyncClient", return_value=mock_ctx):
        client = MetricsClient()
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_overview()


async def test_metrics_client_uses_correct_base_url():
    resp = make_httpx_response({})
    mock_ctx = mock_async_client(resp)

    with (
        patch("app.tools.metrics_client.httpx.AsyncClient", return_value=mock_ctx),
        patch("app.tools.metrics_client.settings") as s,
    ):
        s.metrics_api_url = "http://metrics:8000"
        client = MetricsClient()
        await client.get_overview()

    call_args = mock_ctx.get.call_args
    url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", "")
    assert "http://metrics:8000" in url
