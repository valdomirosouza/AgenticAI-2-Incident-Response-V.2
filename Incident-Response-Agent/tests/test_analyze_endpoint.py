"""
Testes HTTP para os endpoints /analyze e /health.
run_analysis é sempre mockado — sem chamadas à Anthropic API ou serviços externos.
"""

import pytest
from tests.conftest import OK_REPORT, CRITICAL_REPORT

pytestmark = pytest.mark.asyncio


# ─── /health ─────────────────────────────────────────────────────────────────

async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


async def test_health_has_security_headers(client):
    response = await client.get("/health")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"


# ─── /analyze — sem autenticação configurada ─────────────────────────────────

async def test_analyze_returns_200_no_auth_configured(client, mock_run_analysis_ok):
    response = await client.post("/analyze")
    assert response.status_code == 200


async def test_analyze_returns_ok_report_fields(client, mock_run_analysis_ok):
    response = await client.post("/analyze")
    data = response.json()
    assert data["overall_severity"] == "ok"
    assert data["title"] == "System Healthy"
    assert "findings" in data
    assert "recommendations" in data


async def test_analyze_returns_critical_report(client, mock_run_analysis_critical):
    response = await client.post("/analyze")
    data = response.json()
    assert data["overall_severity"] == "critical"
    assert data["root_causes"] == ["Redis configured with noeviction policy"]
    assert data["triggers"] == ["Traffic spike 4x"]
    assert "INC-001" in data["similar_incidents"]


async def test_analyze_response_has_timestamp(client, mock_run_analysis_ok):
    response = await client.post("/analyze")
    data = response.json()
    assert "timestamp" in data


async def test_analyze_response_has_escalation_flag(client, mock_run_analysis_ok):
    response = await client.post("/analyze")
    data = response.json()
    assert "escalation_recommended" in data


# ─── /analyze — com autenticação configurada ─────────────────────────────────

async def test_analyze_missing_api_key_returns_401(client_with_auth, mock_run_analysis_ok):
    response = await client_with_auth.post("/analyze")
    assert response.status_code == 401


async def test_analyze_wrong_api_key_returns_401(client_with_auth, mock_run_analysis_ok):
    response = await client_with_auth.post(
        "/analyze", headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401


async def test_analyze_valid_api_key_returns_200(client_with_auth, mock_run_analysis_ok):
    response = await client_with_auth.post(
        "/analyze", headers={"X-API-Key": "test-secret-key"}
    )
    assert response.status_code == 200


# ─── Security headers ─────────────────────────────────────────────────────────

async def test_analyze_response_has_security_headers(client, mock_run_analysis_ok):
    response = await client.post("/analyze")
    assert "x-content-type-options" in response.headers
    assert "x-frame-options" in response.headers
    assert "strict-transport-security" in response.headers
    assert "content-security-policy" in response.headers


async def test_analyze_request_id_propagated(client, mock_run_analysis_ok):
    response = await client.post("/analyze", headers={"X-Request-ID": "test-req-123"})
    assert response.headers.get("x-request-id") == "test-req-123"
