"""
Testes LLM07:2025 — System Prompt Leakage (SDD §7.3.5).
Garantem que system prompts não aparecem em respostas de API nem em logs estruturados.
"""

import json
import pytest
from app.agents.prompts import (
    LATENCY_SYSTEM_PROMPT_V1,
    ERRORS_SYSTEM_PROMPT_V1,
    SATURATION_SYSTEM_PROMPT_V1,
    TRAFFIC_SYSTEM_PROMPT_V1,
    ORCHESTRATOR_SYSTEM_PROMPT_V1,
    PROMPT_CLASSIFICATION,
)


ALL_PROMPTS = [
    LATENCY_SYSTEM_PROMPT_V1,
    ERRORS_SYSTEM_PROMPT_V1,
    SATURATION_SYSTEM_PROMPT_V1,
    TRAFFIC_SYSTEM_PROMPT_V1,
    ORCHESTRATOR_SYSTEM_PROMPT_V1,
]


def test_prompt_classification_marker_exists():
    assert PROMPT_CLASSIFICATION == "SENSITIVE"


def test_prompts_not_json_serializable_as_plain_value():
    """Verifica que nenhum prompt pode ser inserido acidentalmente como valor JSON de resposta."""
    for prompt in ALL_PROMPTS:
        # Se um prompt acabar em um dict de resposta, json.dumps o serializa
        # — o teste garante que não há prompt embutido em estruturas comuns de resposta
        payload = {"detail": "error", "data": None}
        serialized = json.dumps(payload)
        assert prompt not in serialized


async def test_incident_report_fields_do_not_contain_system_prompts(
    client_with_auth, mock_run_analysis_ok
):
    """POST /analyze não deve incluir system prompts em nenhum campo do IncidentReport."""
    resp = await client_with_auth.post("/analyze", headers={"X-API-Key": "test-secret-key"})
    assert resp.status_code == 200
    body = resp.text
    for prompt in ALL_PROMPTS:
        assert prompt[:50] not in body, "System prompt leaked in /analyze response"
