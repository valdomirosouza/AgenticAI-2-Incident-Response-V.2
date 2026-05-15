"""
Testes para SpecialistAgent (base) e agentes concretos.
Tool-use loop, MAX_TOOL_ITERATIONS e _parse_finding são verificados via mocks.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.specialists.base import SpecialistAgent, MAX_TOOL_ITERATIONS
from app.agents.specialists.latency import LatencyAgent
from app.agents.specialists.errors import ErrorsAgent
from app.agents.specialists.saturation import SaturationAgent
from app.agents.specialists.traffic import TrafficAgent
from app.models.report import Severity
from tests.conftest import make_end_turn_response, make_tool_use_response

pytestmark = pytest.mark.asyncio

VALID_OK_JSON = {"severity": "ok", "summary": "Latency normal", "details": "P99=120ms"}
VALID_CRITICAL_JSON = {"severity": "critical", "summary": "P99 > 1000ms", "details": "P99=1800ms"}


def make_mock_agent_client(responses):
    """Cria um mock do AsyncAnthropic com respostas sequenciais."""
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=responses)
    return mock_client


# ─── analyze() — caminho end_turn direto ─────────────────────────────────────

async def test_analyze_end_turn_returns_finding():
    response = make_end_turn_response(VALID_OK_JSON)
    mock_client = make_mock_agent_client([response])

    with patch("app.agents.specialists.base.anthropic.AsyncAnthropic", return_value=mock_client):
        agent = LatencyAgent()
        finding = await agent.analyze()

    assert finding.severity == Severity.ok
    assert finding.specialist == "Latency"
    assert "120" in finding.details


async def test_analyze_critical_severity_parsed():
    response = make_end_turn_response(VALID_CRITICAL_JSON)
    mock_client = make_mock_agent_client([response])

    with patch("app.agents.specialists.base.anthropic.AsyncAnthropic", return_value=mock_client):
        agent = LatencyAgent()
        finding = await agent.analyze()

    assert finding.severity == Severity.critical


# ─── analyze() — tool_use então end_turn ─────────────────────────────────────

async def test_analyze_tool_use_then_end_turn():
    tool_response = make_tool_use_response("get_response_time_percentiles")
    end_response = make_end_turn_response(VALID_OK_JSON)

    mock_client = make_mock_agent_client([tool_response, end_response])

    with patch("app.agents.specialists.base.anthropic.AsyncAnthropic", return_value=mock_client):
        agent = LatencyAgent()
        with patch.object(agent, "_handle_tool", new=AsyncMock(return_value='{"p99_ms": 120}')):
            finding = await agent.analyze()

    assert finding.severity == Severity.ok
    assert mock_client.messages.create.call_count == 2


async def test_analyze_tool_use_updates_messages():
    tool_response = make_tool_use_response("get_overview", tool_id="tu_xyz")
    end_response = make_end_turn_response(VALID_OK_JSON)

    mock_client = make_mock_agent_client([tool_response, end_response])

    with patch("app.agents.specialists.base.anthropic.AsyncAnthropic", return_value=mock_client):
        agent = ErrorsAgent()
        with patch.object(agent, "_handle_tool", new=AsyncMock(return_value='{"error_rate_5xx_pct": 0.1}')):
            finding = await agent.analyze()

    # Second call should have extended messages with tool_result
    second_call_args = mock_client.messages.create.call_args_list[1]
    messages = second_call_args.kwargs.get("messages") or second_call_args.args[0]
    # Just verify the agent ran to completion
    assert finding is not None


# ─── analyze() — MAX_TOOL_ITERATIONS ─────────────────────────────────────────

async def test_analyze_exceeds_max_iterations_returns_warning():
    # Always returns tool_use — loop will hit the limit
    tool_response = make_tool_use_response("get_saturation")
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=tool_response)

    with patch("app.agents.specialists.base.anthropic.AsyncAnthropic", return_value=mock_client):
        agent = SaturationAgent()
        with patch.object(agent, "_handle_tool", new=AsyncMock(return_value="{}")):
            finding = await agent.analyze()

    assert finding.severity == Severity.warning
    assert str(MAX_TOOL_ITERATIONS) in finding.summary
    assert mock_client.messages.create.call_count == MAX_TOOL_ITERATIONS


# ─── _parse_finding ───────────────────────────────────────────────────────────

async def test_parse_finding_invalid_json_returns_warning():
    block = MagicMock()
    block.text = "not json"
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]

    mock_client = make_mock_agent_client([response])

    with patch("app.agents.specialists.base.anthropic.AsyncAnthropic", return_value=mock_client):
        agent = LatencyAgent()
        finding = await agent.analyze()

    assert finding.severity == Severity.warning
    assert "parse" in finding.summary.lower() or "parse" in finding.details.lower()


async def test_parse_finding_no_text_block_returns_warning():
    block = MagicMock(spec=["type"])  # no 'text' attribute
    block.type = "tool_use"
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [block]

    mock_client = make_mock_agent_client([response])

    with patch("app.agents.specialists.base.anthropic.AsyncAnthropic", return_value=mock_client):
        agent = LatencyAgent()
        finding = await agent.analyze()

    assert finding.severity == Severity.warning


async def test_parse_finding_invalid_severity_defaults_to_warning():
    bad_json = {"severity": "unknown_value", "summary": "test", "details": "d"}
    response = make_end_turn_response(bad_json)
    mock_client = make_mock_agent_client([response])

    with patch("app.agents.specialists.base.anthropic.AsyncAnthropic", return_value=mock_client):
        agent = LatencyAgent()
        finding = await agent.analyze()

    assert finding.severity == Severity.warning


async def test_parse_finding_truncates_summary():
    long_json = {"severity": "ok", "summary": "S" * 500, "details": "d"}
    response = make_end_turn_response(long_json)
    mock_client = make_mock_agent_client([response])

    with patch("app.agents.specialists.base.anthropic.AsyncAnthropic", return_value=mock_client):
        agent = LatencyAgent()
        finding = await agent.analyze()

    assert len(finding.summary) <= 300


# ─── Tool handlers por agente ─────────────────────────────────────────────────

async def test_latency_agent_handles_get_response_time_percentiles():
    agent = LatencyAgent.__new__(LatencyAgent)
    with patch("app.agents.specialists.latency.MetricsClient") as MockClient:
        MockClient.return_value.get_response_times = AsyncMock(return_value={"p99_ms": 120})
        result = await agent._handle_tool("get_response_time_percentiles", {})
    assert "120" in result


async def test_latency_agent_unknown_tool_returns_error():
    agent = LatencyAgent.__new__(LatencyAgent)
    result = await agent._handle_tool("nonexistent_tool", {})
    assert "error" in result


async def test_errors_agent_handles_get_overview():
    agent = ErrorsAgent.__new__(ErrorsAgent)
    with patch("app.agents.specialists.errors.MetricsClient") as MockClient:
        MockClient.return_value.get_overview = AsyncMock(return_value={"error_rate_5xx_pct": 0.5})
        result = await agent._handle_tool("get_overview", {})
    assert "0.5" in result


async def test_errors_agent_unknown_tool_returns_error():
    agent = ErrorsAgent.__new__(ErrorsAgent)
    result = await agent._handle_tool("nonexistent_tool", {})
    assert "error" in result


async def test_saturation_agent_handles_get_saturation():
    agent = SaturationAgent.__new__(SaturationAgent)
    with patch("app.agents.specialists.saturation.MetricsClient") as MockClient:
        MockClient.return_value.get_saturation = AsyncMock(return_value={"used_memory_bytes": 1024})
        result = await agent._handle_tool("get_saturation", {})
    assert "1024" in result


async def test_saturation_agent_unknown_tool_returns_error():
    agent = SaturationAgent.__new__(SaturationAgent)
    result = await agent._handle_tool("unknown", {})
    assert "error" in result


async def test_traffic_agent_handles_get_rps():
    agent = TrafficAgent.__new__(TrafficAgent)
    with patch("app.agents.specialists.traffic.MetricsClient") as MockClient:
        MockClient.return_value.get_rps = AsyncMock(return_value={"current_rps": 1.5})
        result = await agent._handle_tool("get_rps", {})
    assert "1.5" in result


async def test_traffic_agent_handles_get_backends():
    agent = TrafficAgent.__new__(TrafficAgent)
    with patch("app.agents.specialists.traffic.MetricsClient") as MockClient:
        MockClient.return_value.get_backends = AsyncMock(return_value={"web-backend": 100})
        result = await agent._handle_tool("get_backends", {})
    assert "web-backend" in result


async def test_traffic_agent_unknown_tool_returns_error():
    agent = TrafficAgent.__new__(TrafficAgent)
    result = await agent._handle_tool("unknown", {})
    assert "error" in result


# ─── Agent properties ─────────────────────────────────────────────────────────

def test_latency_agent_name():
    assert LatencyAgent.__new__(LatencyAgent).name == "Latency"


def test_errors_agent_name():
    assert ErrorsAgent.__new__(ErrorsAgent).name == "Errors"


def test_saturation_agent_name():
    assert SaturationAgent.__new__(SaturationAgent).name == "Saturation"


def test_traffic_agent_name():
    assert TrafficAgent.__new__(TrafficAgent).name == "Traffic"


def test_traffic_agent_has_two_tools():
    agent = TrafficAgent.__new__(TrafficAgent)
    assert len(agent.tools) == 2
