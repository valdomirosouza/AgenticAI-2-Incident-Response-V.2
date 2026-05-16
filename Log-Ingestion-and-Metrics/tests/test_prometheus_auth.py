"""Testes para proteção do endpoint GET /prometheus/metrics (OWASP A05 / SDD §5)."""

import pytest
from unittest.mock import patch


pytestmark = pytest.mark.asyncio


async def test_prometheus_open_when_no_key_configured(client):
    """Development: sem PROMETHEUS_API_KEY configurado, endpoint é acessível."""
    with patch("app.config.settings.prometheus_api_key", ""):
        resp = await client.get("/prometheus/metrics")
    assert resp.status_code == 200


async def test_prometheus_requires_key_when_configured(client):
    """Quando PROMETHEUS_API_KEY configurado, request sem header retorna 401."""
    with patch("app.config.settings.prometheus_api_key", "prom-secret"):
        resp = await client.get("/prometheus/metrics")
    assert resp.status_code == 401


async def test_prometheus_accepts_valid_key(client):
    """Request com X-API-Key correto retorna 200."""
    with patch("app.config.settings.prometheus_api_key", "prom-secret"):
        resp = await client.get("/prometheus/metrics", headers={"X-API-Key": "prom-secret"})
    assert resp.status_code == 200


async def test_prometheus_rejects_wrong_key(client):
    """Request com X-API-Key incorreto retorna 401."""
    with patch("app.config.settings.prometheus_api_key", "prom-secret"):
        resp = await client.get("/prometheus/metrics", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


def test_staging_requires_prometheus_key():
    """staging e production exigem PROMETHEUS_API_KEY (A05)."""
    from pydantic import ValidationError
    from app.config import Settings

    with pytest.raises(ValidationError, match="PROMETHEUS_API_KEY"):
        Settings(app_env="staging", prometheus_api_key="")
